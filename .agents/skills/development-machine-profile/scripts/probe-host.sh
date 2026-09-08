#!/usr/bin/env bash
# Read-only development-machine probe.
#
# Emits machine-profile JSON (keyed by the eight capability families in
# references/profile-schema.md) to stdout. Secret-safe: only --version,
# --help, command -v, OS/storage/port queries, SSH alias listing, and
# environment-variable EXISTENCE checks. Never prints secret values.
exec python3 - <<'PYEOF'
import json
import os
import re
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
from datetime import datetime


def run(args, timeout=15):
    """Run a command list, return trimmed combined stdout+stderr."""
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return ((r.stdout or "") + (r.stderr or "")).strip()
    except Exception:
        return ""


def first_line(text):
    for line in text.splitlines():
        if line.strip():
            return line.strip()[:200]
    return ""


ERROR_MARKERS = (
    "unknown option",
    "unknown command",
    "flag provided but not defined",
    "not defined",
    "invalid option",
    "usage:",
    "caution:",
    "cannot find or open",
    "no rule to make",
    "pseudo-terminal",
    "error:",
)


def version_of(path):
    for extra in (["--version"], ["-V"], ["version"], ["-v"]):
        out = run([path] + extra, timeout=8)
        if not out:
            continue
        first = first_line(out)
        low = first.lower()
        if any(m in low for m in ERROR_MARKERS):
            continue
        if not any(ch.isdigit() for ch in first):
            continue
        return first
    return ""


def help_of(path, extra=None):
    out = run([path] + (extra or []) + ["--help"], timeout=15)
    return out[:12000]


def extract_block(text, marker):
    i = text.find(marker)
    if i == -1:
        return ""
    j = text.find("╭─", i + len(marker))
    if j == -1:
        return text[i:]
    return text[i:j]


def which(name):
    return shutil.which(name)


def env_exists(name):
    return "set" if name in os.environ else "unset"


CLOUD_SERVICES = [
    {"name": "Bohrium LKM", "endpoint": "https://open.bohrium.com/openapi/v2/lkm", "env": "BOHR_ACCESS_KEY"},
    {"name": "Hugging Face Hub", "endpoint": "https://huggingface.co", "env": "HF_TOKEN"},
]


def endpoint_status(url):
    """Secret-free reachability check: GET the URL, record only the HTTP status."""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=8) as resp:
            return str(resp.status)
    except urllib.error.HTTPError as exc:
        return str(exc.code)
    except Exception:
        return "unreachable"


profile = {
    "schema": "development-machine-profile/v1",
    "generated_at": datetime.now().isoformat(timespec="seconds"),
    "host": {},
    "runtime": {},
    "toolchain": [],
    "agent_backends": {},
    "external_services": {},
    "documented_interfaces": {},
    "credential_surface": {},
    "evidence_status": {},
}

# ---- host ----
os_release = {}
try:
    with open("/etc/os-release") as fh:
        for line in fh:
            if "=" in line:
                k, v = line.rstrip("\n").split("=", 1)
                os_release[k] = v.strip().strip('"')
except OSError:
    pass

cpu_model = ""
try:
    with open("/proc/cpuinfo") as fh:
        for line in fh:
            if line.lower().startswith("model name"):
                cpu_model = line.split(":", 1)[1].strip()
                break
except OSError:
    pass

mem_total = ""
try:
    with open("/proc/meminfo") as fh:
        for line in fh:
            if line.startswith("MemTotal:"):
                mem_total = line.split(":", 1)[1].strip()
                break
except OSError:
    pass

storage = []
for line in run(["df", "-h", "-x", "tmpfs", "-x", "devtmpfs", "-x", "squashfs", "-x", "overlay"]).splitlines()[1:]:
    parts = line.split()
    if len(parts) == 6 and not parts[0].startswith("df:"):
        storage.append({
            "filesystem": parts[0],
            "size": parts[1],
            "avail": parts[3],
            "use%": parts[4],
            "mount": parts[5],
        })

gpu = "none"
if which("nvidia-smi"):
    g = run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], timeout=10)
    if g and not g.lower().startswith("nvidia-smi"):
        gpu = first_line(g)

def human_ram(kb_text):
    m = re.match(r"(\d+)", kb_text)
    if m:
        gib = int(m.group(1)) / 1024 / 1024
        return f"{gib:.1f} GiB ({kb_text})"
    return kb_text


profile["host"] = {
    "hostname": socket.gethostname(),
    "os": os_release.get("PRETTY_NAME", ""),
    "kernel": run(["uname", "-r"]),
    "arch": run(["uname", "-m"]),
    "cpu_model": cpu_model,
    "cpu_cores": os.cpu_count(),
    "ram_total": human_ram(mem_total),
    "gpu": gpu,
    "storage": storage,
}

# ---- runtime ----
profile["runtime"] = {
    "shell": os.environ.get("SHELL", ""),
    "package_managers": [m for m in ("apt", "brew", "uv", "pip3", "pip", "npm", "go", "cargo") if which(m)],
    "runtimes": {},
}
for rt in ("python3", "node", "npm", "go", "uv"):
    p = which(rt)
    profile["runtime"]["runtimes"][rt] = version_of(p) if p else ""

