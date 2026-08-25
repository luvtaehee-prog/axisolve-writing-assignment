# -*- coding: utf-8 -*-
"""topics.json → api/_topics.py 생성.

주제 DB 를 배포본에서 직접 내려받을 수 없게 만들기 위한 빌드 단계다.

  - topics.json 은 출제 학원명(src)을 포함한 원본이며 .vercelignore 로
    배포에서 제외된다. 저장소 안에서만 관리한다.
  - api/_topics.py 는 src 를 제거한 사본이며, 파이썬 모듈이므로
    정적 파일로 서빙될 수 없다. /api/topics 만 이 데이터를 내보낸다.

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

# 브라우저로 내보낼 필드. src(출제 학원명)는 의도적으로 제외한다.
PUBLIC_FIELDS = ("no", "area", "topic", "isNew")


def main():
    topics = json.load(io.open(SRC, encoding="utf-8"))
    public = [{k: t[k] for k in PUBLIC_FIELDS if k in t} for t in topics]

    # JSON 이 아니라 파이썬 리터럴로 내보낸다 (true/false 표기가 다르다).
    body = pprint.pformat(public, width=100, sort_dicts=False)
    io.open(OUT, "w", encoding="utf-8").write(
        "# -*- coding: utf-8 -*-\n"
        '"""자동 생성 파일 — 직접 수정하지 말 것.\n\n'
        "topics.json 을 고친 뒤 `py tools/build_topics.py` 로 다시 만든다.\n"
        "출제 학원명(src)은 의도적으로 제외되어 있다.\n"
        '"""\n\n'
        "TOPICS = " + body + "\n"
    )

    dropped = sorted({t.get("src") for t in topics if t.get("src")})
    print(f"topics.json {len(topics)}개 → api/_topics.py {len(public)}개")
    print(f"제외한 필드: src ({len(dropped)}개 학원명)")
    print(f"내보내는 필드: {', '.join(PUBLIC_FIELDS)}")


if __name__ == "__main__":
    main()
