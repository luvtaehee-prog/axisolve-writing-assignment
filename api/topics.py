# -*- coding: utf-8 -*-
"""GET /api/topics — 주제 목록.

주제 DB 는 이 서비스의 자산이므로 정적 파일로 내려받을 수 없게 한다.

  - 원본 topics.json 은 .vercelignore 로 배포에서 제외된다.
  - 배포본에는 출제 학원명(src)을 제거한 api/_topics.py 만 들어간다.
    파이썬 모듈이므로 정적 파일로 서빙될 수 없다.
  - 이 엔드포인트에도 IP 기준 상한을 걸어 반복 수집을 막는다.

완전한 차단은 불가능하다. 목록은 결국 화면에 렌더되므로 마음먹으면 긁을 수 있다.
목적은 "URL 하나로 전부 받기"를 막아 난이도를 올리는 것이다.

응답: {"topics": [{"no":1,"area":"취향","topic":"...","isNew":false}, ...], "count": 165}
"""

import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _guard   # noqa: E402
from _topics import TOPICS  # noqa: E402

# 정상 이용이라면 페이지 진입 시 한 번이면 충분하다. 넉넉히 잡되 수집은 막는다.
MAX_PER_HOUR = int(os.environ.get("TOPICS_TRIES_HOURLY", "40"))
_hits = {}

_PAYLOAD = json.dumps(
    {"topics": TOPICS, "count": len(TOPICS)}, ensure_ascii=False
).encode("utf-8")


def _rate_limited(key):
    now = time.time()
    seen = [t for t in _hits.get(key, []) if t > now - 3600]
    if len(seen) >= MAX_PER_HOUR:
        _hits[key] = seen
        return True
    seen.append(now)
    _hits[key] = seen
    if len(_hits) > 3000:                       # 메모리 무한 증가 방지
        for k in [k for k, v in _hits.items() if not v or v[-1] < now - 3600]:
            _hits.pop(k, None)
    return False


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            _guard._check_origin(self.headers)
        except _guard.Rejected as rej:
            return self._send(rej.status, {"error": rej.message})

        if _rate_limited(_guard.ip_hash(self.headers)):
            return self._send(429, {
                "error": "주제 목록 요청이 너무 많습니다. 잠시 후 다시 시도해 주십시오."
            }, retry_after=600)

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(_PAYLOAD)))
        # 같은 방문자가 섹션을 오갈 때 재요청하지 않도록 짧게 캐시한다.
        self.send_header("Cache-Control", "private, max-age=600")
        self.end_headers()
        self.wfile.write(_PAYLOAD)

    def do_POST(self):
        self._send(405, {"error": "GET 요청만 지원합니다."})

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