# ---- toolchain ----
TOOLCHAIN = [
    "git", "docker", "ssh", "make", "gcc", "g++", "clang", "cmake", "curl",
    "wget", "jq", "rsync", "tar", "unzip", "zip", "tmux", "htop", "tailscale",
    "python3", "pip3", "node", "npm", "go", "uv", "cargo", "rustc", "hf",
    "orca", "codex", "opencode", "claude", "pi", "harbor", "lark-cli",
]
for name in TOOLCHAIN:
    p = which(name)
    if p:
        profile["toolchain"].append({"name": name, "path": p, "version": version_of(p)})

# ---- agent_backends ----
def backend(name, role):
    p = which(name)
    return {"path": p or "", "version": version_of(p) if p else "", "role": role}

profile["agent_backends"] = {
    "codex": backend("codex", "OpenAI-family coding agent backend"),
    "opencode": backend("opencode", "OpenCode coding agent backend"),
    "claude": backend("claude", "Anthropic-family coding agent backend"),
    "pi": backend("pi", "pi coding agent backend"),
    "harbor": backend("harbor", "external agent/task execution layer"),
    "orca": backend("orca", "Orca orchestration CLI"),
}
harbor_run_help = help_of(which("harbor") or "harbor", ["run"])
profile["agent_backends"]["harbor"]["supported_agents"] = extract_block(harbor_run_help, "╭─ Agent")

# ---- external_services ----
ext = {}
lark = which("lark-cli")
ext["lark_cli"] = {"path": lark or "", "version": version_of(lark) if lark else ""}
hf = which("hf")
ext["hf"] = {"path": hf or "", "version": version_of(hf) if hf else ""}
orca = which("orca")
ext["orca"] = {"path": orca or "", "version": version_of(orca) if orca else ""}
docker = which("docker")
daemon = "not-accessible"
if docker:
    if subprocess.run([docker, "info"], capture_output=True, timeout=15).returncode == 0:
        daemon = "running"
ext["docker"] = {"path": docker or "", "version": version_of(docker) if docker else "", "daemon": daemon}

ssh_hosts = []
ssh_cfg = os.path.expanduser("~/.ssh/config")
if os.path.exists(ssh_cfg):
    try:
        for line in open(ssh_cfg):
            s = line.strip()
            if s.lower().startswith("host "):
                for n in s.split()[1:]:
                    if n and "*" not in n:
                        ssh_hosts.append(n)
    except OSError:
        pass
ext["ssh_hosts"] = ssh_hosts

listening = []
for line in run(["ss", "-tlnp"], timeout=15).splitlines():
    m = re.search(r"LISTEN\s+\S+\s+\S+\s+(\S+):(\d+)\s+", line)
    if not m:
        continue
    proc = ""
    m2 = re.search(r'users:\(\("([^"]+)"', line)
    if m2:
        proc = m2.group(1)
    listening.append({"addr": m.group(1), "port": m.group(2), "proc": proc})
ext["listening_services"] = listening

cloud = []
for svc in CLOUD_SERVICES:
    cloud.append({
        "name": svc["name"],
        "endpoint": svc["endpoint"],
        "env": svc["env"],
        "env_present": env_exists(svc["env"]),
        "http_status": endpoint_status(svc["endpoint"]),
    })
ext["cloud_services"] = cloud

profile["external_services"] = ext

# ---- documented_interfaces ----
hb = which("harbor") or "harbor"
doc = {
    "harbor": help_of(hb),
    "harbor_run": harbor_run_help,
    "harbor_auth": help_of(hb, ["auth"]),
    "harbor_adapter": help_of(hb, ["adapter"]),
    "harbor_task": help_of(hb, ["task"]),
    "harbor_job": help_of(hb, ["job"]),
    "harbor_trial": help_of(hb, ["trial"]),
    "harbor_dataset": help_of(hb, ["dataset"]),
    "harbor_analyze": help_of(hb, ["analyze"]),
    "harbor_view": help_of(hb, ["view"]),
}
if lark:
    doc["lark_cli"] = help_of(lark)
if hf:
    doc["hf"] = help_of(hf)
if docker:
    doc["docker"] = help_of(docker)
if orca:
    doc["orca"] = help_of(orca)
profile["documented_interfaces"] = doc

# ---- credential_surface (existence only) ----
SECRET_VARS = [
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
    "OPENAI_BASE_URL", "ANTHROPIC_BASE_URL", "CODEX_AUTH_JSON_PATH",
    "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "DOCKER_HOST", "GITHUB_TOKEN",
    "BOHR_ACCESS_KEY",
]
profile["credential_surface"] = {v: env_exists(v) for v in SECRET_VARS}

# ---- evidence_status: filled by the facts file, never probed ----
profile["evidence_status"] = {}

print(json.dumps(profile, indent=2))
PYEOF
