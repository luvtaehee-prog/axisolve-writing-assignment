"""로컬 개발 서버 — Vercel 없이 정적 파일과 api/ 함수를 함께 띄운다.

Vercel 의 Python 런타임은 `api/<이름>.py` 안의 `handler` 클래스를 요청마다
깨워 `do_GET` / `do_POST` 를 부른다. 이 파일은 그 규칙만 흉내낸다.
따라서 api/ 에 파일을 새로 넣으면 서버를 고치지 않아도 바로 잡힌다.

로컬과 배포가 어긋나지 않도록 두 가지를 배포본과 똑같이 막는다.

  1. `/api/_*` — 공용 모듈은 엔드포인트가 아니다 (vercel.json 의 rewrites 와 동일)
  2. `.vercelignore` 에 적힌 경로 — 배포본에 없는 파일이 로컬에서만 열리면
     "로컬은 되는데 배포하면 404" 를 배포 후에야 알게 된다

실행:  py dev_server.py             →  http://localhost:3000
       PORT=3100 py dev_server.py   →  포트가 겹칠 때

환경변수는 `.env.local` 에서 읽는다. 없으면 없는 대로 뜬다.
OPENAI_API_KEY 가 없으면 화면은 전부 열리고 생성만 500 으로 막힌다.
"""

import os
import sys
import traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.join(ROOT, "api")
PORT = int(os.environ.get("PORT", "3000"))

# 윈도우 기본 콘솔은 cp949 라 한글을 찍다가 서버가 통째로 죽는다.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# api/ 안의 모듈들은 서로를 `import _guard` 처럼 이름만으로 부른다.
# Vercel 은 함수 파일이 있는 폴더를 기준으로 돌리므로 여기서도 같게 맞춘다.
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

# .vercelignore 와 같은 목록. 여기를 고치면 저쪽도 같이 고쳐야 한다.
BLOCKED_PREFIXES = (
    "/topics.json",
    "/docs/", "/supabase/", "/tools/",
    "/README.md", "/.env.example", "/.env.local", "/.git/",
    "/dev_server.py",
)


def load_env_file(path):
    """.env.local 을 os.environ 에 넣는다. 이미 있는 값은 덮지 않는다."""
    if not os.path.exists(path):
        return 0
    loaded = 0
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
                loaded += 1
    return loaded


def load_api_handler(name):
    """api/<name>.py 를 불러 그 안의 handler 클래스를 돌려준다.

    매 요청마다 다시 부른다. 함수 코드를 고치고 새로고침만 하면 반영되도록
    캐시하지 않는다 — 개발 서버이므로 속도보다 그쪽이 낫다.
    """
    import importlib
    path = os.path.join(API_DIR, name + ".py")
    if not os.path.exists(path):
        return None
    module = importlib.import_module(name)
    return getattr(importlib.reload(module), "handler", None)


class DevHandler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        SimpleHTTPRequestHandler.__init__(self, *a, directory=ROOT, **kw)

    # ---------- 라우팅 ----------

    def route(self, method):
        path = self.path.split("?")[0]

        if path.startswith("/api/"):
            return self.serve_api(path, method)

        if any(path.startswith(p) for p in BLOCKED_PREFIXES):
            self.send_error(404, "Not Found")
            return

        if method == "GET":
            return SimpleHTTPRequestHandler.do_GET(self)
        self.send_error(405, "Method Not Allowed")

    def serve_api(self, path, method):
        name = path[len("/api/"):].strip("/")

        # 공용 모듈은 엔드포인트가 아니다. vercel.json 의 rewrites 와 같은 처리.
        if not name or name.startswith("_") or "/" in name:
            self.send_error(404, "Not Found")
            return

        handler_cls = load_api_handler(name)
        if handler_cls is None:
            self.send_error(404, "Not Found")
            return

        if not hasattr(handler_cls, "do_" + method):
            self.send_error(405, "Method Not Allowed")
            return

        # Vercel 런타임처럼 handler 를 이 요청 위에서 실행한다.
        # 함수 파일들은 `_read_json` 같은 자기 클래스의 헬퍼를 쓰므로,
        # 메서드만 빌려 오면 안 되고 그 클래스의 객체여야 한다.
        # 그래서 __init__ 없이 객체를 만들고 인스턴스 딕셔너리를 이 요청과
        # 공유시킨다 — rfile·wfile·headers 를 그대로 보고, 응답도 이 소켓으로 나간다.
        proxy = object.__new__(handler_cls)
        proxy.__dict__ = self.__dict__
        try:
            getattr(proxy, "do_" + method)()
        except Exception:
            traceback.print_exc()
            try:
                self.send_error(500, "Internal Server Error")
            except Exception:
                pass

    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    count = load_env_file(os.path.join(ROOT, ".env.local"))
    print("AXISOLVE Writing Engine — http://localhost:%d" % PORT)
    if count:
        print(".env.local 에서 환경변수 %d개를 읽었습니다." % count)
    else:
        print(".env.local 이 없습니다. 화면은 열리고 AI 생성만 막힙니다.")
        print("  cp .env.example .env.local  후 OPENAI_API_KEY 를 채우십시오.")
    if not os.environ.get("OPENAI_API_KEY"):
        print("경고: OPENAI_API_KEY 미설정 — /api/generate 는 500 을 돌려줍니다.")
    print("종료: Ctrl+C\n")
    ThreadingHTTPServer(("127.0.0.1", PORT), DevHandler).serve_forever()
