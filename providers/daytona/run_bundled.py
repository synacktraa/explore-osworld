from daytona import (
    Daytona, 
    CreateSnapshotParams,
    Image,
    Resources,
    CreateSandboxFromSnapshotParams, 
)
from daytona.common.errors import DaytonaNotFoundError

from providers.common import DEFAULT_ENV_VARS, wait_for_vm


def main():
    daytona = Daytona()
    
    try:
        snapshot = daytona.snapshot.get(name="osworld-ubuntu")
    except DaytonaNotFoundError:
        print("'osworld-ubuntu' snapshot not found, creating...")
        snapshot = daytona.snapshot.create(
            params=CreateSnapshotParams(
                name="osworld-ubuntu",
                image=Image.base("synacktra/osworld-ubuntu:latest"),
                resources=Resources(
                    cpu=4,
                    memory=8,
                    disk=25,
                ),
            ),
            on_logs=print,
        )

    print(f"Using osworld-ubuntu snapshot with ID: {snapshot.id}")
    sandbox = daytona.create(
        params=CreateSandboxFromSnapshotParams(
            snapshot="osworld-ubuntu",
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
