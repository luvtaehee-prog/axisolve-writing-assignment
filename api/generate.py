"""Vercel Python Serverless Function — OpenAI Responses API 프록시.

브라우저는 이 엔드포인트만 호출한다. API 키는 서버 환경변수 OPENAI_API_KEY
에만 존재하며 응답 어디에도 포함되지 않는다.

요청  : POST /api/generate   {"prompt": "...", "system": "..."}
응답  : 200      {"text": "모델이 생성한 원문 텍스트"}
        4xx/5xx  {"error": "사용자에게 보여줄 메시지"}
"""

import json
import os
from http.server import BaseHTTPRequestHandler

import openai

# gpt-5.6-sol(최상위) / gpt-5.6-terra(균형) / gpt-5.6-luna(저비용)
# 환경변수 OPENAI_MODEL 로 교체할 수 있다.
MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.6-terra")
# none / minimal / low / medium / high (모델별 지원 범위 상이)
REASONING_EFFORT = os.environ.get("OPENAI_REASONING_EFFORT", "medium")
MAX_OUTPUT_TOKENS = 8000  # 추론 토큰을 포함한 상한
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

        if not os.environ.get("OPENAI_API_KEY"):
            return self._send(500, {
                "error": "OPENAI_API_KEY 가 설정되지 않았습니다. "
                         "Vercel 프로젝트의 Settings > Environment Variables 에서 추가한 뒤 재배포해 주십시오."
            })

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
            return self._send(500, {"error": "API 키가 유효하지 않습니다. 서버 환경변수를 확인해 주십시오."})
        except openai.PermissionDeniedError:
            return self._send(500, {"error": f"모델 '{MODEL}' 에 접근할 권한이 없습니다. OpenAI 계정의 사용 가능 모델을 확인해 주십시오."})
        except openai.NotFoundError:
            return self._send(500, {"error": f"모델 '{MODEL}' 을 찾을 수 없습니다. OPENAI_MODEL 설정을 확인해 주십시오."})
        except openai.RateLimitError:
            return self._send(429, {"error": "요청이 몰려 잠시 처리할 수 없습니다. 30초 후 다시 시도해 주십시오."})
        except openai.BadRequestError as exc:
            return self._send(400, {"error": f"요청이 거절되었습니다. ({exc.message})"})
        except openai.APIStatusError as exc:
            return self._send(502, {"error": f"AI 서버 오류가 발생했습니다. (HTTP {exc.status_code})"})
        except openai.APIConnectionError:
            return self._send(504, {"error": "AI 서버에 연결하지 못했습니다. 네트워크 상태를 확인한 뒤 다시 시도해 주십시오."})

        # max_output_tokens 에 걸려 잘린 경우: 프론트엔드의 재시도 대상으로 넘긴다.
        if response.status == "incomplete":
            reason = getattr(response.incomplete_details, "reason", "unknown")
            return self._send(502, {"error": f"응답이 완성되지 않았습니다. ({reason}) 다시 시도해 주십시오."})

        text = (response.output_text or "").strip()
        if not text:
            return self._send(502, {"error": "AI가 빈 응답을 반환했습니다. 다시 시도해 주십시오."})

        return self._send(200, {"text": text})

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
