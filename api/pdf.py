# -*- coding: utf-8 -*-
"""POST /api/pdf — 생성된 워크북을 PDF 로 내려받는다.

브라우저는 화면에 띄운 결과(doc.grades[grade])를 그대로 보내고,
서버가 docs/layout_spec.md 의 고정 양식으로 PDF 를 만들어 돌려준다.

**PDF 를 서버에서 만드는 이유** — 헤더의 "Past Test · {출제 학원명}" 때문이다.
학원명은 주제 DB 보호를 위해 브라우저로 내보내지 않는다(api/topics.py 참조).
서버에서 만들면 학원명을 노출하지 않고도 헤더에 찍을 수 있다.

크레딧은 차감하지 않는다. 생성 시점에 이미 1크레딧을 받았고 PDF 자체의
추가 원가는 사실상 0이다. (docs/layout_spec.md 구현 노트 8장)

요청 : {"topic_no": 1, "grade": "Grade 1-2", "topic": "...", "area": "...",
        "custom": false, "data": { ...해당 학년 생성 결과... }}
응답 : 200 application/pdf
       4xx/5xx {"error": "..."}
"""

import json
import os
import re
import sys
import time
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _guard      # noqa: E402
import _workbook   # noqa: E402
from _topics_full import TOPICS_BY_NO  # noqa: E402

MAX_BODY = 200_000                      # 워크북 1건은 넉넉히 이 안에 들어간다
MAX_PER_HOUR = int(os.environ.get("PDF_TRIES_HOURLY", "40"))
_hits = {}

# 학년별로 반드시 있어야 하는 키. 없으면 렌더링 중에 터지므로 미리 막는다.
REQUIRED = {
    "Grade 1-2": ("brain", "outline", "keywords", "patterns", "essay"),
    "Grade 3-4": ("brain", "outline", "vocab", "trans", "essay"),
    "Grade 5-6": ("matrix", "vocab", "essay_paras"),
}


def _rate_limited(key):
    now = time.time()
    seen = [t for t in _hits.get(key, []) if t > now - 3600]
    if len(seen) >= MAX_PER_HOUR:
        _hits[key] = seen
        return True
    seen.append(now)
    _hits[key] = seen
    if len(_hits) > 3000:
        for k in [k for k, v in _hits.items() if not v or v[-1] < now - 3600]:
            _hits.pop(k, None)
    return False


def _word_count(text):
    """app.js 의 wordCount() 와 같은 규칙. 화면 수치와 어긋나면 안 된다."""
    return len(re.findall(r"[A-Za-z0-9'’-]+", text or ""))


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            _guard._check_origin(self.headers)
        except _guard.Rejected as rej:
            return self._json(rej.status, {"error": rej.message})

        if _rate_limited(_guard.ip_hash(self.headers)):
            return self._json(429, {
                "error": "내려받기 요청이 너무 많습니다. 잠시 후 다시 시도해 주십시오."
            }, retry_after=600)

        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._json(400, {"error": "요청 본문 길이를 읽을 수 없습니다."})
        if length <= 0:
            return self._json(400, {"error": "요청 본문이 비어 있습니다."})
        if length > MAX_BODY:
            return self._json(413, {"error": "요청이 너무 큽니다."})

        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return self._json(400, {"error": "요청 형식이 올바르지 않습니다."})
        if not isinstance(payload, dict):
            return self._json(400, {"error": "요청 본문은 JSON 객체여야 합니다."})

        grade = payload.get("grade")
        data = payload.get("data")
        if grade not in REQUIRED:
            return self._json(400, {"error": "학년 정보가 올바르지 않습니다."})
        if not isinstance(data, dict):
            return self._json(400, {"error": "생성 결과가 없습니다. 먼저 에세이를 생성해 주십시오."})

        missing = [k for k in REQUIRED[grade] if not data.get(k)]
        if missing:
            return self._json(400, {
                "error": f"생성 결과가 완전하지 않습니다. ({', '.join(missing)}) 다시 생성해 주십시오."
            })

        doc = self._compose(payload, grade, data)

        try:
            pdf = _workbook.render(doc, grade)
        except RuntimeError as exc:            # 폰트 누락 등 서버 설정 문제
            return self._json(500, {"error": f"PDF 서식을 준비하지 못했습니다. ({exc})"})
        except Exception:
            return self._json(500, {"error": "PDF 를 만들지 못했습니다. 다시 시도해 주십시오."})

        name = _workbook.filename(doc, grade)
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Length", str(len(pdf)))
        # 한글이 섞일 수 있으므로 RFC 5987 형식을 함께 보낸다.
        ascii_name = re.sub(r"[^\x20-\x7E]", "_", name)
        self.send_header(
            "Content-Disposition",
            f'attachment; filename="{ascii_name}"; '
            f"filename*=UTF-8''{self._urlquote(name)}"
        )
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(pdf)

    def do_GET(self):
        self._json(405, {"error": "POST 요청만 지원합니다."})

    # ---------- helpers ----------
    def _compose(self, payload, grade, data):
        """브라우저가 보낸 값과 서버가 가진 값을 합쳐 렌더링용 문서를 만든다.

        주제·영역·학원명은 **서버의 주제 DB 를 신뢰**한다. 브라우저 값은
        직접 입력 주제일 때만 쓴다.
        """
        custom = bool(payload.get("custom"))
        no = payload.get("topic_no")
        no = no if isinstance(no, int) and no > 0 else 0

        src = TOPICS_BY_NO.get(no) if not custom else None
        if src:
            area, topic, academy = src["area"], src["topic"], src.get("src")
        else:
            area = str(payload.get("area") or "직접 입력")[:40]
            topic = str(payload.get("topic") or "")[:200]
            academy = "Custom Topic"

        # 화면 표기와 어긋나지 않도록 단어 수는 서버가 다시 센다.
        body = data.get("essay") or " ".join(data.get("essay_paras") or [])
        data = dict(data, word_count=_word_count(body))

        return {
            "topic_no": no,
            "area": area,
            "topic": topic or "(제목 없음)",
            "source_academy": academy,
            "grades": {grade: data},
        }

    @staticmethod
    def _urlquote(s):
        """RFC 5987 용 퍼센트 인코딩.

        chr(byte).isalnum() 은 0xEB 같은 값을 'ë' 로 보고 통과시키므로
        반드시 ASCII 범위인지 먼저 확인해야 한다.
        """
        safe = ("ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                "abcdefghijklmnopqrstuvwxyz0123456789-._~")
        return "".join(
            chr(b) if chr(b) in safe else "%%%02X" % b
            for b in s.encode("utf-8")
        )

    def _json(self, status, body, retry_after=None):
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        if retry_after:
            self.send_header("Retry-After", str(int(retry_after)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt, *args):
        pass
