"""Loopback HTTP transport, with closed connections outside an open session."""
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .protocol import PATHS, decode, media_type, HTTPError
from .lifecycle import OPEN


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    def __init__(self, session, port):
        self.session = session
        super().__init__(('127.0.0.1', port), Handler)

    def process_request(self, request, address):
        # Reserve the port while idle, but do not expose HTTP until countdown ends.
        if self.session.state not in OPEN:
            self.shutdown_request(request)
            return
        request.settimeout(5)
        super().process_request(request, address)


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def __getattr__(self, name):
        if name.startswith('do_'):
            return self.wrong_method
        raise AttributeError(name)

    def log_message(self, *args):
        pass  # Structured request records belong to Session.record.

    def send_error(self, code, message=None, explain=None):
        self.reply(code, self.server.session.rejected())

    def reply(self, status, response):
        body = json.dumps(response, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Connection', 'close')
        if status == 405:
            self.send_header('Allow', 'POST')
        self.end_headers()
        try:
            if self.command != 'HEAD':
                self.wfile.write(body)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass  # Action was recorded; retrying its ID returns the cached response.
        self.close_connection = True

    def do_POST(self):
        session = self.server.session
        payload = {}
        try:
            if self.path not in PATHS:
                raise HTTPError(404)
            media_type(self.headers)
            sizes = self.headers.get_all('Content-Length', [])
            if len(sizes) != 1 or not sizes[0].isascii() or not sizes[0].isdigit() or self.headers.get('Transfer-Encoding') is not None:
                raise HTTPError(400)
            length = int(sizes[0])
            if length > 65536:
                raise HTTPError(413)
            body = self.rfile.read(length)
            if len(body) != length:
                raise HTTPError(400)
            payload = decode(body)
            if session.state not in OPEN:
                self.close_connection = True
                return
            status, response = session.handle(self.path, payload)
        except HTTPError as exc:
            status, response = exc.status, session.rejected()
            session.record(self.path, payload, status, response, int(session.wall()*1000))
        except (TimeoutError, ConnectionError):
            self.close_connection = True
            return
        self.reply(status, response)

    def wrong_method(self):
        self.reply(405 if self.path in PATHS else 404, self.server.session.rejected())

    do_GET = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_HEAD = do_TRACE = do_CONNECT = wrong_method


class HTTPService:
    def __init__(self, session, port):
        self.session = session
        self.server = Server(session, port)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
