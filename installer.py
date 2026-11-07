#!/usr/bin/env python3
"""TailsMusic installer for Debian/Raspberry Pi OS (non-destructive by default)."""
import argparse
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys

DEFAULT_CONFIG = {
    "okbutton": "KEY_PLAYCD",
    "okbutton2": "KEY_PAUSECD",
    "backbutton": "KEY_PREVIOUSSONG",
    "skipbutton": "KEY_NEXTSONG",
    "evtestname": "",
}


def run(*args, dry_run=False):
    print("+", " ".join(map(str, args)), flush=True)
    if not dry_run:
        subprocess.run(args, check=True)


def install(args):
    if sys.platform != "linux":
        raise RuntimeError("The installer requires Linux (Raspberry Pi OS/Debian).")
    if shutil.which("apt-get") is None:
        raise RuntimeError("apt-get not found. This installer supports Debian-based systems.")
    if os.geteuid() != 0:
        raise RuntimeError("Run the installer with sudo.")
    username = args.user or os.environ.get("SUDO_USER") or "pi"
    if username == "root":
        raise RuntimeError("Choose a non-root user with --user.")
    account = pwd.getpwnam(username)
    source = Path(__file__).resolve().parent
    target = Path(args.install_dir).expanduser().resolve() if args.install_dir else source
    if target != source:
        raise RuntimeError("Run setup.sh in the desired checkout; --install-dir must match it.")
    venv = target / ".venv"
    print(f"Install: {target}\nUser: {username}\nMode: {'Kivy + headless' if args.with_kivy else 'headless'}")
    packages = [
        "python3", "python3-venv", "python3-pip", "python3-dev",
        "python3-evdev", "python3-pygame", "python3-pulsectl",
        "espeak-ng", "pulseaudio", "pulseaudio-module-bluetooth",
        "bluez", "bluetooth", "rfkill", "network-manager",
        "libasound2-dev", "libmtdev1", "git",
    ]
    if args.with_kivy:
        packages += ["python3-kivy"]
    if args.with_hotspot:
        packages += ["hostapd", "dnsmasq"]
    if not args.skip_apt:
        run("apt-get", "update", dry_run=args.dry_run)
        run("apt-get", "install", "-y", *packages, dry_run=args.dry_run)
    else:
        print("Skipping system packages at your request.")

    # Use distro-provided libraries where possible; keep pip out of the system Python.
    run(sys.executable, "-m", "venv", "--system-site-packages", str(venv), dry_run=args.dry_run)
    pip = str(venv / "bin" / "python")
    run(pip, "-m", "pip", "install", "--upgrade", "pip", dry_run=args.dry_run)
    run(pip, "-m", "pip", "install", "requests", "bleak", dry_run=args.dry_run)
    if args.with_kivy and args.skip_apt:
        print("Note: --skip-apt requires Kivy to be already installed and importable in the venv.")
    for name in ("songs", "playlists"):
        dest = target / name
        print("+ mkdir", dest)
        if not args.dry_run:
            dest.mkdir(exist_ok=True)
    cfg = target / "config.json"
    if not cfg.exists():
        print("+ create default config.json (edit evtestname for your headset buttons)")
        if not args.dry_run:
            cfg.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n", encoding="utf-8")
    else:
        print("Preserving existing config.json.")

    if not args.dry_run:
        for name in ("songs", "playlists", ".venv"):
            path = target / name
            for base, dirs, files in os.walk(path):
                os.chown(base, account.pw_uid, account.pw_gid)
                for item in dirs + files:
                    os.chown(os.path.join(base, item), account.pw_uid, account.pw_gid)
        os.chown(cfg, account.pw_uid, account.pw_gid)

    if args.service:
        unit_name = "tailsmusic.service"
        service = f"""[Unit]
Description=TailsMusic v2 Headless Player
Wants=bluetooth.service
After=bluetooth.service sound.target network.target

[Service]
Type=simple
User={username}
WorkingDirectory={target}
ExecStart={venv}/bin/python {target}/player.py
Restart=on-failure
RestartSec=5
SupplementaryGroups=audio input
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""
        path = Path("/etc/systemd/system") / unit_name
        print("+ write", path)
        if not args.dry_run:
            path.write_text(service, encoding="utf-8")
        run("systemctl", "daemon-reload", dry_run=args.dry_run)
        run("systemctl", "enable", unit_name, dry_run=args.dry_run)
        if args.start_service:
            run("systemctl", "restart", unit_name, dry_run=args.dry_run)

    if args.with_kivy:
        desktop = Path(account.pw_dir) / ".local/share/applications/tailsmusic-kivy.desktop"
        entry = f"""[Desktop Entry]
Type=Application
Name=TailsMusic Touch
Exec={venv}/bin/python {target}/kivy_player.py
Path={target}
Terminal=false
Categories=Audio;Player;
"""
        print("+ write", desktop)
        if not args.dry_run:
            desktop.parent.mkdir(parents=True, exist_ok=True)
            desktop.write_text(entry, encoding="utf-8")
            os.chown(desktop.parent, account.pw_uid, account.pw_gid)
            os.chown(desktop, account.pw_uid, account.pw_gid)

    print("\nInstallation steps complete.")
    print("Headless player: sudo systemctl start tailsmusic" if args.service else f"Headless player: {pip} {target}/player.py")
    if args.with_kivy:
        print(f"Touchscreen UI: {pip} {target}/kivy_player.py")
        print("Stop the headless service first; both players cannot own audio playback simultaneously.")
    print("Pair headphones via bluetoothctl; set config.json evtestname for media-button input.")
    if args.dry_run:
        print("DRY RUN: no commands or filesystem changes were applied.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", help="Non-root account that owns and runs TailsMusic")
    parser.add_argument("--install-dir", help="Must be the directory containing this installer")
    parser.add_argument("--with-kivy", action="store_true", help="Install optional touchscreen GUI")
    parser.add_argument("--with-hotspot", action="store_true", help="Install optional hotspot packages")
    parser.add_argument("--skip-apt", action="store_true", help="Skip apt packages (already installed)")
    parser.add_argument("--service", action="store_true", help="Enable headless systemd service")
    parser.add_argument("--start-service", action="store_true", help="Restart headless service; implies --service")
    parser.add_argument("--dry-run", action="store_true", help="Print steps without changes")
    args = parser.parse_args()
    if args.start_service:
        args.service = True
    try:
        install(args)
    except (RuntimeError, OSError, subprocess.CalledProcessError, KeyError) as exc:
        print(f"Installation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
