#!/bin/bash
# TailsMusic v2 - Interactive Setup Script for Raspberry Pi OS
# Run with: sudo bash setup.sh

set -e

# ── Configurable defaults ──────────────────────────────────────────────
INSTALL_DIR="${INSTALL_DIR:-/home/pi/mp3player}"
MUSIC_DIR="$INSTALL_DIR/songs"
PLAYLIST_DIR="$INSTALL_DIR/playlists"
SFX_DIR="$INSTALL_DIR/sfx"
CONFIG_FILE="$INSTALL_DIR/config.json"

# ── Colours (fallback when dialog is unavailable) ──────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── Collected settings ─────────────────────────────────────────────────
BT_MAC=""
BT_NAME=""
INPUT_DEVICE_PATH=""
INPUT_DEVICE_NAME=""
OKBUTTON=""
OKBUTTON2=""
BACKBUTTON=""
SKIPBUTTON=""

# ── Helpers ────────────────────────────────────────────────────────────

msgbox() {
    dialog --title "TailsMusic Setup" --msgbox "$1" 0 0
}

yesno() {
    dialog --title "TailsMusic Setup" --yesno "$1" 0 0
}

infobox() {
    dialog --title "TailsMusic Setup" --infobox "$1" 0 0
}

inputbox() {
    dialog --title "TailsMusic Setup" --inputbox "$1" 0 0 "$2" 2>&1 1>/dev/tty
}

passwordbox() {
    dialog --title "TailsMusic Setup" --passwordbox "$1" 0 0 2>&1 1>/dev/tty
}

