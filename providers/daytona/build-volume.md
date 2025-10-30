## Create a volume

```bash
daytona volume create osworld-ubuntu-vm -s 40
```

## Download the VM image into the volume

Create a temporary sandbox and SSH into it to download the VM image.

```bash
eval "$(uv run python -c "
from daytona import Daytona, CreateSandboxFromSnapshotParams, VolumeMount

daytona = Daytona()
volume = daytona.volume.get(name='osworld-ubuntu-vm')

sandbox = daytona.create(
    params=CreateSandboxFromSnapshotParams(
        volumes=[VolumeMount(volumeId=volume.id, mountPath='/vm')],
    )
)

ssh_access = sandbox.create_ssh_access()
print(f'ssh {ssh_access.token}@ssh.app.io')
")"
```

This will automatically SSH into the sandbox with the volume mounted at `/vm`.

Once inside the SSH shell, download and extract the VM:

```bash
cd /vm
curl -L -# -o Ubuntu.qcow2.zip https://huggingface.co/datasets/xlangai/ubuntu_osworld/resolve/main/Ubuntu.qcow2.zip
unzip -p Ubuntu.qcow2.zip > /vm/System.qcow2
ls -lh System.qcow2
```

**Note:** The temporary sandbox will remain running. To clean it up after you're done, list sandboxes and delete it:

```bash
daytona sandbox list
daytona sandbox delete <sandbox-id>
```