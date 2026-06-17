"""Servidor local para Datara con UTF-8 forzado y redirect a upload.html."""
import http.server
import os

SCREENS_DIR = os.path.join(os.path.dirname(__file__), "screens")

class DataraHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SCREENS_DIR, **kwargs)

    def send_head(self):
        if self.path == "/":
            self.send_response(301)
            self.send_header("Location", "/upload.html")
            self.end_headers()
            return None
        return super().send_head()

    def guess_type(self, path):
        ctype = super().guess_type(path)
        if ctype == "text/html":
            return "text/html; charset=utf-8"
        if ctype == "text/css":
            return "text/css; charset=utf-8"
        if ctype == "application/javascript":
            return "application/javascript; charset=utf-8"
        return ctype

if __name__ == "__main__":
    port = 8000
    server = http.server.HTTPServer(("0.0.0.0", port), DataraHandler)
    print(f"Datara Dev Server -> http://localhost:{port}")
    print(f"Sirviendo: {SCREENS_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
