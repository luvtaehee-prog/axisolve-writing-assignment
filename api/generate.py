"""Vercel Python Serverless Function — Anthropic Messages API 프록시.

브라우저는 이 엔드포인트만 호출한다. API 키는 서버 환경변수 ANTHROPIC_API_KEY
에만 존재하며 응답 어디에도 포함되지 않는다.

요청  : POST /api/generate   {"prompt": "...", "system": "..."}
응답  : 200  Anthropic Message 객체 (content 배열 포함)
        4xx/5xx  {"error": "사용자에게 보여줄 메시지"}
"""

import json
import os
from http.server import BaseHTTPRequestHandler

import anthropic

# 기존 Netlify 함수와 동일한 모델을 유지한다.
# 다른 모델로 바꾸려면 Vercel 환경변수 ANTHROPIC_MODEL 을 설정한다.
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
MAX_TOKENS = 8000
MAX_PROMPT_CHARS = 20000


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            payload = self._read_json()
        except ValueError as exc:
            return self._send(400, {"error": str(exc)})

        prompt = payload.get("prompt")
        system = payload.get("system")

        if not isinstance(prompt, str) or not prompt.strip():
            return self._send(400, {"error": "생성 요청이 비어 있습니다. 주제를 선택한 뒤 다시 시도해 주십시오."})
        if len(prompt) > MAX_PROMPT_CHARS:
            return self._send(400, {"error": "요청이 너무 깁니다. 키워드를 줄인 뒤 다시 시도해 주십시오."})

        if not os.environ.get("ANTHROPIC_API_KEY"):
            return self._send(500, {
                "error": "ANTHROPIC_API_KEY 가 설정되지 않았습니다. "
                         "Vercel 프로젝트의 Settings > Environment Variables 에서 추가한 뒤 재배포해 주십시오."
            })

        client = anthropic.Anthropic()

        try:
            message = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                output_config={"effort": "medium"},
                system=system or anthropic.NOT_GIVEN,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.AuthenticationError:
            return self._send(500, {"error": "API 키가 유효하지 않습니다. 서버 환경변수를 확인해 주십시오."})
        except anthropic.NotFoundError:
            return self._send(500, {"error": f"모델 '{MODEL}' 을 찾을 수 없습니다. ANTHROPIC_MODEL 설정을 확인해 주십시오."})
        except anthropic.RateLimitError:
            return self._send(429, {"error": "요청이 몰려 잠시 처리할 수 없습니다. 30초 후 다시 시도해 주십시오."})
        except anthropic.APIStatusError as exc:
            return self._send(502, {"error": f"AI 서버 오류가 발생했습니다. (HTTP {exc.status_code})"})
        except anthropic.APIConnectionError:
            return self._send(504, {"error": "AI 서버에 연결하지 못했습니다. 네트워크 상태를 확인한 뒤 다시 시도해 주십시오."})

        # 프론트엔드(app.js)는 content 배열에서 type === "text" 블록만 읽는다.
        return self._send(200, message.model_dump(mode="json"))

    def do_GET(self):
        self._send(405, {"error": "POST 요청만 지원합니다."})

    # ---------- helpers ----------
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

    def _send(self, status, body):
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt, *args):  # Vercel 로그 소음 억제
        pass
