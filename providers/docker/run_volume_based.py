import os
from contextlib import suppress
from pathlib import Path
from tempfile import tempdir

import docker
from filelock import FileLock

from providers.common import DEFAULT_ENV_VARS, wait_for_vm
from providers.docker.utils import (
    get_system_occupied_ports,
    get_docker_occupied_ports,
    get_next_available_port,
    UBUNTU_QCOW2_FILEPATH,
    download_vm,
)


def main():
    if not UBUNTU_QCOW2_FILEPATH.exists():
        download_vm()

    docker_client = docker.from_env()

    lock_file = Path(tempdir or Path.cwd()) / "docker_port_allocation.lck"
    lock = FileLock(lock_file, timeout=10)

    occupied_ports = get_system_occupied_ports() | get_docker_occupied_ports(
        docker_client.containers.list()
    )

    with lock:
        # Allocate required ports
        server_port = get_next_available_port(
            start_port=5000, occupied_ports=occupied_ports
        )
        vnc_port = get_next_available_port(
            start_port=8006, occupied_ports=occupied_ports
        )
        chromium_port = get_next_available_port(
            start_port=9222, occupied_ports=occupied_ports
        )
        vlc_port = get_next_available_port(
            start_port=8080, occupied_ports=occupied_ports
        )

        devices = []
        env_vars = DEFAULT_ENV_VARS.copy()
        if os.path.exists("/dev/kvm"):
            devices.append("/dev/kvm")
            print("KVM device found, using hardware acceleration")
        else:
            env_vars["KVM"] = "N"
            print("KVM device not found, running without hardware acceleration (will be slower)")

        container = docker_client.containers.run(
            "synacktra/osworld-docker",
            environment=env_vars,
            cap_add=["NET_ADMIN"],
            devices=devices,
            volumes={
                str(UBUNTU_QCOW2_FILEPATH): {
                    "bind": "/vm/System.qcow2",
                    "mode": "ro"
                }
            },
            ports={
                5000: server_port,
                8006: vnc_port,
                9222: chromium_port,
                8080: vlc_port
            },
            detach=True
        )
        try:
            wait_for_vm(f"http://localhost:{server_port}")
        finally:
            with suppress(Exception):
                container.stop()
                container.remove()

if __name__ == "__main__":
    main()
