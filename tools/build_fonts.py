# -*- coding: utf-8 -*-
"""Noto Sans KR 서브셋 생성 — 배포본에 넣을 PDF 폰트를 만든다.

Vercel 서버에는 한글 폰트가 없으므로 저장소에 폰트를 함께 넣어야 한다.
원본은 Regular/Bold 각 5.9MB(합 11.8MB)이고, 그 대부분이 한자(8,138자)다.
워크북에는 한자가 쓰이지 않으므로 덜어내면 용량과 콜드스타트가 크게 줄어든다.

유지하는 범위
    한글 완성형 전체(11,172자) · 한글 자모 · 라틴 · 문장부호
    화살표(→) · 도형(□ ■) · CJK 문장부호 · 통화 기호

    py tools/build_fonts.py
"""

import os
import sys

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "api", "_fonts")

SOURCES = {
    "NotoSansKR-Regular.ttf": ["NotoSansKR-Regular.ttf", "NotoSansCJKkr-Regular.otf"],
    "NotoSansKR-Bold.ttf": ["NotoSansKR-Bold.ttf", "NotoSansCJKkr-Bold.otf"],
}

FONT_DIRS = [
    r"C:\Windows\Fonts",
    os.path.expanduser(r"~\AppData\Local\Microsoft\Windows\Fonts"),
    "/usr/share/fonts/truetype/noto",
    "/usr/share/fonts/opentype/noto",
]

# 유지할 유니코드 구간 (시작, 끝) 포함
RANGES = [
    (0x0020, 0x007E),   # ASCII
    (0x00A0, 0x024F),   # 라틴-1 보충 · 확장 A/B (· × ÷ é 등)
    (0x2010, 0x206F),   # 일반 문장부호 (— ‘ ’ “ ” … ‰)
    (0x20A0, 0x20BF),   # 통화 기호 (₩ € 등)
    (0x2100, 0x214F),   # 문자꼴 기호 (© ™ № 등)
    (0x2190, 0x21FF),   # 화살표 (→ ← ↑ ↓)
    (0x2200, 0x22FF),   # 수학 연산자
    (0x2460, 0x24FF),   # 원문자 (① ②)
    (0x2500, 0x257F),   # 괘선
    (0x25A0, 0x25FF),   # 도형 (□ ■ ▶ ●)
    (0x2600, 0x26FF),   # 기타 기호 (★ ☆ ⚠)
    (0x3000, 0x303F),   # CJK 문장부호 (、。「」)
    (0x3130, 0x318F),   # 호환 한글 자모 (ㄱ ㅏ)
    (0x1100, 0x11FF),   # 한글 자모
    (0xAC00, 0xD7A3),   # 한글 완성형 전체
    (0xFF00, 0xFFEF),   # 전각 형태
]


def find_source(names):
    for d in FONT_DIRS:
        for n in names:
            p = os.path.join(d, n)
            if os.path.isfile(p):
                return p
    return None


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    unicodes = []
    for lo, hi in RANGES:
        unicodes.extend(range(lo, hi + 1))

    total_before = total_after = 0
    for out_name, candidates in SOURCES.items():
        src = find_source(candidates)
        if src is None:
            sys.exit(f"원본 폰트를 찾지 못했습니다: {candidates[0]}\n"
                     "Noto Sans KR 을 설치한 뒤 다시 실행해 주십시오.")

        font = TTFont(src, fontNumber=0)
        have = set(font.getBestCmap())
        keep = sorted(set(unicodes) & have)

        opts = subset.Options()
        opts.layout_features = ["*"]
        opts.name_IDs = ["*"]
        opts.notdef_outline = True
        opts.recalc_bounds = True
        opts.drop_tables += ["FFTM"]

        subsetter = subset.Subsetter(options=opts)
        subsetter.populate(unicodes=keep)
        subsetter.subset(font)

        out = os.path.join(OUT_DIR, out_name)
        font.flavor = None                      # TTF 로 저장 (reportlab 은 woff2 를 못 읽는다)
        font.save(out)

        before = os.path.getsize(src)
        after = os.path.getsize(out)
        total_before += before
        total_after += after
        print(f"  {out_name}: {before/1048576:.1f}MB → {after/1048576:.2f}MB "
              f"(글리프 {len(have)} → {len(keep)})")

    print(f"\n  합계 {total_before/1048576:.1f}MB → {total_after/1048576:.2f}MB "
          f"({(1-total_after/total_before)*100:.0f}% 감소)")
    print(f"  출력: {OUT_DIR}")


if __name__ == "__main__":
    main()
