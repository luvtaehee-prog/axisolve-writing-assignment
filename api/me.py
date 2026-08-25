# -*- coding: utf-8 -*-
"""GET /api/me — 로그인 상태와 크레딧 잔액.

브라우저가 부팅 시 한 번 호출한다. 응답에는 Supabase 접속 정보(공개 키)도
포함되므로, 프론트엔드는 별도의 설정 파일 없이 이 응답만으로 로그인을 시작할 수 있다.

응답 예
  { "logged_in": true,  "credits": 3, "name": "홍길동",
    "config": { "supabase_url": "...", "anon_key": "...", "free_anon_uses": 2 } }
  { "logged_in": false, "free_anon_uses": 2, "config": { ... } }
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _supabase  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        config = {
            "supabase_url": _supabase.SUPABASE_URL,
            "anon_key": _supabase.ANON_KEY,
            "free_anon_uses": _supabase.FREE_ANON_USES,
            "signup_bonus": _supabase.SIGNUP_BONUS,
            "auth_enabled": _supabase.configured(),
            "purchase_contact": _supabase.PURCHASE_CONTACT,
            "purchase_bank": _supabase.PURCHASE_BANK,
        }

        if not _supabase.configured():
            # Phase 2 미설정 상태 — 로그인 없이 그대로 쓰던 대로 동작한다.
            return self._send(200, {"logged_in": False, "config": config})

        try:
            user = _supabase.verify_token(self.headers.get("Authorization"))
        except _supabase.SupabaseError as exc:
            return self._send(503, {"error": str(exc), "config": config})

        if not user:
            return self._send(200, {
                "logged_in": False,
                "free_anon_uses": _supabase.FREE_ANON_USES,
                "config": config,
            })

        try:
            balance, bonus_granted = _supabase.ensure_account(user["id"])
        except _supabase.SupabaseError as exc:
            return self._send(503, {"error": str(exc), "config": config})

        return self._send(200, {
            "logged_in": True,
            "credits": balance,
            "bonus_just_granted": bonus_granted,
            "name": user["name"],
            "email": user["email"],
            "avatar": user["avatar"],
            "config": config,
        })

    def do_POST(self):
        self._send(405, {"error": "GET 요청만 지원합니다."})

    def _send(self, status, body):
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt, *args):
        pass
