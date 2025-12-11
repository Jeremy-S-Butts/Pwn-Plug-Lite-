from http.server import BaseHTTPRequestHandler, HTTPServer
from base64 import b64decode, b64encode

class C2Server(BaseHTTPRequestHandler):

    def do_GET(self):
        cookie = self.headers.get("Cookie")

        if cookie:
            try:
                # Decode inbound message
                data = b64decode(cookie).decode()
                print("[+] Received from client:", data)

                # Send server reply
                reply = b64encode(b"Message received").decode()

                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(reply.encode())

            except Exception as e:
                print("Decode error:", e)
                self.send_error(400)
        else:
            self.send_error(404, "Missing Cookie header")

# -----------------------------

if __name__ == "__main__":
    host = "0.0.0.0"
    port = 8443

    print(f"[+] Server listening on port {port}")
    webserver = HTTPServer((host, port), C2Server)

    try:
        webserver.serve_forever()
    except KeyboardInterrupt:
        pass

    webserver.server_close()
    print("[+] Server stopped.")