menu_select() {
    # $1 = prompt, $@ = options (tag item pairs)
    local prompt="$1"; shift
    local height=$(( $# / 2 + 7 ))
    [ "$height" -lt 10 ] && height=10
    [ "$height" -gt 20 ] && height=20
    dialog --title "TailsMusic Setup" --menu "$prompt" "$height" 70 $(( $# / 2 )) "$@" 2>&1 1>/dev/tty
}

gauge_update() {
    echo "$1"
    echo "###"
    echo "$2"
    echo "###"
    echo "$3"
}

# ── Step 0: Root check ─────────────────────────────────────────────────

check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        echo "This script must be run as root (use sudo)." >&2
        exit 1
    fi
}

# ── Step 1: Install dialog ─────────────────────────────────────────────

install_dialog() {
    if ! command -v dialog &>/dev/null; then
        echo "Installing dialog..."
        apt-get update -qq
        apt-get install -y -qq dialog
    fi
}

# ── Step 2: Welcome ────────────────────────────────────────────────────

welcome() {
    msgbox "Welcome to TailsMusic v2 Setup!

This wizard will guide you through setting up your Raspberry Pi
MP3 player with Bluetooth headphone support.

You will:
  - Install required system & Python packages
  - Pair your Bluetooth headphone/speaker
  - Map your media buttons
  - Optionally configure WiFi
  - Set up auto-start on boot

Press ENTER to continue."
}

# ── Step 3: Install system packages ────────────────────────────────────

install_system_packages() {
    local pct=0

    # List of system packages to install
    local PKGS=(
        pulseaudio pulseaudio-module-bluetooth
        espeak-ng
        evtest python3-evdev
        network-manager
        bluetooth bluez bluez-tools
        git
    )

    # Optional hotspot packages
    local OPT_PKGS=(hostapd dnsmasq)

    # Combine all
    local ALL_PKGS=("${PKGS[@]}" "${OPT_PKGS[@]}")

    {
        pct=10
        gauge_update "$pct" "Updating package lists..."
        apt-get update -qq 2>/dev/null

        local total=${#ALL_PKGS[@]}
        local i=0
        for pkg in "${ALL_PKGS[@]}"; do
            ((i++))
            pct=$((10 + i * 70 / total))
            gauge_update "$pct" "Installing $pkg..."
            if dpkg -s "$pkg" &>/dev/null 2>&1; then
                gauge_update "$pct" "  $pkg already installed, skipping"
            else
                apt-get install -y -qq "$pkg" 2>/dev/null || true
            fi
        done

        pct=85
        gauge_update "$pct" "Configuring PulseAudio..."
        pulseaudio --start 2>/dev/null || true

        pct=92
        gauge_update "$pct" "Enabling Bluetooth service..."
        systemctl enable bluetooth 2>/dev/null || true
        systemctl start bluetooth 2>/dev/null || true

        pct=98
        gauge_update "$pct" "Unblocking Bluetooth..."
        rfkill unblock bluetooth 2>/dev/null || true

        pct=100
        gauge_update "$pct" "System packages complete!"
        sleep 1
    } | dialog --title "TailsMusic Setup" --gauge "Preparing system packages..." 8 70 0
}

# ── Step 4: Install Python packages ────────────────────────────────────

install_python_packages() {
    local PIP_PKGS=(pygame evdev pulsectl bleak vosk sounddevice numpy gtts requests)

    {
        local pct=10
        gauge_update "$pct" "Checking pip..."

        local total=${#PIP_PKGS[@]}
        local i=0
        for pkg in "${PIP_PKGS[@]}"; do
            ((i++))
            pct=$((10 + i * 85 / total))
            local status
            if python3 -c "import $pkg" 2>/dev/null; then
                status="  $pkg already installed"
            else
                status="  Installing $pkg..."
                pip install --break-system-packages "$pkg" 2>/dev/null 1>/dev/null || true
            fi
            gauge_update "$pct" "$status"
        done

        pct=100
        gauge_update "$pct" "Python packages complete!"
        sleep 1
    } | dialog --title "TailsMusic Setup" --gauge "Installing Python packages..." 8 70 0
}

# ── Step 5: Create directories ─────────────────────────────────────────

setup_directories() {
    {
        gauge_update 20 "Creating directories..."
        mkdir -p "$MUSIC_DIR" "$PLAYLIST_DIR" "$SFX_DIR"

        gauge_update 80 "Setting permissions..."
        chown -R pi:pi "$INSTALL_DIR" 2>/dev/null || true

        gauge_update 100 "Directory setup complete!"
        sleep 1
    } | dialog --title "TailsMusic Setup" --gauge "Setting up directories..." 8 70 0
}

# ── Step 6: Bluetooth audio setup ──────────────────────────────────────

bt_scan() {
    # Pipe commands into bluetoothctl's interactive session.
    # scan on -> sleep $1 -> scan off -> devices -> exit
    local timeout="${1:-8}"
    {
        echo "power on"
        echo "agent on"
        echo "default-agent"
        echo "scan on"
        sleep "$timeout"
        echo "scan off"
        echo "devices"
        echo "exit"
    } | bluetoothctl 2>/dev/null
}

bluetooth_setup() {
    if ! yesno "Do you want to pair a Bluetooth speaker/headphone now?

(This is required for audio output)"; then
        return
    fi

    # Ensure adapter is unblocked and powered
    rfkill unblock bluetooth 2>/dev/null || true
    bluetoothctl power on 2>/dev/null || true

    local scan_output

    # Run scan in background, capturing output to a temp file
    local SCAN_FILE
    SCAN_FILE=$(mktemp)
    bt_scan 8 > "$SCAN_FILE" 2>/dev/null &
    local SCAN_PID=$!

    {
        for i in $(seq 1 10); do
            echo $((i * 10))
            sleep 0.8
        done
    } | dialog --title "TailsMusic Setup" --gauge "Scanning for Bluetooth devices... put your device in pairing mode!" 7 70

    wait "$SCAN_PID" 2>/dev/null || true
    scan_output=$(cat "$SCAN_FILE")
    rm -f "$SCAN_FILE"

    # Also grab known devices as fallback
    local known
    known=$(bluetoothctl devices 2>/dev/null || true)
    scan_output="${scan_output}${known}"

    local menu_args=()
    local seen=()
    while IFS= read -r line; do
        if [[ "$line" =~ Device[[:space:]]+([0-9A-Fa-f:]{17})[[:space:]]+(.*) ]]; then
            local mac="${BASH_REMATCH[1]}"
            local name="${BASH_REMATCH[2]}"
            [ -z "$name" ] && name="Unknown Device"
            # deduplicate by MAC
            if [[ ! " ${seen[*]} " =~ " ${mac} " ]]; then
                seen+=("$mac")
                menu_args+=("$mac" "$name")
            fi
        fi
    done <<< "$scan_output"

    if [ ${#menu_args[@]} -eq 0 ]; then
        msgbox "No Bluetooth devices found.

Troubleshooting:
  - Make sure Bluetooth is enabled (rfkill unblock bluetooth)
  - Put your device in pairing mode
  - Check 'bluetoothctl power on'

You can run setup again later to pair a device."
        return
    fi

    local chosen
    chosen=$(menu_select "Select your Bluetooth speaker/headphone:" "${menu_args[@]}")

    if [ -z "$chosen" ]; then
        msgbox "No device selected. You can pair later from the player menu."
        return
    fi

    BT_MAC="$chosen"

    # Pair, trust, connect
    {
        gauge_update 20 "Pairing with device..."
        bluetoothctl -- pair "$BT_MAC" 2>/dev/null || true
        sleep 1

        gauge_update 50 "Trusting device..."
        bluetoothctl -- trust "$BT_MAC" 2>/dev/null || true
        sleep 1

        gauge_update 80 "Connecting..."
        bluetoothctl -- connect "$BT_MAC" 2>/dev/null || true
        sleep 2

        gauge_update 100 "Bluetooth setup complete!"
        sleep 1
    } | dialog --title "TailsMusic Setup" --gauge "Pairing Bluetooth device..." 8 70 0

    # Get the device name
    BT_NAME=$(bluetoothctl info "$BT_MAC" 2>/dev/null | grep "Name:" | sed 's/.*Name: //')

    # Set PulseAudio default sink
    infobox "Waiting for audio profile..." 3 40
    sleep 3

    local sink_name
    sink_name=$(pactl list short sinks 2>/dev/null | grep "${BT_MAC//:/_}" | head -1 | awk '{print $2}')
    if [ -n "$sink_name" ]; then
        pactl set-default-sink "$sink_name" 2>/dev/null || true
        msgbox "Bluetooth audio configured!

Device: $BT_NAME ($BT_MAC)
Audio sink: $sink_name"
    else
        msgbox "Bluetooth paired, but couldn't auto-detect the audio sink.
The audio sink will be detected automatically when the player starts.

Device: $BT_NAME ($BT_MAC)"
    fi
}

# ── Step 7: Input device detection ─────────────────────────────────────

input_device_setup() {
    if [ -z "$BT_MAC" ]; then
        if ! yesno "No Bluetooth device paired. Do you want to configure
an input device for button controls anyway?"; then
            return
        fi
    fi

    infobox "Detecting input devices..." 3 40
    sleep 1

    # List /dev/input/event* devices and get their names
    local menu_args=()
    for dev in /dev/input/event*; do
        if [ -e "$dev" ]; then
            local name
            name=$(cat "/sys/class/input/$(basename "$dev")/device/name" 2>/dev/null || echo "Unknown")
            menu_args+=("$dev" "$name")
        fi
    done

    if [ ${#menu_args[@]} -eq 0 ]; then
        msgbox "No input devices found in /dev/input/.
Make sure your Bluetooth device is connected and has media buttons."
        return
    fi

    local chosen
    chosen=$(menu_select "Select the input device for button controls
(usually your Bluetooth headphone with media buttons):" "${menu_args[@]}")

    if [ -z "$chosen" ]; then
        msgbox "No input device selected."
        return
    fi

    INPUT_DEVICE_PATH="$chosen"
    INPUT_DEVICE_NAME=$(cat "/sys/class/input/$(basename "$chosen")/device/name" 2>/dev/null || echo "Unknown")

    msgbox "Input device selected:
$INPUT_DEVICE_NAME
$INPUT_DEVICE_PATH"
}

# ── Step 8: Button mapping ─────────────────────────────────────────────

button_mapping() {
    if [ -z "$INPUT_DEVICE_PATH" ]; then
        if ! yesno "No input device selected. Do you want to
configure buttons anyway?"; then
            return
        fi
        # Re-prompt for device
        input_device_setup
        if [ -z "$INPUT_DEVICE_PATH" ]; then
            return
        fi
    fi

    capture_button() {
        local prompt="$1"
        local keycode=""

        dialog --title "TailsMusic Setup" --msgbox "$prompt

Press the button NOW on your device.
You have 10 seconds..." 8 60

        # Capture the next button press using evtest
        keycode=$(timeout 10 evtest --grab "$INPUT_DEVICE_PATH" 2>/dev/null \
            | grep -m1 "value 1" \
            | grep -oP '\(KEY_\w+\)' \
            | tr -d '()' \
            || true)

        if [ -z "$keycode" ]; then
            dialog --title "TailsMusic Setup" --msgbox "No button press detected.
Skipping this button." 6 50
            echo ""
        else
            dialog --title "TailsMusic Setup" --msgbox "Detected: $keycode" 6 50
            echo "$keycode"
        fi
    }

    msgbox "Now we will map each button on your device.
Follow the prompts and press the corresponding button
when asked." 8 50

    OKBUTTON=$(capture_button "Press the PLAY/PAUSE or OK button")
    if [ -n "$OKBUTTON" ]; then
        OKBUTTON2=$(capture_button "Press the ALTERNATE OK button
(e.g., STOP, or press the same button again if you only have one OK button)")
    fi
    BACKBUTTON=$(capture_button "Press the BACK (previous) button")
    SKIPBUTTON=$(capture_button "Press the SKIP (forward) button")
}

# ── Step 9: WiFi setup ─────────────────────────────────────────────────

wifi_setup() {
    if ! command -v nmcli &>/dev/null; then
        msgbox "NetworkManager (nmcli) is not available. Skipping WiFi setup."
        return
    fi

    if ! yesno "Do you want to configure WiFi now?"; then
        return
    fi

    infobox "Scanning for WiFi networks..." 3 50
    # Ensure wifi radio is on
    nmcli radio wifi on 2>/dev/null || true
    sleep 2

    local ssids
    ssids=$(nmcli -t -f SSID,SIGNAL --escape no device wifi list 2>/dev/null \
        | sort -t: -k2 -nr \
        | awk -F: '!seen[$1]++ {print $1, "(" $2 "%)"}' \
        || true)

    if [ -z "$ssids" ]; then
        msgbox "No WiFi networks found."
        return
    fi

    local menu_args=()
    while IFS= read -r line; do
        local ssid="${line%% (*}"
        local sig="${line##*(}"
        sig="${sig%)}"
        [ -z "$ssid" ] && continue
        menu_args+=("$ssid" "Signal: $sig%")
    done <<< "$ssids"

    local chosen
    chosen=$(menu_select "Select a WiFi network:" "${menu_args[@]}")

    if [ -z "$chosen" ]; then
        msgbox "No network selected."
        return
    fi

    local pwd
    pwd=$(passwordbox "Enter the WiFi password for '$chosen':")

    if [ -z "$pwd" ]; then
        msgbox "No password entered. Skipping WiFi setup."
        return
    fi

    {
        gauge_update 30 "Connecting to $chosen..."
        nmcli dev wifi connect "$chosen" password "$pwd" 2>/dev/null 1>/dev/null || true
        sleep 2

        gauge_update 100 "WiFi setup complete!"
        sleep 1
    } | dialog --title "TailsMusic Setup" --gauge "Connecting to WiFi..." 7 70 0

    # Verify connection
    if nmcli -t -f GENERAL.STATE device show wlan0 2>/dev/null | grep -q "connected"; then
        local ip
        ip=$(ip route get 8.8.8.8 2>/dev/null | awk '{print $7; exit}')
        msgbox "Connected to '$chosen'
IP address: ${ip:-unknown}"
    else
        msgbox "WiFi connection may have failed.
Check your password and try again."
    fi
}

# ── Step 10: Generate config.json ──────────────────────────────────────

generate_config() {
    # If button mapping didn't set all buttons, provide sensible defaults
    [ -z "$OKBUTTON" ] && OKBUTTON="KEY_PLAYPAUSE"
    [ -z "$OKBUTTON2" ] && OKBUTTON2="KEY_STOP"
    [ -z "$BACKBUTTON" ] && BACKBUTTON="KEY_PREVIOUSSONG"
    [ -z "$SKIPBUTTON" ] && SKIPBUTTON="KEY_NEXTSONG"
    [ -z "$INPUT_DEVICE_NAME" ] && INPUT_DEVICE_NAME="SIMOLIO"

    # Ask for evtestname
    local evname
    evname=$(inputbox "Enter the evtestname (substring to match your input device name).
This is used to find your headphone buttons at startup.

Current name: $INPUT_DEVICE_NAME
(usually part of the device name is enough)" "$INPUT_DEVICE_NAME")

    if [ -n "$evname" ]; then
        INPUT_DEVICE_NAME="$evname"
    fi

    # Generate config
    cat > "$CONFIG_FILE" << EOF
{
    "okbutton": "$OKBUTTON",
    "okbutton2": "$OKBUTTON2",
    "backbutton": "$BACKBUTTON",
    "skipbutton": "$SKIPBUTTON",
    "evtestname": "$INPUT_DEVICE_NAME"
}
EOF

    chown pi:pi "$CONFIG_FILE" 2>/dev/null || true

    msgbox "Configuration saved to $CONFIG_FILE

okbutton:     $OKBUTTON
okbutton2:    $OKBUTTON2
backbutton:   $BACKBUTTON
skipbutton:   $SKIPBUTTON
evtestname:   $INPUT_DEVICE_NAME"
}

# ── Step 11: Auto-start setup (bashrc) ─────────────────────────────────

setup_autostart() {
    if ! yesno "Do you want TailsMusic to start automatically
on boot (via ~/.bashrc)?"; then
        return
    fi

    local BASHRC="/home/pi/.bashrc"
    local BASHRC_BAK="/home/pi/.bashrc.backup.tailsmusic"

    # Backup existing bashrc
    if [ -f "$BASHRC" ]; then
        cp "$BASHRC" "$BASHRC_BAK"
    fi

    cat > "$BASHRC" << 'INNEREOF'
# ~/.bashrc: executed by bash(1) for non-login shells.
case $- in
    *i*) ;;
      *) return;;
esac
HISTCONTROL=ignoreboth
shopt -s histappend
HISTSIZE=1000
HISTFILESIZE=2000
shopt -s checkwinsize
if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi
case "$TERM" in
    xterm-color|*-256color) color_prompt=yes;;
esac
force_color_prompt=yes
if [ -n "$force_color_prompt" ]; then
    if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
        color_prompt=yes
    else
        color_prompt=
    fi
fi
if [ "$color_prompt" = yes ]; then
    PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w \$\[\033[00m\] '
else
    PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '
fi
unset color_prompt force_color_prompt
case "$TERM" in
xterm*|rxvt*)
    PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
    ;;
*)
    ;;
esac
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi
if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi
INNEREOF

    # Append TailsMusic auto-start
    cat >> "$BASHRC" << EOF
# ── TailsMusic v2 auto-start ────────────────────────────────────────
echo "TailsMusic starting in 2 seconds... Press Ctrl-C for terminal."
sleep 2
while true; do
    echo "Connecting Bluetooth..."
EOF

    if [ -n "$BT_MAC" ]; then
        cat >> "$BASHRC" << EOF
    sudo bluetoothctl connect $BT_MAC 2>/dev/null
    while [ "\$?" != "0" ]; do
        echo "Retrying Bluetooth..."
        sleep 1
        sudo bluetoothctl connect $BT_MAC 2>/dev/null
    done
EOF
    fi

    cat >> "$BASHRC" << EOF
    sleep 1
EOF

    if [ -n "$BT_MAC" ]; then
        cat >> "$BASHRC" << EOF
    pactl set-default-sink bluez_sink.${BT_MAC//:/_}.a2dp_sink 2>/dev/null || true
EOF
    fi

    cat >> "$BASHRC" << EOF
    echo "Starting TailsMusic..."
    sudo pkill -9 -f portal.server 2>/dev/null
    sleep 0.5
    cd $INSTALL_DIR
    echo "=== tailsmusic started \$(date) ===" >> tailsmusic.log
    PYTHONUNBUFFERED=1 python3 player.py >> tailsmusic.log 2>&1
    cd
done
EOF

    chown pi:pi "$BASHRC" 2>/dev/null || true

    msgbox "Auto-start configured in $BASHRC

TailsMusic will start automatically on login.
A backup of your original bashrc was saved to $BASHRC_BAK"
}

# ── Step 12: Summary & Finish ──────────────────────────────────────────

finish() {
    local summary=""
    summary+="TailsMusic v2 Setup Complete!\n\n"
    summary+="Install directory:  $INSTALL_DIR\n"
    summary+="Config file:        $CONFIG_FILE\n\n"
    summary+="okbutton:     ${OKBUTTON:-not set}\n"
    summary+="okbutton2:    ${OKBUTTON2:-not set}\n"
    summary+="backbutton:   ${BACKBUTTON:-not set}\n"
    summary+="skipbutton:   ${SKIPBUTTON:-not set}\n"
    summary+="evtestname:   ${INPUT_DEVICE_NAME:-not set}\n\n"

    if [ -n "$BT_MAC" ]; then
        summary+="Bluetooth:    ${BT_NAME:-Unknown} ($BT_MAC)\n\n"
    else
        summary+="Bluetooth:    not configured\n\n"
    fi

    summary+="Place your .mp3 files in:\n"
    summary+="  $MUSIC_DIR\n\n"
    summary+="To start manually:  cd $INSTALL_DIR && python3 player.py\n"
    summary+="To reconfigure:     sudo bash $INSTALL_DIR/setup.sh\n\n"
    summary+="Reboot your Pi to test the auto-start setup!"

    dialog --title "TailsMusic Setup" --msgbox "$summary" 22 70

    clear
    echo -e "${GREEN}=== TailsMusic v2 Setup Complete ===${NC}"
    echo ""
    echo "Install directory:  $INSTALL_DIR"
    echo "Config file:        $CONFIG_FILE"
    echo ""
    echo "Place .mp3 files in: $MUSIC_DIR"
    echo ""
    echo "To start manually:  cd $INSTALL_DIR && python3 player.py"
    echo "To reconfigure:     sudo bash $INSTALL_DIR/setup.sh"
    echo ""
    echo "Reboot to test auto-start."
}

# ── Full guided workflow ───────────────────────────────────────────────

full_setup() {
    welcome
    install_system_packages
    install_python_packages
    setup_directories
    bluetooth_setup
    input_device_setup
    button_mapping
    wifi_setup
    generate_config
    setup_autostart
    finish
}

# ── Main menu ──────────────────────────────────────────────────────────

main_menu() {
    while true; do
        local choice
        choice=$(menu_select "TailsMusic v2 - Setup Menu" \
            "full"     "Full guided setup (recommended)" \
            "pkgs"     "Install system packages only" \
            "pip"      "Install Python packages only" \
            "files"    "Create required directories" \
            "bt"       "Pair Bluetooth device" \
            "input"    "Configure input device & buttons" \
            "wifi"     "Configure WiFi" \
            "config"   "Generate/update config.json" \
            "autostart" "Setup auto-start on boot" \
            "quit"     "Exit setup")

        case "$choice" in
            full)
                full_setup
                return
                ;;
            pkgs)
                install_system_packages
                ;;
            pip)
                install_python_packages
                ;;
            files)
                setup_directories
                ;;
            bt)
                bluetooth_setup
                ;;
            input)
                input_device_setup
                button_mapping
                generate_config
                ;;
            wifi)
                wifi_setup
                ;;
            config)
                generate_config
                ;;
            autostart)
                setup_autostart
                ;;
            quit|"")
                clear
                echo "Setup cancelled."
                return
                ;;
        esac
    done
}

# ── Entry point ────────────────────────────────────────────────────────

check_root
install_dialog

if [ "$1" = "--full" ] || [ "$1" = "-f" ]; then
    full_setup
else
    main_menu
fi
