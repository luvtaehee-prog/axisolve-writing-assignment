# -*- coding: utf-8 -*-
"""topics.json → api/_topics.py + api/_topics_full.py 생성.

주제 DB 를 배포본에서 직접 내려받을 수 없게 만들기 위한 빌드 단계다.

  - topics.json 은 출제 학원명(src)을 포함한 원본이며 .vercelignore 로
    배포에서 제외된다. 저장소 안에서만 관리한다.
  - api/_topics.py      — src 를 제거한 공개본. /api/topics 가 이것만 내보낸다.
  - api/_topics_full.py — src 를 포함한 서버 전용본. PDF 헤더의
                          "Past Test · {학원명}" 표기에만 쓰이며 응답에 넣지 않는다.

둘 다 파이썬 모듈이므로 정적 파일로 서빙될 수 없다.

주제를 추가·수정한 뒤에는 반드시 이 스크립트를 다시 돌리고 함께 커밋한다.

    py tools/build_topics.py
"""

import io
import json
import os
import pprint

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "topics.json")
OUT = os.path.join(ROOT, "api", "_topics.py")
OUT_FULL = os.path.join(ROOT, "api", "_topics_full.py")

# 브라우저로 내보낼 필드. src(출제 학원명)는 의도적으로 제외한다.
PUBLIC_FIELDS = ("no", "area", "topic", "isNew")

# 서버 전용. PDF 헤더에만 쓰이며 어떤 응답으로도 나가지 않는다.
SERVER_FIELDS = ("no", "area", "topic", "src")

HEADER_PUBLIC = '''# -*- coding: utf-8 -*-
"""자동 생성 파일 — 직접 수정하지 말 것.

topics.json 을 고친 뒤 `py tools/build_topics.py` 로 다시 만든다.
출제 학원명(src)은 의도적으로 제외되어 있다.
"""

TOPICS = '''

HEADER_FULL = '''# -*- coding: utf-8 -*-
"""자동 생성 파일 — 직접 수정하지 말 것.

서버 전용 주제 정보. 출제 학원명(src)을 포함하므로
브라우저로 내보내는 응답에 절대 넣지 말 것.
PDF 헤더의 "Past Test · {학원명}" 표기에만 쓴다.
"""

TOPICS_BY_NO = '''


def main():
    topics = json.load(io.open(SRC, encoding="utf-8"))

    public = [{k: t[k] for k in PUBLIC_FIELDS if k in t} for t in topics]
    io.open(OUT, "w", encoding="utf-8").write(
        HEADER_PUBLIC + pprint.pformat(public, width=100, sort_dicts=False) + "\n"
    )

    server = {t["no"]: {k: t[k] for k in SERVER_FIELDS if k in t} for t in topics}
    io.open(OUT_FULL, "w", encoding="utf-8").write(
        HEADER_FULL + pprint.pformat(server, width=100, sort_dicts=False) + "\n"
    )

    dropped = sorted({t.get("src") for t in topics if t.get("src")})
    print(f"topics.json {len(topics)}개")
    print(f"  -> api/_topics.py       {len(public)}개  (필드: {', '.join(PUBLIC_FIELDS)})")
    print(f"  -> api/_topics_full.py  {len(server)}개  (서버 전용, 학원명 {len(dropped)}곳 포함)")


if __name__ == "__main__":
    main()
