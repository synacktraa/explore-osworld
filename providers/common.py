import time
import requests
from io import BytesIO
from urllib.parse import urljoin

DEFAULT_ENV_VARS = {"DISK_SIZE": "8G", "RAM_SIZE": "4G", "CPU_CORES": "4"}

def wait_for_vm(
    server_url, 
    *, 
    headers: dict[str, str] | None = None, 
    timeout: int = 300
):
    """Wait for VM to be ready by checking screenshot endpoint."""
    start_time = time.time()
    screenshot_url = urljoin(server_url, "/screenshot")

    def capture_screenshot() -> BytesIO | None:
        try:
            response = requests.get(
                screenshot_url, headers=headers, timeout=(10, 10)
            )
            if response.status_code == 200:
                return BytesIO(initial_bytes=response.content)

            return None
        except Exception:
            return None

    idx = 1
    while time.time() - start_time < timeout:
        if (ss := capture_screenshot()) is not None:
            from PIL import Image
            Image.open(ss).show(title=f"Screenshot (attempt {idx})")
            return

        print(f"[{idx}] Checking if virtual machine is ready...")
        idx += 1
        time.sleep(1)
    
    raise TimeoutError("VM failed to become ready within timeout period")
