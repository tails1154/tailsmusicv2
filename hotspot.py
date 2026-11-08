"""NetworkManager-managed TailsMusic setup hotspot.

No global process kills, firewall flushes, or privileged system Python.
Requires NetworkManager permissions for the currently running user.
"""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
IFACE = os.environ.get("TAILSMUSIC_WIFI_IFACE", "wlan0")
SSID = os.environ.get("TAILSMUSIC_HOTSPOT_SSID", "TailsMusic-Setup")
PASSWORD = os.environ.get("TAILSMUSIC_HOTSPOT_PASSWORD", "tailsmusic")
PORT = int(os.environ.get("TAILSMUSIC_PORTAL_PORT", "8080"))
_CONNECTION = None
_PORTAL = None


def _run(*cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=25).stdout.strip()


def is_running():
    return _CONNECTION is not None


def start():
    global _CONNECTION, _PORTAL
    if is_running():
        return "Setup hotspot is already running"
    if len(PASSWORD) < 8:
        return "Hotspot password must contain at least eight characters"
    try:
        # NetworkManager configures its own DHCP and NAT without altering
        # unrelated system firewall chains or terminating other daemons.
        _run("nmcli", "device", "wifi", "hotspot", "ifname", IFACE,
             "ssid", SSID, "password", PASSWORD)
        _CONNECTION = _run("nmcli", "-g", "GENERAL.CONNECTION",
                           "device", "show", IFACE).splitlines()[0]
        address = _run("nmcli", "-g", "IP4.ADDRESS", "device", "show", IFACE)
        ip = address.splitlines()[0].split("/")[0]
        env = dict(os.environ, TAILSMUSIC_PORTAL_PORT=str(PORT))
        _PORTAL = subprocess.Popen(
            [sys.executable, "-m", "portal.server"],
            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if _PORTAL.poll() is not None:
            raise RuntimeError("Setup portal did not start")
        return "Hotspot '{}' active. Open http://{}:{} on a connected device.".format(SSID, ip, PORT)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError,
            IndexError, RuntimeError) as exc:
        stop()
        return "Hotspot failed: {}. Check NetworkManager permissions and Wi-Fi AP support.".format(exc)


def stop():
    global _CONNECTION, _PORTAL
    if _PORTAL is not None:
        _PORTAL.terminate()
        try:
            _PORTAL.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _PORTAL.kill()
            _PORTAL.wait()
        _PORTAL = None
    if _CONNECTION is not None:
        try:
            _run("nmcli", "connection", "down", _CONNECTION)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass
        _CONNECTION = None
    return "Hotspot stopped"
