# Research Notes: Introducing a New Desktop Environment Provider

> **Note on Volume Support**: This research was conducted during the early exploration phase when understanding of sandbox provider capabilities was limited. It has since been discovered that modern sandbox providers like e2b and Daytona support volume attachments through mechanisms such as S3FS (AWS, CloudeFlare R2) and Google Cloud Storage FUSE (gfuse). The approaches documented here represent the evolution of understanding these platforms' capabilities, from initial assumptions about volume limitations to discovering native volume support features.

## Goal

- Capture how `OSWorld` provisions desktop environments today and identify what must change to support sandbox-style providers (e2b, Daytona, etc.) that only run plain Docker images with no external volumes.

## How Current Providers Work

- Volume-backed VMs: All integrations mount pre-baked VM disk images before launching an instance. For example, see [desktop_env/providers/virtualbox/manager.py#L23](https://github.com/xlang-ai/OSWorld/blob/main/desktop_env/providers/virtualbox/manager.py#L23) and [desktop_env/providers/docker/manager.py#L19-L20](https://github.com/xlang-ai/OSWorld/blob/main/desktop_env/providers/docker/manager.py#L19-L20).
- Controller-service contract: `desktop_env.py` creates a controller to communicate with the environment; the Python controller issues REST calls such as `/screenshot` and `/execute`. Code references: [desktop_env/desktop_env.py](https://github.com/xlang-ai/OSWorld/blob/main/desktop_env/desktop_env.py), [desktop_env/controllers/python.py](https://github.com/xlang-ai/OSWorld/blob/main/desktop_env/controllers/python.py), and the provider-side server at [desktop_env/server/main.py](https://github.com/xlang-ai/OSWorld/blob/main/desktop_env/server/main.py).
- Manual VM setup rationale: The server README clarifies that VM images are curated so pre-installed software lives at hard-coded paths used by evaluation scripts, and the server registers as a boot service. See [desktop_env/server/README.md#software-installation](https://github.com/xlang-ai/OSWorld/blob/main/desktop_env/server/README.md#software-installation).

## Why This Breaks on Sandbox Providers

- Providers such as e2b and Daytona let us snapshot Docker images into templates but do not support attaching large external volumes. The existing Docker provider relies on the `happysixd/osworld-docker` base image (see [desktop_env/providers/docker/provider.py#L110](https://github.com/xlang-ai/OSWorld/blob/main/desktop_env/providers/docker/provider.py#L110)) and expects a 22.7 GB `System.qcow2` disk to be mounted, so it cannot run on these services as-is.

## Multi-Stage Image Experiment

- Strategy: Bake the VM disk directly into the container image so no runtime volume is needed.
- `Dockerfile` used:

```docker
# This builds osworld-docker with Ubuntu VM pre-installed

# Stage 1: Download and extract Ubuntu VM
FROM ubuntu:22.04 AS vm-builder

RUN apt-get update && \
    apt-get install -y wget unzip ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /tmp

# Download Ubuntu VM
RUN wget --progress=dot:giga \
    https://huggingface.co/datasets/xlangai/ubuntu_osworld/resolve/main/Ubuntu.qcow2.zip && \
    unzip Ubuntu.qcow2.zip && \
    rm Ubuntu.qcow2.zip

# Verify the VM file exists and is readable
RUN test -f /tmp/Ubuntu.qcow2 && \
    echo "VM file size: $(du -h /tmp/Ubuntu.qcow2)"

# Stage 2: Layer VM on top of osworld-docker
FROM happysixd/osworld-docker

# Copy VM from builder stage to the expected location
COPY --from=vm-builder --chmod=644 /tmp/Ubuntu.qcow2 /System.qcow2

# Verify the VM was copied successfully
RUN test -f /System.qcow2 && \
    echo "VM installed at /System.qcow2" && \
    ls -lh /System.qcow2
```

- Built image: `synacktra/osworld-ubuntu:latest`. This image was tested by modifying the Docker provider’s `start_emulator` method locally to remove the volume mount requirement:

```python
self.container = self.client.containers.run(
    "synacktra/osworld-ubuntu:latest",
    environment=self.environment,
    cap_add=["NET_ADMIN"],
    devices=devices,
    # NO VOLUMES - VM is already at /System.qcow2 in the image
    ports={
        8006: self.vnc_port,
        5000: self.server_port,
        9222: self.chromium_port,
        8080: self.vlc_port
    },
    detach=True
)
```

The test was successful - the instance started without any issues and controller APIs responded normally.

## E2B Template Build Failure

- Attempted template build:

```python
from e2b import Template, default_build_logger

template = (
    Template()
    .from_image("synacktra/osworld-ubuntu:latest")
)

Template.build(
    template,
    alias="osworld-ubuntu",
    cpu_count=4,
    memory_mb=8192,
    on_build_logs=default_build_logger()
)
```

- Build output (truncated):

```
...
INFO  Base Docker image size: 12 GB
...
ERROR Build failed: ... failed to get uncompressed layer 6 ... NAME_INVALID: The requested artifact is larger than our max limit of 9.9 GiB
```

- Root cause: e2b limits individual image layers to 9.9 GB. The original VM file is 22.7 GB, which when compressed in the Docker registry becomes approximately 12 GB. However, when e2b attempts to extract and process this layer, the uncompressed size exceeds their 9.9 GiB per-layer limit.

## Daytona Volume Support Discovery

Upon discussion with a friend, discovered that Daytona does support attaching volumes during sandbox creation (see [Daytona volumes documentation](https://www.daytona.io/docs/en/volumes/)).

Since the `happysixd/osworld-docker` image requires the VM file to be available at the root (`/`) folder, attempted to upload the VM file to the root folder using a volume mount:

```python
volume = daytona.volume.get(name="osworld-ubuntu-vm", create=True)

params = CreateSandboxFromSnapshotParams(
    language="python",
    volumes=[VolumeMount(volumeId=volume.id, mountPath="/")],
)
sandbox = daytona.create(params)

try:
    f_info = sandbox.fs.get_file_info("/System.qcow2")
    print("VM file found in sandbox.")
except DaytonaNotFoundError:
    print("VM file not found in sandbox. Uploading...")
    sandbox.fs.upload_file(
        r"docker_vm_data/Ubuntu.qcow2.zip",
        "/System.qcow2.zip",
    )
    print(sandbox.process.exec("unzip /System.qcow2.zip -d /"))
```

However, this resulted in the following error:

```
daytona.common.errors.DaytonaError: Failed to create sandbox: Sandbox failed to start: Error response from daemon: invalid volume specification: '/mnt/daytona-volume-ce8a533f-6d19-4ab4-9a75-9c9714bc9d49/://': invalid mount config for type "bind": invalid specification: destination can't be '/'
```

**Issue**: `happysixd/osworld-docker` requires the VM file to be mounted at root folder (`/System.qcow2`), but Daytona does not allow volume mounts at the root folder.

## Reverse Engineering the Docker Image

The `happysixd/osworld-docker` image is not open source, so initially it appeared there was no way to modify the image to change the VM file path. However, by examining the image layers at [Docker Hub](https://hub.docker.com/layers/happysixd/osworld-docker/latest/images/sha256-0e6497a9295647cf05bf2b2af522fdd79bdeba2737595259cab310a3bcf6baa9), found layer 9: `COPY --chmod=755 ./src /run/`.

Spawned a container from the image and located the file using the `/System.qcow2` path. Found that `/run/install.sh` contains the hardcoded path. Extracted the relevant section:

```bash
# In override-install.sh
findBackingFile() {

  local ext="$1"
  local file

  file=$(find /vm -maxdepth 1 -type f -iname "System.$ext" | head -n 1)
  detectType "$file" && return 0

  return 1
}

findBackingFile "qcow2" && qemu-img create -f qcow2 -b /vm/System.qcow2 -F qcow2 /boot.qcow2
```

Modified the script to look for the VM file at `/vm/System.qcow2` instead of `/System.qcow2`.

---

### **Override `install.sh` Script**

Created a new `Dockerfile` to patch the `/run/install.sh` file:

```docker
FROM happysixd/osworld-docker

# Replace the install script inside the image
COPY --chmod=644 override-install.sh /run/install.sh
```

Built image: `synacktra/osworld-docker`. Successfully created a sandbox with the modified image and mounted the VM file at `/vm/System.qcow2` using volume mount:

```python
self.client.containers.run(
    "synacktra/osworld-docker",
    environment=self.environment,
    cap_add=["NET_ADMIN"],
    devices=devices,
    volumes={
        os.path.abspath(path_to_vm): {
            "bind": "/vm/System.qcow2",
            "mode": "ro"
        }
    },
    ports={
        8006: self.vnc_port,
        5000: self.server_port,
        9222: self.chromium_port,
        8080: self.vlc_port
    },
    detach=True
)
```

**Result**: The modified `install.sh` script successfully detected the VM file at `/vm/System.qcow2` and the container started successfully with controller APIs responding normally.

### Snapshot Build Process

```python
snapshot = daytona.snapshot.create(
    params=CreateSnapshotParams(
        name="osworld",
        image=Image.base("synacktra/osworld-docker:latest"),
        resources=Resources(
            cpu=4,
            memory=8,
            disk=10,
        ),
    ),
    on_logs=print,
)
print("Created snapshot:", snapshot)
```

During Daytona's snapshot build process, after building the image, it performs a validation step where it spawns a sandbox instance to verify that all layers execute without errors. Since there is no way to pass a volume to the snapshot build process, the original `ENTRYPOINT` layer (`ENTRYPOINT ["/usr/bin/tini" "-s" "/run/entry.sh"]`) needs to be overridden. The `entry.sh` script expects the VM file to be available, causing the validation to fail. To fix this, created a script to conditionally check for the VM before launching the original entrypoint:

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

VM_PATH="/vm/System.qcow2"

if [ -f "$VM_PATH" ]; then
  echo "✅ VM image found at $VM_PATH — launching original entrypoint..."
  exec /usr/bin/tini -s /run/entry.sh "$@"
else
  echo "⚠️  VM image not found at $VM_PATH. Skipping startup."
  echo "Place the VM at $VM_PATH and restart the container."
  sleep infinity
fi
```

This also requires the `Dockerfile` to be updated:

```docker
FROM happysixd/osworld-docker

# Replace the install script inside the image
COPY --chmod=644 override-install.sh /run/install.sh

# Copy a conditional entry script to verify VM presence
COPY --chmod=755 verify-and-entry.sh /run/verify-and-entry.sh

# Override the default entrypoint to use the new script
ENTRYPOINT ["/run/verify-and-entry.sh"]
```

Rebuilt the Docker image with these changes and re-created the Daytona snapshot. This time the validation step passed and the snapshot was ready to be used.

### Running `OSWorld` Snapshot

```python
import time
import requests
from urllib.parse import urljoin

from daytona import Daytona, CreateSandboxFromSnapshotParams, VolumeMount

daytona = Daytona()

volume = daytona.volume.get(name="osworld-ubuntu-vm")
sandbox = daytona.create(
    params=CreateSandboxFromSnapshotParams(
        snapshot="osworld",
        volumes=[VolumeMount(volumeId=volume.id, mountPath="/vm")],
        env_vars={"DISK_SIZE": "8G", "RAM_SIZE": "4G", "CPU_CORES": "4"}
    )
)

def wait_for_vm_ready(timeout: int):
    """Wait for VM to be ready by checking screenshot endpoint."""
    start_time = time.time()
    
    preview_link = sandbox.get_preview_link(5000)
    screenshot_url = urljoin(preview_link.url, "/screenshot")
    print("Screenshot URL:", screenshot_url)
    print("Auth token:", preview_link.token)

    def check_screenshot():
        try:
            response = requests.get(
                screenshot_url,
                headers={"Authorization": f"Bearer {preview_link.token}"}, 
                timeout=(10, 10)
            )
            if response.status_code == 200:
                with open("daytona-screenshot.png", "wb") as f:
                    f.write(response.content)

            return response.status_code == 200
        except Exception:
            return False

    while time.time() - start_time < timeout:
        if check_screenshot():
            return True
        print("Checking if virtual machine is ready...")
        time.sleep(1)
    
    raise TimeoutError("VM failed to become ready within timeout period")

wait_for_vm_ready(500)

sandbox.delete()
```

Starting a sandbox instance from the `osworld` snapshot did not work as expected - it timed out because the screenshot API failed, suggesting the API service never started. To investigate, two tests were performed:

- Removed the `wait_for_vm_ready` call and executed the command `sandbox.process.exec("ls /vm")`, which resulted in the following error:
    - `daytona.common.errors.DaytonaError: Failed to execute command: bad request: no IP address found. Is the Sandbox started?`
- Tried the same test using the base snapshot (by removing the `snapshot="osworld"` argument), which executed correctly and returned the file available in the `/vm` directory: `System.qcow2`

Additionally, ran a Docker container instance using the modified Docker image (`synacktra/osworld-docker`) directly, which worked perfectly without any issues. The next step is to figure out why the snapshot created by Daytona is not working as expected.