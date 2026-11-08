#!/usr/bin/env python3
"""TailsMusic installer for Debian/Raspberry Pi OS (non-destructive by default)."""
import argparse
import json
import grp
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
    try:
        account = pwd.getpwnam(username)
    except KeyError as exc:
        raise RuntimeError(f"User {username!r} does not exist; pass --user LOGIN") from exc
    source = Path(__file__).resolve().parent
    target = Path(args.install_dir).expanduser().resolve() if args.install_dir else source
    if target != source:
        raise RuntimeError("Run setup.sh in the desired checkout; --install-dir must match it.")
    venv = target / ".venv"
    print(f"Install: {target}\nUser: {username}\nMode: {'Kivy + headless' if args.with_kivy else 'headless'}")
    packages = [
        "python3", "python3-venv", "python3-pip", "python3-dev",
        "python3-evdev", "python3-pygame",
        "espeak-ng", "pulseaudio", "pulseaudio-module-bluetooth",
        "bluez", "bluetooth", "rfkill", "network-manager",
        "libasound2-dev", "libmtdev1", "git", "sudo", "iproute2", "dbus-user-session",
    ]
    if args.with_kivy:
        # SDL2 KMS/DRM enables Kivy directly on the Linux console.
        packages += ["python3-kivy", "libdrm2", "libgbm1", "libsdl2-2.0-0"]
    if args.with_hotspot:
        print("Hotspot uses NetworkManager hotspot sharing; no global hostapd/dnsmasq management.")
    if not args.skip_apt:
        run("apt-get", "update", dry_run=args.dry_run)
        run("apt-get", "install", "-y", *packages, dry_run=args.dry_run)
    else:
        print("Skipping system packages at your request.")

    # Use distro-provided libraries where possible; keep pip out of the system Python.
    run(sys.executable, "-m", "venv", "--system-site-packages", str(venv), dry_run=args.dry_run)
    pip = str(venv / "bin" / "python")
    run(pip, "-m", "pip", "install", "--upgrade", "pip", dry_run=args.dry_run)
    run(pip, "-m", "pip", "install", "-r", str(target / "requirements.txt"), dry_run=args.dry_run)
    if not args.dry_run:
        modules = ["pygame", "evdev", "pulsectl", "requests", "bleak", "gtts"]
        if args.with_kivy:
            modules.append("kivy")
        for module in modules:
            run(pip, "-c", f"import {module}; print({module!r}, 'OK')")
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
        # User units inherit the logged-in user's PulseAudio/PipeWire session.
        # A system unit with User= is NOT a substitute for an audio user session.
        uid = account.pw_uid
        unit_name = "tailsmusic.service"
        unit_dir = Path(account.pw_dir) / ".config/systemd/user"
        unit = unit_dir / unit_name
        service = f"""[Unit]
Description=TailsMusic v2 Headless Player
Wants=bluetooth.target
After=bluetooth.target

[Service]
Type=simple
WorkingDirectory={target}
ExecStart={venv}/bin/python {target}/player.py
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
"""
        print("+ write", unit)
        if not args.dry_run:
            unit_dir.mkdir(parents=True, exist_ok=True)
            unit.write_text(service, encoding="utf-8")
            for path in (unit_dir.parent, unit_dir, unit):
                os.chown(path, uid, account.pw_gid)
        # Users need read access to /dev/input/event* for headset controls.
        # Membership takes effect on a new login.
        for group in ("input", "audio"):
            run("usermod", "-aG", group, username, dry_run=args.dry_run)
        run("loginctl", "enable-linger", username, dry_run=args.dry_run)
        run("systemctl", "start", f"user@{uid}.service", dry_run=args.dry_run)
        def userctl(*command):
            return run("runuser", "-u", username, "--", "env",
                       f"XDG_RUNTIME_DIR=/run/user/{uid}",
                       f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/bus",
                       "systemctl", "--user", *command, dry_run=args.dry_run)
        userctl("daemon-reload")
        userctl("enable", unit_name)
        if args.start_service:
            userctl("restart", unit_name)

    if args.with_kivy:
        # Console KMS/DRM needs access to the GPU node and the active VT.
        # Keep the groups conditional for Debian derivatives without one.
        for group in ("video", "render"):
            try:
                grp.getgrnam(group)
            except KeyError:
                print(f"Note: optional {group} group is absent")
            else:
                run("usermod", "-aG", group, username, dry_run=args.dry_run)

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
    print(f"Headless player: systemctl --user start tailsmusic (as {username})" if args.service else f"Headless player: {pip} {target}/player.py")
    if args.with_kivy:
        print(f"Touchscreen UI (direct KMS/DRM on a local text console): {pip} {target}/kivy_player.py")
        print("Run from a local Pi TTY, not SSH; no X11 or startx is required.")
        print("SDL2 must be built with the kmsdrm driver and DRM display access is required.")
        print("Stop the headless service first; both players cannot own audio playback simultaneously.")
    print("Pair headphones via bluetoothctl; set config.json evtestname for media-button input.")
    print("NOTE: start the user audio service (PulseAudio/PipeWire), connect headset and check pactl info.")
    print("NOTE: reopen your login session after installer adds the input/audio groups.")
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
