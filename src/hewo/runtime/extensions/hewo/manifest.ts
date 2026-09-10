import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const excluded = new Set(['AGENTS.md', 'CLAUDE.md']);

/** Resolve only normalized, non-symlink paths within this installed package. */
function resource(value: unknown): string {
  if (typeof value !== 'string' || !/^(?:\.\/)?[A-Za-z0-9_.-]+(?:\/[A-Za-z0-9_.-]+)*$/.test(value)) {
    throw new Error('Invalid runtime manifest path');
  }
  const parts = value.replace(/^\.\//, '').split('/');
  if (parts.some((part) => part === '.' || part === '..')) throw new Error('Runtime path traversal');
  let target = root;
  for (const part of parts) {
    target = path.join(target, part);
    if (fs.lstatSync(target).isSymbolicLink()) throw new Error('Runtime resource symlinks are not allowed');
  }
  return target;
}

function paths(value: unknown): string[] {
  if (!Array.isArray(value)) throw new Error('Runtime resource list must be an array');
  return value.map(resource);
}

function markdown(target: string): string[] {
  if (excluded.has(path.basename(target))) return [];
  if (fs.statSync(target).isDirectory()) {
    return fs.readdirSync(target).sort().flatMap((name) => {
      if (excluded.has(name)) return [];
      return markdown(resource(path.relative(root, path.join(target, name))));
    });
  }
  return target.endsWith('.md') ? [target] : [];
}

export function loadRuntimeManifest(): { prompt: string; tools: Set<string> } {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
  const agent = manifest.agent;
  if (agent?.manifest_version !== 1 || agent.backend !== 'pi') throw new Error('Unsupported runtime manifest');
  // pi loads its own resources; validate the same declared paths here, without
  // introducing a second resource list in an installer or launcher.
  for (const key of ['extensions', 'skills', 'prompts', 'themes']) paths(manifest.pi?.[key] ?? []);
  for (const key of ['agent_definitions', 'leaf_tools']) paths(agent[key] ?? []);
  const system = paths(agent.system_prompt);
  for (const file of system) {
    if (!fs.statSync(file).isFile()) throw new Error('System prompt must be a file');
  }
  const files = [...system.filter((file) => !excluded.has(path.basename(file))), ...paths(agent.context).flatMap(markdown)];
  if (!Array.isArray(agent.default_tools) || agent.default_tools.some((name: unknown) => typeof name !== 'string' || !/^[A-Za-z0-9_.-]+$/.test(name))) {
    throw new Error('Invalid runtime default_tools');
  }
  return {
    prompt: files.map((file) => `## Runtime source: ${path.relative(root, file)}\n\n${fs.readFileSync(file, 'utf8').trim()}`).join('\n\n'),
    tools: new Set<string>(agent.default_tools),
  };
}
