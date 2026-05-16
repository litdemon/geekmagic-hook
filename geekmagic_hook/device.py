"""GeekMagic SmallTV-Ultra HTTP API client."""

import json
import logging
import pathlib
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from .constants import HTTP_TIMEOUT

log = logging.getLogger("geekmagic_hook")


class GeekMagic:
    """Thin wrapper around the GeekMagic device HTTP API.

    All methods time out after HTTP_TIMEOUT seconds and return a safe
    default (None / False) on failure so callers never need to handle
    network exceptions.
    """

    def __init__(self, ip: str) -> None:
        self.base = f"http://{ip}"

    # ------------------------------------------------------------------
    # Low-level HTTP helpers
    # ------------------------------------------------------------------

    def _get(self, path: str) -> Optional[str]:
        try:
            url = self.base + path
            with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as r:
                return r.read().decode()
        except Exception as e:
            log.debug("GET %s failed: %s", path, e)
            return None

    def _upload(self, path: str, filename: str, data: bytes) -> bool:
        boundary = "GeekMagicBoundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: image/gif\r\n\r\n"
        ).encode() + data + f"\r\n--{boundary}--\r\n".encode()

        try:
            req = urllib.request.Request(
                self.base + path,
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST",
            )
            # Device responds with updated filelist HTML (not "OK") on success
            with urllib.request.urlopen(req, timeout=30) as r:
                resp = r.read().decode()
                return r.status == 200 or filename in resp
        except Exception as e:
            log.debug("Upload %s failed: %s", filename, e)
            return False

    # ------------------------------------------------------------------
    # Device information
    # ------------------------------------------------------------------

    def is_online(self) -> bool:
        return self._get("/v.json") is not None

    def get_info(self) -> Optional[dict]:
        raw = self._get("/v.json")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass
        return None

    def get_space(self) -> Optional[dict]:
        """Return storage info: {total, free} in bytes."""
        raw = self._get("/space.json")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass
        return None

    def get_active_theme(self) -> Optional[int]:
        raw = self._get("/app.json")
        if raw:
            try:
                return json.loads(raw).get("theme")
            except Exception:
                pass
        return None

    # ------------------------------------------------------------------
    # Display control
    # ------------------------------------------------------------------

    def set_theme(self, theme_id: int) -> bool:
        return self._get(f"/set?theme={theme_id}") == "OK"

    def get_theme_list(self) -> Optional[dict]:
        """Return current auto-switch settings: {list, sw_en, sw_i}."""
        raw = self._get("/theme_list.json")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass
        return None

    def set_auto_switch(self, enabled: bool) -> bool:
        """Toggle auto theme switching, preserving the user's theme list and interval.

        Skips the API call if sw_en is already in the desired state to avoid a
        firmware side-effect: sending theme_list back to the device causes it to
        momentarily activate the first entry in the list (e.g. Weather Clock Today)
        before our subsequent set_theme(PHOTO_ALBUM_THEME) call overrides it.
        """
        tl = self.get_theme_list()
        if not tl:
            return False
        desired = "1" if enabled else "0"
        if tl.get("sw_en", "0") == desired:
            log.debug("set_auto_switch: already sw_en=%s, skipping", desired)
            return True  # already in desired state — no API call needed
        theme_list = tl.get("list", "0,0,1,1,0,0,0")
        sw_i = tl.get("sw_i", "30")
        return self._get(
            f"/set?theme_list={theme_list}&sw_en={desired}&theme_interval={sw_i}"
        ) == "OK"

    def set_image(self, image_path: str) -> bool:
        """Set the displayed GIF. Device expects the raw double-slash path format."""
        return self._get(f"/set?img={image_path}") == "OK"

    # ------------------------------------------------------------------
    # File management
    # ------------------------------------------------------------------

    def upload_gif(self, upload_dir: str, local_path: pathlib.Path) -> bool:
        data = local_path.read_bytes()
        encoded_dir = urllib.parse.quote(upload_dir)
        return self._upload(f"/doUpload?dir={encoded_dir}", local_path.name, data)

    def list_files(self, directory: str) -> Optional[str]:
        """Return raw HTML filelist for the given device directory."""
        encoded = urllib.parse.quote(directory)
        return self._get(f"/filelist?dir={encoded}")
