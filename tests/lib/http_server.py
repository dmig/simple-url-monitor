"""
    Testing HTTP server
    A simple implementation inspired by httpbin.org
"""
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from socket import socket
import time
from typing import Any
from urllib.parse import urlparse


# pylint:disable=C0115,C0116
class DelayingRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # pylint:disable=C0103
        path: str = urlparse(self.path).path
        code = 200
        if path.startswith('/status/'):
            try:
                code = int(path[8:])  # skip /status/
            except ValueError:
                pass

        try:
            message, explain = self.responses[code]
        except KeyError:
            message, explain = 'test', 'test content'

        self.log_error("code %d, message %s", code, message)
        self.send_response(code, message)
        self.send_header('Connection', 'close')

        # Message body is omitted for cases described in:
        #  - RFC7230: 3.3. 1xx, 204(No Content), 304(Not Modified)
        #  - RFC7231: 6.3.6. 205(Reset Content)
        body = None
        if (code >= 200 and
            code not in (HTTPStatus.NO_CONTENT,
                         HTTPStatus.RESET_CONTENT,
                         HTTPStatus.NOT_MODIFIED)):
            # HTML encode to prevent Cross Site Scripting attacks
            # (see bug #1100201)
            content = (self.error_message_format % {
                'code': code,
                'message': message,
                'explain': explain
            })
            body = content.encode('UTF-8', 'replace')
            self.send_header("Content-Type", self.error_content_type)
            self.send_header('Content-Length', str(len(body)))
        self.end_headers()

        if self.server.response_delay:  # type:ignore
            time.sleep(self.server.response_delay / 1000)  # type:ignore

        if body:
            self.wfile.write(body)


class DelayingHTTPServer(HTTPServer):
    def __init__(self, host: str, port: int,
                 ttfb_delay: int = 0, response_delay: int = 0) -> None:
        super().__init__((host, port), DelayingRequestHandler, True)
        self.ttfb_delay = ttfb_delay
        self.response_delay = response_delay

    def process_request(self, request: socket | tuple[bytes, socket], client_address: Any) -> None:
        if self.ttfb_delay:
            time.sleep(self.ttfb_delay / 1000)
        return super().process_request(request, client_address)
