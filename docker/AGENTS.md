# Clean Container Runtime

For the development coding agent only: maintain the clean-user Docker installation and E2E entrypoint. Do not bake credentials, host configuration, or development instructions into final images. Mount only explicitly selected credential inputs. Distinguish build, CLI startup, and real model-task success.
