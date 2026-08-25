# -*- coding: utf-8 -*-
"""워크북 렌더러 스모크 테스트.

같은 필드라도 출처에 따라 형태가 다르다는 점이 실제 버그를 냈다.

    app.js 스키마      : "단어: 뜻"          (문자열)
    손으로 만든 샘플   : ["단어", "뜻"]      (리스트)

문자열에 [0], [1] 로 접근하면 첫 글자·둘째 글자가 나오므로,
Grade 5-6 어휘표가 't / h', 'f / r' 처럼 한 글자만 찍혔다.

이 테스트는 두 형태 모두로 3개 학년을 렌더링하고,
원본 텍스트가 PDF 안에 온전히 들어갔는지 확인한다.

    py tools/smoke_workbook.py
"""

import io
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "api"))

import _workbook  # noqa: E402

try:
    import pdfplumber
except ImportError:
    sys.exit("pdfplumber 가 필요합니다:  py -m pip install pdfplumber")


def norm(s):
    return re.sub(r"\s+", "", str(s))


# ---------------------------------------------------------------------------
# (A) app.js 스키마 — 리스트 안의 값이 "라벨: 내용" 문자열
# ---------------------------------------------------------------------------
SCHEMA_DOC = {
    "topic_no": 31,
    "area": "상상",
    "topic": "What if you were on a sinking ship?",
    "source_academy": "TEST",
    "grades": {
        "Grade 1-2": {
            "brain": [
                ["Q1. What", "What would you take?", "a warm jacket"],
                ["Q2. Who", "Who would you help?", "my little brother"],
                ["Q3. Why", "Why stay calm?", "to think clearly"],
            ],
            "outline": [
                ["Opening", "배가 기울기 시작하는 장면", "the ship starts to tilt"],
                ["Detail 1", "구명조끼를 찾는 행동", "look for a life jacket"],
                ["Detail 2", "동생을 돕는 장면", "help my brother first"],
                ["Closing", "침착함이 중요하다는 정리", "staying calm matters"],
            ],
            "keywords": ["calm: 침착한", "jacket: 구명조끼", "rescue: 구조하다"],
            "patterns": ["I would ~.", "First, I ~.", "It is important to ~."],
            "essay": "The ship starts to tilt. " * 12,
            "word_count": 60,
        },
        "Grade 3-4": {
            "brain": [
                ["1. Situation", "어떤 상황인가?", "the ship is sinking"],
                ["2. Action", "무엇을 먼저 하는가?", "find a life jacket"],
                ["3. Meaning", "무엇을 배웠는가?", "calm thinking saves lives"],
            ],
            "outline": [
                ["Topic Sentence", "침착함이 가장 중요하다", "staying calm matters most"],
                ["Supporting 1", "구명조끼를 먼저 찾는다", "find a life jacket first"],
                ["Supporting 2", "동생을 돕는다", "help my younger brother"],
                ["Closing Sentence", "훈련이 습관을 만든다", "practice builds habits"],
            ],
            "vocab": ["panic: 공황, 당황", "rescue: 구조하다", "signal: 신호를 보내다"],
            "trans": ["First,", "However,", "As a result,"],
            "essay": "If I were on a sinking ship, I would stay calm. " * 10,
            "word_count": 110,
        },
        "Grade 5-6": {
            "matrix": [
                ["Introduction", "침몰 상황과 침착함이라는 논제 제시", "Imagine standing on a deck..."],
                ["Body 1", "공포가 판단을 흐리는 방식", "The first danger is panic..."],
                ["Body 2", "협력이 생존 확률을 높이는 이유", "Cooperation matters more..."],
                ["Conclusion", "침착함을 훈련된 습관으로 재정의", "Ultimately, survival depends..."],
            ],
            # 여기가 문제였던 지점 — 문자열 형태
            "vocab": [
                "perspective: 관점, 시각",
                "resilience: 회복하는 힘",
                "cooperation: 협력",
                "priority: 우선순위",
                "composure: 침착함",
            ],
            "essay_paras": [
                "Imagine standing on a deck that tilts beneath your feet. " * 4,
                "The first danger is not the water but panic itself. " * 4,
                "Cooperation matters more than individual strength. " * 4,
                "Ultimately, survival depends on habits built long before. " * 4,
            ],
            "word_count": 200,
        },
    },
}

# ---------------------------------------------------------------------------
# (B) 손으로 만든 샘플 형태 — 어휘가 ["단어", "뜻"] 리스트
# ---------------------------------------------------------------------------
PAIR_DOC = {
    "topic_no": 1,
    "area": "취향",
    "topic": "Write about your favorite book.",
    "source_academy": "ILE",
    "grades": {
        "Grade 5-6": {
            "matrix": SCHEMA_DOC["grades"]["Grade 5-6"]["matrix"],
            "vocab": [
                ["perspective", "관점, 시각"],
                ["belonging", "소속되어 있다는 느낌"],
                ["empathy", "다른 사람의 감정을 이해하는 능력"],
                ["assumption", "충분히 알기 전에 내리는 판단"],
                ["responsibility", "자신의 선택과 행동에 대한 책임"],
            ],
            "essay_paras": SCHEMA_DOC["grades"]["Grade 5-6"]["essay_paras"],
            "word_count": 200,
        },
    },
}

EXPECT = {
    "Grade 1-2": lambda d: (
        [x for b in d["brain"] for x in b]
        + [x for o in d["outline"] for x in o]
        + d["keywords"] + d["patterns"]
    ),
    "Grade 3-4": lambda d: (
        [x for b in d["brain"] for x in b]
        + [x for o in d["outline"] for x in o]
        + d["vocab"] + d["trans"]
    ),
    "Grade 5-6": lambda d: (
        [x for m in d["matrix"] for x in m]
        + [x if isinstance(x, str) else " ".join(x) for x in d["vocab"]]
    ),
}

CARD_W = (493.2 - 11.3 * 2) / 3
failed = 0


def check(doc, grade, label):
    global failed
    pdf = _workbook.render(doc, grade)
    path = os.path.join(tempfile.mkdtemp(), "t.pdf")
    open(path, "wb").write(pdf)

    with pdfplumber.open(path) as p:
        blob = ""
        for pg in p.pages:
            blob += pg.extract_text() or ""
            # 카드는 3열 병렬이라 열 단위로도 잘라 읽는다.
            for i in range(3):
                x0 = 51.0 + i * (CARD_W + 11.3)
                blob += pg.crop((x0, 150, x0 + CARD_W, 340)).extract_text() or ""
        pages = len(p.pages)

    blob = norm(blob)
    items = EXPECT[grade](doc["grades"][grade])
    # "단어: 뜻" 문자열은 PDF 에서 두 칸으로 나뉘므로 조각으로 확인한다.
    missing = []
    for it in items:
        parts = [q for q in re.split(r"[:|]", str(it)) if q.strip()]
        for q in parts:
            if norm(q) not in blob:
                missing.append(q.strip())

    mark = "OK  " if not missing else "FAIL"
    if missing:
        failed += 1
    print(f"  {mark} {label} / {grade}: {pages}p, 검사 {len(items)}항목"
          + (f" — 누락 {missing[:4]}" if missing else ""))


print("[A] app.js 스키마 (문자열 형태)")
for g in ("Grade 1-2", "Grade 3-4", "Grade 5-6"):
    check(SCHEMA_DOC, g, "A")

print()
print("[B] 샘플 JSON (리스트 형태)")
check(PAIR_DOC, "Grade 5-6", "B")

print()
if failed:
    print(f"  {failed}건 실패")
    sys.exit(1)
print("  전부 통과")
