# Explore OSWorld

Research and experimentation on adapting [OSWorld](https://github.com/xlang-ai/OSWorld) to work with modern cloud-based sandbox providers and exploring various integration possibilities.

## What is this?

This repository documents ongoing research and development work on OSWorld, focusing on making it more accessible and flexible for different deployment scenarios. Current work includes:

- **Desktop Environment Providers**: Adapting OSWorld's desktop environment provisioning to work with cloud-based sandbox providers like Daytona and e2b
- **Agent Providers** _(planned)_: Exploring integration with different agent frameworks and providers
- **General OSWorld Exploration**: Investigating architecture, capabilities, and potential improvements

The initial focus has been on solving desktop environment provisioning challenges, particularly around the 22.7 GB VM disk images that OSWorld relies on, which present unique challenges for sandbox providers with layer size limitations and volume mounting constraints.

## Why?

**The Problem**: OSWorld's existing providers (VirtualBox, Docker) require pre-baked VM disk images to be mounted before launching instances. This approach doesn't translate well to modern sandbox providers because:

- e2b has a 9.9 GiB per-layer limit, making it impossible to bake large VM files directly into Docker images
- Daytona and similar providers have specific volume mounting constraints (e.g., cannot mount at root `/`)
- The `happysixd/osworld-docker` base image is closed-source with hardcoded paths

**The Solution**: Through reverse engineering and experimentation, this project:

1. Patches the closed-source `happysixd/osworld-docker` image to support flexible VM file paths
2. Implements volume-based VM provisioning for Daytona
3. Provides working examples for both local Docker and Daytona sandbox environments

## How?

### Project Structure

```
explore-osworld/
├── docs/                          # Research documentation
│   └── desktop-env.md            # Detailed research notes and findings
├── template/                      # Modified OSWorld Docker image
│   ├── Dockerfile                # Patches happysixd/osworld-docker
│   ├── override-install.sh       # Modified script to support /vm path
│   └── verify-and-entry.sh       # Conditional entrypoint for snapshots
├── providers/
│   ├── common.py                 # Shared utilities
│   ├── docker/                   # Local Docker provider
│   │   └── run.py               # Run OSWorld with local Docker
│   └── daytona/                  # Daytona sandbox provider
│       ├── run.py               # Run OSWorld on Daytona
│       └── build-volume.md      # Guide for setting up Daytona volumes
└── pyproject.toml                # Project dependencies
```

### Quick Start

#### Prerequisites

- [uv](https://github.com/astral-sh/uv) package manager
- Docker (for local testing)
- Daytona account and CLI (for cloud deployment)

#### Modified Docker Image

The `template/` directory contains a modified version of `happysixd/osworld-docker` (published as `synacktra/osworld-docker`) that is used by both local Docker and Daytona providers. It patches the original image to:

- Support flexible VM paths (`/vm/System.qcow2` instead of `/System.qcow2`)
- Add a conditional entrypoint for Daytona snapshot validation
- Maintain compatibility with the original OSWorld controller contract

#### Docker Testing

```bash
uv run python -m providers.docker.run
```

This mounts the VM file from your local filesystem at `/vm/System.qcow2` in the container.

#### Daytona Testing

```bash
export DAYTONA_API_KEY=dtn_xxxxxx
uv run python -m providers.daytona.run
```

This uses a Daytona volume with the VM file and a snapshot built from `synacktra/osworld-docker`.

## Key Findings

### Multi-Stage Image Approach (Attempted)
Initially attempted to bake the VM directly into the Docker image using multi-stage builds. This worked locally but failed on e2b & daytona due to their 10 GiB layer size limit.

### Volume Mount Solution (Successful)
Discovered that Daytona supports volume mounting through S3FS and gfuse. By reverse-engineering the `happysixd/osworld-docker` image and patching the `/run/install.sh` script, successfully moved the VM file from `/System.qcow2` to `/vm/System.qcow2`, enabling volume-based deployment.

### Entrypoint Workaround
Created a conditional entrypoint (`verify-and-entry.sh`) that checks for VM presence before launching. This allows Daytona's snapshot validation to pass even when the VM volume isn't attached during the build process.

## Research Documentation

For detailed research notes, findings, and experiments, see [`docs/desktop-env.md`](docs/desktop-env.md).

## Current Status

### Desktop Environment Providers
- ✅ Local Docker provider working
- ✅ Modified Docker image with flexible VM paths
- ✅ Daytona volume setup documented
- 🚧 Daytona snapshot integration (in progress)
- ⏳ e2b provider (planned)

### Agent Providers
- ⏳ Research and exploration (planned)

## Contributing

This is a research project documenting exploration of OSWorld deployment options. Feel free to open issues or PRs with improvements, findings, or alternative approaches.

## License

This project is for research and educational purposes. Please refer to [OSWorld's license](https://github.com/xlang-ai/OSWorld) for the underlying framework.

## Acknowledgments

- [OSWorld](https://github.com/xlang-ai/OSWorld) - The original desktop environment framework
- [Daytona](https://www.daytona.io/) - Cloud sandbox provider
- [e2b](https://e2b.dev/) - Cloud sandbox provider
