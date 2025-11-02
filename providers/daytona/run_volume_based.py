from daytona import (
    Daytona, 
    CreateSnapshotParams,
    Image,
    Resources,
    CreateSandboxFromSnapshotParams, 
    VolumeMount
)
from daytona.common.errors import DaytonaNotFoundError

from providers.common import DEFAULT_ENV_VARS, wait_for_vm


def main():
    daytona = Daytona()

    try:
        volume = daytona.volume.get(name="osworld-ubuntu-vm")
    except DaytonaNotFoundError:
        print("Please refer ./build-volume.md to create the required volume first.")
        return
    
    try:
        snapshot = daytona.snapshot.get(name="osworld")
    except DaytonaNotFoundError:
        print("'osworld' snapshot not found, creating...")
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

    print(f"Using osworld snapshot with ID: {snapshot.id}")
    sandbox = daytona.create(
        params=CreateSandboxFromSnapshotParams(
            snapshot="osworld",
            volumes=[VolumeMount(volumeId=volume.id, mountPath="/vm")],
            env_vars=DEFAULT_ENV_VARS
        )
    )
    print(f"OSWorld Sandbox created with ID: {sandbox.id}")

    try:
        preview_link = sandbox.get_preview_link(5000)
        wait_for_vm(
            preview_link.url,
            headers={"Authorization": f"Bearer {preview_link.token}"},
        )
    finally:
        sandbox.delete()

if __name__ == "__main__":
    main()
