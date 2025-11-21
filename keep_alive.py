import os
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


PORT = int(os.environ.get("PORT", "8080"))


class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/ping", "/health"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            payload = {"status": "ok", "path": self.path}
            self.wfile.write(json.dumps(payload).encode("utf-8"))
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "not found"}).encode("utf-8"))

    def log_message(self, format, *args):
        logging.info("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format % args))


def run():
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
    server_address = ("", PORT)
    httpd = ThreadingHTTPServer(server_address, KeepAliveHandler)
    logging.info(f"Keep-alive server listening on 0.0.0.0:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        logging.info("Keep-alive server stopped")


if __name__ == "__main__":
    run()
