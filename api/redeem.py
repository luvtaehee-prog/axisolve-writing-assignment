# -*- coding: utf-8 -*-
"""POST /api/redeem — 충전 코드로 크레딧 받기.

사업자등록 전이라 PG 결제를 붙일 수 없는 동안의 충전 경로다.
운영자가 입금을 확인하고 발급한 코드를 사용자가 입력한다.

요청 : {"code": "AX-XXXX-XXXX"}   (Authorization: Bearer <토큰> 필수)
응답 : 200 {"credits": 30, "balance": 33}
       4xx {"error": "..."}
"""

import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _guard      # noqa: E402
import _supabase   # noqa: E402

# 코드 무차별 대입 방어. IP 해시당 시간당 시도 횟수.
MAX_TRIES_PER_HOUR = int(os.environ.get("REDEEM_TRIES_HOURLY", "10"))
_tries = {}

MESSAGES = {
    "not_found": "존재하지 않는 코드입니다. 대소문자와 하이픈을 확인해 주십시오.",
    "expired": "사용 기한이 지난 코드입니다.",
    "exhausted": "이미 사용된 코드입니다.",
    "already_used": "이미 이 계정에서 사용한 코드입니다.",
}


def _rate_limited(key):
    now = time.time()
    hits = [t for t in _tries.get(key, []) if t > now - 3600]
    if len(hits) >= MAX_TRIES_PER_HOUR:
        _tries[key] = hits
        return True
    hits.append(now)
    _tries[key] = hits
    if len(_tries) > 2000:                       # 메모리 무한 증가 방지
        for k in [k for k, v in _tries.items() if not v or v[-1] < now - 3600]:
            _tries.pop(k, None)
    return False


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if not _supabase.configured():
            return self._send(503, {"error": "충전 기능이 아직 설정되지 않았습니다."})

        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        except (ValueError, UnicodeDecodeError):
            return self._send(400, {"error": "요청 형식이 올바르지 않습니다."})

        code = payload.get("code")
        if not isinstance(code, str) or not code.strip():
            return self._send(400, {"error": "충전 코드를 입력해 주십시오."})
        if len(code) > 64:
            return self._send(400, {"error": "코드 형식이 올바르지 않습니다."})

        if _rate_limited(_guard.ip_hash(self.headers)):
            return self._send(429, {
                "error": "코드 입력 시도가 너무 많습니다. 잠시 후 다시 시도해 주십시오."
            }, retry_after=600)

        try:
            user = _supabase.verify_token(self.headers.get("Authorization"))
            if not user:
                return self._send(401, {"error": "로그인 후 이용해 주십시오."})
            result = _supabase.redeem(user["id"], code.strip())
        except _supabase.SupabaseError as exc:
            return self._send(503, {"error": f"계정 서버에 연결하지 못했습니다. ({exc})"})

        if result["status"] != "ok":
            return self._send(400, {
                "error": MESSAGES.get(result["status"], "코드를 사용할 수 없습니다.")
            })

        return self._send(200, {"credits": result["credits"], "balance": result["balance"]})

    def do_GET(self):
        self._send(405, {"error": "POST 요청만 지원합니다."})

    def _send(self, status, body, retry_after=None):
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
