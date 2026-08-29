"""Minimal JSON-RPC framing for the Language Server Protocol.

Positions are UTF-16 code units in LSP. Hangul syllables and ASCII are all in
the BMP, so a Python character index and a UTF-16 index agree for any source
this language accepts; surrogate pairs would need conversion.
"""
import json
import sys


class Connection:
    def __init__(self, reader=None, writer=None):
        self.reader = reader or sys.stdin.buffer
        self.writer = writer or sys.stdout.buffer

    def read(self):
        """Read one message. Returns None at end of stream."""
        length = 0
        while True:
            line = self.reader.readline()
            if not line:
                return None
            line = line.strip()
            if not line:
                break
            name, _, value = line.decode("ascii", "replace").partition(":")
            if name.strip().lower() == "content-length":
                length = int(value.strip())
        if not length:
            return None
        return json.loads(self.reader.read(length).decode("utf-8"))

    def write(self, message):
        body = json.dumps(message, ensure_ascii=False).encode("utf-8")
        self.writer.write(b"Content-Length: %d\r\n\r\n" % len(body))
        self.writer.write(body)
        self.writer.flush()

    def respond(self, request_id, result):
        self.write({"jsonrpc": "2.0", "id": request_id, "result": result})

    def fail(self, request_id, code, message):
        self.write({"jsonrpc": "2.0", "id": request_id,
                    "error": {"code": code, "message": message}})

    def notify(self, method, params):
        self.write({"jsonrpc": "2.0", "method": method, "params": params})
