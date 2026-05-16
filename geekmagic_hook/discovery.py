"""Network discovery for GeekMagic devices."""

import json
import socket
import threading
import urllib.request
from typing import Optional


class DeviceDiscovery:
    """Scans the local subnet in parallel to find GeekMagic devices.

    Uses 254 threads (one per host) with a short per-host timeout so the
    full scan completes in about one second regardless of subnet size.
    """

    SCAN_TIMEOUT = 0.8   # seconds per host
    JOIN_TIMEOUT = 2.0   # max wall-clock time to wait for all threads

    def discover(self, subnet: Optional[str] = None) -> list[tuple[str, dict]]:
        """Return a list of (ip, info_dict) for each device found on the subnet."""
        if subnet is None:
            subnet = self._guess_subnet()

        print(f"  Scanning {subnet}.1-254 …", flush=True)
        results: list[tuple[str, dict]] = []
        lock = threading.Lock()
        threads = []

        for i in range(1, 255):
            ip = f"{subnet}.{i}"
            t = threading.Thread(
                target=self._check_ip,
                args=(ip, results, lock),
                daemon=True,
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=self.JOIN_TIMEOUT)

        return results

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _check_ip(self, ip: str, results: list, lock: threading.Lock) -> None:
        """Probe a single IP; append (ip, info) to results if it responds."""
        try:
            url = f"http://{ip}/v.json"
            with urllib.request.urlopen(url, timeout=self.SCAN_TIMEOUT) as r:
                data = json.loads(r.read().decode())
                if "m" in data and "v" in data:
                    with lock:
                        results.append((ip, data))
        except Exception:
            pass

    def _guess_subnet(self) -> str:
        """Return the local subnet prefix (e.g. '192.168.1') via a UDP probe."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ".".join(ip.split(".")[:3])
        except Exception:
            return "192.168.1"
