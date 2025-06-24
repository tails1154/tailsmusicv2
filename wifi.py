import subprocess
def scan_wifi():
    result = subprocess.run(
        ["nmcli", "-t", "-f", "SSID,SIGNAL", "--escape", "no", "--fields", "SSID,SIGNAL", "device", "wifi", "list"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    output = result.stdout.decode().strip().split('\n')
    networks = []
    seen = set()
    for line in output:
        if line:
            parts = line.split(":")
            ssid = ":".join(parts[:-1])  # Join everything except last part for SSID
            signal = parts[-1]
            if ssid and ssid not in seen:
                seen.add(ssid)
                try:
                    networks.append((ssid, int(signal)))
                except ValueError:
                    continue
    networks.sort(key=lambda x: -x[1])
    return networks


def connect_wifi(ssid, password):
    if True:
        result = subprocess.run(
            ["nmcli", "dev", "wifi", "connect", ssid, "password", password],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("Connected successfully!")
        print(result.stdout.decode())
def get_ip():
    if True:
        result = subprocess.run(
            ["sh", "-c", 'ip route get 8.8.8.8 | awk -F"src " \'NR==1{split($2,a," ");print a[1]}\'' ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        ip_address = result.stdout.strip()
        return ip_address
  #  except subprocess.CalledProcessError as e:
    #    print("Failed to get IP address.")
   #     print(e.stderr)
     #   return None
# Example usage
#networks = scan_wifi()
#if networks:
#    print("Available Networks:")
#    for i, (ssid, signal) in enumerate(networks):
#        print(f"{i+1}. {ssid} ({signal}%)")

#    choice = int(input("Select a network number: ")) - 1
#    selected_ssid = networks[choice][0]
 #   password = input(f"Enter password for {selected_ssid}: ")

#    connect_wifi(selected_ssid, password)
#else:
#    print("No Wi-Fi networks found.")
#
