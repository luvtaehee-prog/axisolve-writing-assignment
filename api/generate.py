"""Vercel Python Serverless Function — OpenAI Responses API 프록시.

브라우저는 이 엔드포인트만 호출한다. API 키는 서버 환경변수 OPENAI_API_KEY
에만 존재하며 응답 어디에도 포함되지 않는다.

요청  : POST /api/generate   {"prompt": "...", "system": "..."}
응답  : 200      {"text": "모델이 생성한 원문 텍스트"}
        4xx/5xx  {"error": "사용자에게 보여줄 메시지"}
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler

import openai

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _guard  # noqa: E402  (Phase 1 비용 방어 계층)
import _supabase  # noqa: E402  (Phase 2 로그인·크레딧)

# gpt-5.6-sol(최상위) / gpt-5.6-terra(균형) / gpt-5.6-luna(저비용)
# 환경변수 OPENAI_MODEL 로 교체할 수 있다.
MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.6-terra")
# none / minimal / low / medium / high (모델별 지원 범위 상이)
REASONING_EFFORT = os.environ.get("OPENAI_REASONING_EFFORT", "medium")
MAX_OUTPUT_TOKENS = 8000  # 추론 토큰을 포함한 상한
MAX_PROMPT_CHARS = 20000
MAX_ATTEMPTS = 4          # app.js 의 generateWithRetry 와 같은 값이어야 한다
CREDITS_PER_GENERATION = 1


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            payload = self._read_json()
        except ValueError as exc:
            return self._send(400, {"error": str(exc)})

        prompt = payload.get("prompt")
        system = payload.get("system")
        gen_id = payload.get("gen_id")
        topic_no = payload.get("topic_no")
        grade = payload.get("grade")

        if not isinstance(prompt, str) or not prompt.strip():
            return self._send(400, {"error": "생성 요청이 비어 있습니다. 주제를 선택한 뒤 다시 시도해 주십시오."})
        if len(prompt) > MAX_PROMPT_CHARS:
            return self._send(400, {"error": "요청이 너무 깁니다. 키워드를 줄인 뒤 다시 시도해 주십시오."})

        if not os.environ.get("OPENAI_API_KEY"):
            return self._send(500, {
                "error": "OPENAI_API_KEY 가 설정되지 않았습니다. "
                         "Vercel 프로젝트의 Settings > Environment Variables 에서 추가한 뒤 재배포해 주십시오."
            })

        # 비용 방어: 출처·레이트리밋 검사. 통과 시 호출 1건이 선기록된다.
        try:
            _guard.check(self.headers)
        except _guard.Rejected as rej:
            return self._send(rej.status, {"error": rej.message}, retry_after=rej.retry_after)

        # 로그인·크레딧 검사. Supabase 미설정 시에는 이 계층 전체를 건너뛰고
        # Phase 1 상태(레이트리밋만)로 동작한다.
        billing = None
        if _supabase.configured():
            try:
                billing = self._authorize(gen_id, topic_no, grade)
            except _guard.Rejected as rej:
                _guard.refund(self.headers)
                return self._send(rej.status, {"error": rej.message}, retry_after=rej.retry_after)
            except _supabase.SupabaseError as exc:
                _guard.refund(self.headers)
                return self._send(503, {"error": f"계정 서버에 연결하지 못했습니다. ({exc})"})
        self._billing = billing

        client = openai.OpenAI()

        try:
            response = client.responses.create(
                model=MODEL,
                instructions=system or None,
                input=[{"role": "user", "content": prompt}],
                reasoning={"effort": REASONING_EFFORT},
                max_output_tokens=MAX_OUTPUT_TOKENS,
            )
        except openai.AuthenticationError:
            return self._fail(500, "API 키가 유효하지 않습니다. 서버 환경변수를 확인해 주십시오.")
        except openai.PermissionDeniedError:
            return self._fail(500, f"모델 '{MODEL}' 에 접근할 권한이 없습니다. OpenAI 계정의 사용 가능 모델을 확인해 주십시오.")
        except openai.NotFoundError:
            return self._fail(500, f"모델 '{MODEL}' 을 찾을 수 없습니다. OPENAI_MODEL 설정을 확인해 주십시오.")
        except openai.RateLimitError:
            return self._fail(429, "요청이 몰려 잠시 처리할 수 없습니다. 30초 후 다시 시도해 주십시오.")
        except openai.BadRequestError as exc:
            return self._fail(400, f"요청이 거절되었습니다. ({exc.message})")
        except openai.APIStatusError as exc:
            return self._fail(502, f"AI 서버 오류가 발생했습니다. (HTTP {exc.status_code})")
        except openai.APIConnectionError:
            return self._fail(504, "AI 서버에 연결하지 못했습니다. 네트워크 상태를 확인한 뒤 다시 시도해 주십시오.")

        # max_output_tokens 에 걸려 잘린 경우: 프론트엔드의 재시도 대상으로 넘긴다.
        if response.status == "incomplete":
            reason = getattr(response.incomplete_details, "reason", "unknown")
            return self._fail(502, f"응답이 완성되지 않았습니다. ({reason}) 다시 시도해 주십시오.")

        text = (response.output_text or "").strip()
        if not text:
            return self._fail(502, "AI가 빈 응답을 반환했습니다. 다시 시도해 주십시오.")

        body = {"text": text}
        if billing:
            body["credits"] = billing.get("credits")
            body["free_used"] = billing.get("free_used")
        return self._send(200, body)

    def do_GET(self):
        self._send(405, {"error": "POST 요청만 지원합니다."})

    # ---------- helpers ----------
    def _fail(self, status, message):
        """생성 실패 — 선기록한 호출과 차감한 크레딧을 모두 되돌린다."""
        _guard.refund(self.headers)
        billing = getattr(self, "_billing", None)
        if billing and billing.get("charged"):
            try:
                if billing.get("user_id"):
                    _supabase.refund(billing["user_id"], CREDITS_PER_GENERATION)
                elif billing.get("ip_hash"):
                    _supabase.unbump_anon(billing["ip_hash"])
            except _supabase.SupabaseError:
                pass  # 환불 실패가 원래 오류를 가려서는 안 된다.
        return self._send(status, {"error": message})

    def _authorize(self, gen_id, topic_no, grade):
        """로그인 여부에 따라 크레딧 또는 무료 횟수를 차감한다.

        반환: {"user_id"|"ip_hash", "credits"|"free_used", "charged": bool}
        막아야 하면 _guard.Rejected 를 던진다.
        """
        if not isinstance(gen_id, str) or len(gen_id) < 8:
            raise _guard.Rejected(400, "생성 요청 식별자가 없습니다. 페이지를 새로고침해 주십시오.")

        user = _supabase.verify_token(self.headers.get("Authorization"))

        if user:
            result = _supabase.consume(
                user["id"], gen_id, CREDITS_PER_GENERATION,
                topic_no=topic_no if isinstance(topic_no, int) else None,
                grade=grade if isinstance(grade, str) else None,
                max_attempts=MAX_ATTEMPTS,
            )
            if result == -1:
                raise _guard.Rejected(402, "크레딧이 부족합니다. 충전 후 이용해 주십시오.")
            if result == -2:
                raise _guard.Rejected(429, "이 요청의 재시도 한도를 초과했습니다. 다시 생성해 주십시오.")
            return {"user_id": user["id"], "credits": result, "charged": True}

        # 비회원 — 무료 체험
        ip_hash = _guard.ip_hash(self.headers)
        result = _supabase.bump_anon(ip_hash, gen_id, max_attempts=MAX_ATTEMPTS)
        if result == -1:
            raise _guard.Rejected(401, "무료 체험을 모두 사용했습니다. 카카오 로그인 후 계속 이용해 주십시오.")
        if result == -2:
            raise _guard.Rejected(429, "이 요청의 재시도 한도를 초과했습니다. 다시 생성해 주십시오.")
        if result > _supabase.FREE_ANON_USES:
            _supabase.unbump_anon(ip_hash)
            raise _guard.Rejected(401, "무료 체험을 모두 사용했습니다. 카카오 로그인 후 계속 이용해 주십시오.")
        return {"ip_hash": ip_hash, "free_used": result, "charged": True}

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ValueError("요청 본문 길이를 읽을 수 없습니다.")
        if length <= 0:
            raise ValueError("요청 본문이 비어 있습니다.")
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("요청 형식이 올바르지 않습니다. (JSON 파싱 실패)")
        if not isinstance(payload, dict):
            raise ValueError("요청 본문은 JSON 객체여야 합니다.")
        return payload

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

    def log_message(self, fmt, *args):  # Vercel 로그 소음 억제
        pass
