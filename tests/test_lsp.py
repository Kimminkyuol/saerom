import io
import json
import unittest

from saerom.lsp.analysis import Analysis, TOKEN_TYPES
from saerom.lsp.protocol import Connection
from saerom.lsp.server import Server

SOURCE = ('학생은 이런 것이다:\n'
          '    이름은 문자열이다.\n'
          '\n'
          '학생의 소개하는 것은:\n'
          '    학생의 이름을 돌려준다.  # 주석\n'
          '\n'
          '철수는 이름이 "김철수"인 학생이다.\n'
          '"{철수의 소개한 값}"을 출력한다.\n')


def frame(messages):
    out = io.BytesIO()
    for message in messages:
        body = json.dumps(message, ensure_ascii=False).encode("utf-8")
        out.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
    out.seek(0)
    return out


def talk(messages):
    """Run a scripted session and return everything the server sent back."""
    written = io.BytesIO()
    Server(Connection(frame(messages), written)).serve()
    raw = written.getvalue()
    out, index = [], 0
    while True:
        head = raw.find(b"\r\n\r\n", index)
        if head < 0:
            return out
        header = raw[index:head].decode("ascii")
        length = int(header.split(":")[1])
        body = raw[head + 4:head + 4 + length]
        out.append(json.loads(body.decode("utf-8")))
        index = head + 4 + length


def open_document(text=SOURCE, uri="file:///tmp/x.sr"):
    return [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "textDocument/didOpen",
         "params": {"textDocument": {"uri": uri, "languageId": "saerom",
                                     "version": 1, "text": text}}},
    ]


def request(method, params, request_id=2):
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}


DOC = {"textDocument": {"uri": "file:///tmp/x.sr"}}


class Session(unittest.TestCase):
    def test_initialize_advertises_capabilities(self):
        reply = talk(open_document())[0]
        capabilities = reply["result"]["capabilities"]
        self.assertTrue(capabilities["documentFormattingProvider"])
        self.assertIn("semanticTokensProvider", capabilities)
        self.assertEqual(
            capabilities["semanticTokensProvider"]["legend"]["tokenTypes"], TOKEN_TYPES)

    def test_unknown_method_is_answered_not_fatal(self):
        replies = talk(open_document() + [request("textDocument/nonsense", DOC)])
        self.assertIn("error", replies[-1])

    def test_clean_document_has_no_diagnostics(self):
        replies = talk(open_document())
        published = [m for m in replies if m.get("method") == "textDocument/publishDiagnostics"]
        self.assertEqual(published[-1]["params"]["diagnostics"], [])

    def test_syntax_error_reports_where(self):
        replies = talk(open_document("수는 1이다.\n만약 수가 1이면\n    참\n"))
        published = [m for m in replies if m.get("method") == "textDocument/publishDiagnostics"]
        problems = published[-1]["params"]["diagnostics"]
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0]["code"], "구문 오류")

    def test_unknown_verb_is_flagged_without_running(self):
        replies = talk(open_document("수는 1이다.\n수를 출려한다.\n"))
        published = [m for m in replies if m.get("method") == "textDocument/publishDiagnostics"]
        problems = published[-1]["params"]["diagnostics"]
        self.assertEqual([p["message"] for p in problems],
                         ["동사 '출려하다' 정의되지 않음"])

    def test_formatting_returns_one_edit(self):
        replies = talk(open_document("목록를 정렬한다.\n") + [request("textDocument/formatting", DOC)])
        edits = replies[-1]["result"]
        self.assertEqual(len(edits), 1)
        self.assertEqual(edits[0]["newText"], "목록을 정렬한다.\n")

    def test_formatting_a_clean_file_changes_nothing(self):
        replies = talk(open_document("목록을 정렬한다.\n") + [request("textDocument/formatting", DOC)])
        self.assertEqual(replies[-1]["result"], [])

    def test_hover_on_a_verb_lists_signatures(self):
        params = dict(DOC, position={"line": 4, "character": 12})   # 돌려준다
        replies = talk(open_document() + [request("textDocument/hover", params)])
        self.assertIn("돌려주다", replies[-1]["result"]["contents"]["value"])

    def test_document_symbols(self):
        replies = talk(open_document() + [request("textDocument/documentSymbol", DOC)])
        names = [symbol["name"] for symbol in replies[-1]["result"]]
        self.assertIn("학생", names)
        self.assertIn("소개하다", names)
        self.assertIn("철수", names)


