"""A Language Server for 새롬.

Diagnostics, semantic tokens, formatting, completion, hover and the outline.
Nothing here runs the user's program: everything comes from lexing and parsing.
"""
import urllib.parse

from ..errors import SaeromError
from ..formatter import format_source
from .analysis import Analysis, TOKEN_MODIFIERS, TOKEN_TYPES
from .protocol import Connection

METHOD_NOT_FOUND = -32601
INTERNAL_ERROR = -32603

CAPABILITIES = {
    "textDocumentSync": {"openClose": True, "change": 1, "save": True},
    "documentFormattingProvider": True,
    "documentSymbolProvider": True,
    "hoverProvider": True,
    "completionProvider": {"triggerCharacters": ["의"], "resolveProvider": False},
    "semanticTokensProvider": {
        "legend": {"tokenTypes": TOKEN_TYPES, "tokenModifiers": TOKEN_MODIFIERS},
        "full": True,
    },
}


def uri_to_path(uri):
    if not uri.startswith("file://"):
        return None
    parsed = urllib.parse.urlparse(uri)
    return urllib.parse.unquote(parsed.path)


class Server:
    def __init__(self, connection=None):
        self.connection = connection or Connection()
        self.documents = {}
        self.analyses = {}
        self.running = True

    # --- loop ---
    def serve(self):
        while self.running:
            message = self.connection.read()
            if message is None:
                break
            self.handle(message)

    def handle(self, message):
        method = message.get("method")
        params = message.get("params") or {}
        request_id = message.get("id")
        handler = getattr(self, "on_" + method.replace("/", "_").replace("$", "dollar"),
                          None) if method else None

        if handler is None:
            if request_id is not None:
                self.connection.fail(request_id, METHOD_NOT_FOUND, f"{method} 없음")
            return
        try:
            result = handler(params)
        except SaeromError as error:
            if request_id is not None:
                self.connection.fail(request_id, INTERNAL_ERROR, error.message)
            return
        except Exception as error:                       # 서버가 죽으면 안 된다
            if request_id is not None:
                self.connection.fail(request_id, INTERNAL_ERROR, str(error))
            return
        if request_id is not None:
            self.connection.respond(request_id, result)

    # --- lifecycle ---
    def on_initialize(self, params):
        return {"capabilities": CAPABILITIES,
                "serverInfo": {"name": "saerom", "version": version()}}

    def on_initialized(self, params):
        return None

    def on_shutdown(self, params):
        self.running = False
        return None

    def on_exit(self, params):
        self.running = False
        return None

    # --- documents ---
    def on_textDocument_didOpen(self, params):
        document = params["textDocument"]
        self.update(document["uri"], document["text"])
        return None

    def on_textDocument_didChange(self, params):
        changes = params.get("contentChanges") or []
        if changes:
            self.update(params["textDocument"]["uri"], changes[-1]["text"])
        return None

    def on_textDocument_didSave(self, params):
        uri = params["textDocument"]["uri"]
        if "text" in params:
            self.update(uri, params["text"])
        return None

    def on_textDocument_didClose(self, params):
        uri = params["textDocument"]["uri"]
        self.documents.pop(uri, None)
        self.analyses.pop(uri, None)
        self.connection.notify("textDocument/publishDiagnostics",
                               {"uri": uri, "diagnostics": []})
        return None

    def update(self, uri, text):
        self.documents[uri] = text
        analysis = Analysis(uri, text, uri_to_path(uri))
        self.analyses[uri] = analysis
        self.connection.notify("textDocument/publishDiagnostics",
                               {"uri": uri, "diagnostics": analysis.diagnostics()})

    def analysis(self, params):
        return self.analyses.get(params["textDocument"]["uri"])

    # --- features ---
    def on_textDocument_semanticTokens_full(self, params):
        analysis = self.analysis(params)
        return {"data": analysis.semantic_tokens() if analysis else []}

    def on_textDocument_documentSymbol(self, params):
        analysis = self.analysis(params)
        return analysis.symbols() if analysis else []

    def on_textDocument_hover(self, params):
        analysis = self.analysis(params)
        if analysis is None:
            return None
        position = params["position"]
        text = analysis.hover(position["line"], position["character"])
        if text is None:
            return None
        return {"contents": {"kind": "markdown", "value": text}}

    def on_textDocument_completion(self, params):
        analysis = self.analysis(params)
        if analysis is None:
            return {"isIncomplete": False, "items": []}
        position = params["position"]
        return {"isIncomplete": False,
                "items": analysis.completions(position["line"], position["character"])}

    def on_textDocument_formatting(self, params):
        uri = params["textDocument"]["uri"]
        text = self.documents.get(uri)
        if text is None:
            return []
        formatted = format_source(text)
        if formatted == text:
            return []
        lines = text.split("\n")
        end = {"line": len(lines) - 1, "character": len(lines[-1])}
        return [{"range": {"start": {"line": 0, "character": 0}, "end": end},
                 "newText": formatted}]


def version():
    from .. import __version__
    return __version__


def main(argv=None):
    Server().serve()
    return 0
