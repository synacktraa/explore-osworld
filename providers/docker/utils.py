from pathlib import Path
from time import sleep
from zipfile import ZipFile

import psutil
import requests
from docker.models.containers import Container
from tqdm import tqdm

VMS_DIR = Path(__file__).parent / ".vms"

UBUNTU_QCOW2_ZIP_URL = "https://huggingface.co/datasets/xlangai/ubuntu_osworld/resolve/main/Ubuntu.qcow2.zip"
UBUNTU_QCOW2_ZIP_FILENAME = UBUNTU_QCOW2_ZIP_URL.split("/")[-1]
UBUNTU_QCOW2_ZIP_FILEPATH = VMS_DIR / UBUNTU_QCOW2_ZIP_FILENAME
UBUNTU_QCOW2_FILEPATH = VMS_DIR / UBUNTU_QCOW2_ZIP_FILENAME.removesuffix(".zip")

def get_system_occupied_ports() -> set[int]:
    return set(conn.laddr.port for conn in psutil.net_connections())


def get_docker_occupied_ports(containers: list[Container]) -> set[int]:
    occupied_ports = set()
    for container in containers:
        ports = container.attrs['NetworkSettings']['Ports']
        if not ports:
            continue
        for port_mappings in ports.values():
            if port_mappings:
                occupied_ports.update(int(p['HostPort']) for p in port_mappings)
    
    return occupied_ports


def get_next_available_port(*, start_port: int, occupied_ports: set[int]) -> int:
    port = start_port
    while port < 65354:
        if port not in occupied_ports:
            return port
        port += 1
    raise Exception(f"No available ports found starting from {start_port}")


def download_vm():
    VMS_DIR.mkdir(exist_ok=True)

    current_size = 0
    while True:
        headers = {}
        if UBUNTU_QCOW2_ZIP_FILEPATH.exists():
            current_size = UBUNTU_QCOW2_ZIP_FILEPATH.stat().st_size
            headers["Range"] = f"bytes={current_size}-"
        
        with requests.get(
            UBUNTU_QCOW2_ZIP_URL, headers=headers, stream=True
        ) as response:
            if response.status_code == 416:
                break

            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            with UBUNTU_QCOW2_ZIP_FILEPATH.open("ab") as file, tqdm(
                desc="Progress",
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
                initial=current_size,
                ascii=True
            ) as bar:
                try:
                    for data in response.iter_content(chunk_size=1024):
                        size = file.write(data)
                        bar.update(size)
                except (requests.exceptions.RequestException, IOError) as e:
                    print(f"Download error: {e}. Retrying...")
                    sleep(5)
                else:
                    break

        with ZipFile(UBUNTU_QCOW2_ZIP_FILEPATH, 'r') as zip_file:
            zip_file.extractall(VMS_DIR)