class SemanticTokens(unittest.TestCase):
    def spans(self, text):
        analysis = Analysis("file:///tmp/x.sr", text)
        data = analysis.semantic_tokens()
        out, line, char = [], 0, 0
        for index in range(0, len(data), 5):
            delta_line, delta_char, length, kind, _ = data[index:index + 5]
            line += delta_line
            char = delta_char if delta_line else char + delta_char
            out.append((line, char, length, TOKEN_TYPES[kind]))
        return out

    def test_name_and_particle_are_separate(self):
        """정규식으로는 못 하는 일: 반복횟수 + 는 을 갈라 칠한다."""
        self.assertEqual(self.spans("반복횟수는 0이다.")[:4],
                         [(0, 0, 4, "variable"), (0, 4, 1, "particle"),
                          (0, 6, 1, "number"), (0, 7, 2, "ending")])

    def test_verb_splits_into_stem_and_ending(self):
        self.assertEqual(self.spans("수를 출력한다.")[2:],
                         [(0, 3, 2, "function"), (0, 5, 2, "ending")])

    def test_irregular_verb_stays_whole(self):
        """'뺀' 은 어간과 어미가 한 글자에 녹아 있어 나눌 수 없다."""
        self.assertIn((0, 7, 1, "function"), self.spans("3에서 1을 뺀 값"))

    def test_comment(self):
        self.assertIn((0, 10, 4, "comment"), self.spans("수를 출력한다.  # 주석"))

    def test_inside_interpolation_is_code(self):
        spans = self.spans('"{수를 출력한 값}"을 출력한다.')
        self.assertIn((0, 1, 1, "embedded"), spans)      # 여는 중괄호
        self.assertIn((0, 2, 1, "variable"), spans)
        self.assertIn((0, 3, 1, "particle"), spans)

    def test_spans_never_overlap(self):
        """시맨틱 토큰은 겹치면 안 된다."""
        spans = self.spans('"안녕 {이름}님"을 출력한다.\n수를 출력한다.')
        for before, after in zip(spans, spans[1:]):
            if before[0] == after[0]:
                self.assertLessEqual(before[1] + before[2], after[1])

    def test_deltas_never_go_backwards(self):
        data = Analysis("file:///tmp/x.sr", SOURCE).semantic_tokens()
        self.assertEqual(len(data) % 5, 0)
        for index in range(0, len(data), 5):
            self.assertGreaterEqual(data[index], 0)
            self.assertGreaterEqual(data[index + 1], 0)
            self.assertGreater(data[index + 2], 0)


class Completion(unittest.TestCase):
    def items(self, text, line, character):
        return Analysis("file:///tmp/x.sr", text).completions(line, character)

    def test_offers_the_right_particle_first(self):
        """'목록' 뒤에는 '을', '숫자' 뒤에는 '를' 을 제안한다."""
        labels = [i["label"] for i in self.items("목록", 0, 2)]
        self.assertIn("목록을", labels)
        self.assertNotIn("목록를", labels)
        labels = [i["label"] for i in self.items("숫자", 0, 2)]
        self.assertIn("숫자를", labels)

    def test_riul_takes_ro(self):
        labels = [i["label"] for i in self.items("파일", 0, 2)]
        self.assertIn("파일로", labels)
        self.assertNotIn("파일으로", labels)

    def test_offers_declared_names_and_verbs(self):
        labels = [i["label"] for i in self.items(SOURCE + "\n", 8, 0)]
        self.assertIn("철수", labels)
        self.assertIn("소개하다", labels)
        self.assertIn("출력하다", labels)
        self.assertIn("만약", labels)


if __name__ == "__main__":
    unittest.main()
