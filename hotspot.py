import subprocess
import os
import time
import signal

HOTSPOT_IFACE = "wlan0"
HOTSPOT_SSID = "TailsMusic-Setup"
HOTSPOT_PASS = "tailsmusic"
HOTSPOT_IP = "192.168.4.1"
DNSMASQ_LEASES = "/var/lib/misc/dnsmasq.leases"
PORTAL_PID_FILE = "/tmp/tailsmusic_portal.pid"

def _run(cmd, check=True):
    return subprocess.run(cmd, capture_output=True, text=True, check=check)

def _write_file(path, content):
    with open(path, 'w') as f:
        f.write(content)

def is_running():
    return os.path.exists(PORTAL_PID_FILE)

def start():
    if is_running():
        return "Portal is already running"

    try:
        _run(["sudo", "nmcli", "radio", "wifi", "off"], check=False)
        time.sleep(1)

        _write_file("/tmp/hostapd.conf", f"""interface={HOTSPOT_IFACE}
driver=nl80211
ssid={HOTSPOT_SSID}
hw_mode=g
channel=6
wmm_enabled=1
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={HOTSPOT_PASS}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
""")

        _write_file("/tmp/dnsmasq.conf", f"""interface={HOTSPOT_IFACE}
dhcp-range=192.168.4.2,192.168.4.100,255.255.255.0,24h
dhcp-option=3,{HOTSPOT_IP}
dhcp-option=6,{HOTSPOT_IP}
address=/#/{HOTSPOT_IP}
log-queries
log-dhcp
""")

        _run(["sudo", "ifconfig", HOTSPOT_IFACE, HOTSPOT_IP, "netmask", "255.255.255.0", "up"])

        _run(["sudo", "pkill", "-9", "dnsmasq"], check=False)
        _run(["sudo", "pkill", "-9", "hostapd"], check=False)
        time.sleep(1)

        dnsmasq_proc = subprocess.Popen(
            ["sudo", "dnsmasq", "-C", "/tmp/dnsmasq.conf", "--no-daemon"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        hostapd_proc = subprocess.Popen(
            ["sudo", "hostapd", "/tmp/hostapd.conf"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        _run(["sudo", "iptables", "-t", "nat", "-F", "PREROUTING"], check=False)
        _run(["sudo", "iptables", "-t", "nat", "-A", "PREROUTING",
              "-i", HOTSPOT_IFACE, "-p", "tcp", "--dport", "80",
              "-j", "DNAT", "--to-destination", f"{HOTSPOT_IP}:80"], check=False)
        _run(["sudo", "iptables", "-A", "FORWARD",
              "-i", HOTSPOT_IFACE, "-j", "ACCEPT"], check=False)

        portal_proc = subprocess.Popen(
            ["sudo", "python3", "-m", "portal.server"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        with open(PORTAL_PID_FILE, 'w') as f:
            f.write(f"{dnsmasq_proc.pid},{hostapd_proc.pid},{portal_proc.pid}")

        return f"Hotspot '{HOTSPOT_SSID}' started. Connect and visit any website to access setup."

    except subprocess.CalledProcessError as e:
        return f"Hotspot error: {e.stderr}"

def stop():
    if not is_running():
        return "Portal is not running"
    try:
        with open(PORTAL_PID_FILE) as f:
            pids = f.read().strip().split(",")
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass

        os.remove(PORTAL_PID_FILE)
    except Exception:
        pass

    _run(["sudo", "pkill", "-9", "dnsmasq"], check=False)
    _run(["sudo", "pkill", "-9", "hostapd"], check=False)
    _run(["sudo", "pkill", "-9", "-f", "portal.server"], check=False)
    _run(["sudo", "iptables", "-t", "nat", "-F", "PREROUTING"], check=False)
    _run(["sudo", "nmcli", "radio", "wifi", "on"], check=False)
    return "Hotspot stopped"
