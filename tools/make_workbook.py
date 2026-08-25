# -*- coding: utf-8 -*-
"""AXISOLVE 라이팅 워크북 PDF 생성 (CLI).

렌더링 로직은 api/_workbook.py 에 있으며 서버리스 함수와 공유한다.

    py tools/make_workbook.py <source.json> [-o 출력디렉터리]
    py tools/make_workbook.py <source.json> --grade "Grade 1-2"
"""

import argparse
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api"))
from _workbook import BUILDERS, filename, render  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="AXISOLVE 라이팅 워크북 PDF 생성")
    ap.add_argument("source", help="콘텐츠 JSON 경로")
    ap.add_argument("-o", "--out", default=".", help="출력 디렉터리")
    ap.add_argument("--grade", action="append", help="특정 학년만 생성 (여러 번 지정 가능)")
    args = ap.parse_args()

    doc = json.load(io.open(args.source, encoding="utf-8"))
    os.makedirs(args.out, exist_ok=True)

    for g in (args.grade or [g for g in BUILDERS if g in doc["grades"]]):
        if g not in doc["grades"]:
            print(f"  건너뜀 - JSON 에 {g} 데이터가 없습니다.")
            continue
        path = os.path.join(args.out, filename(doc, g))
        with open(path, "wb") as f:
            f.write(render(doc, g))
        print(f"  생성: {os.path.basename(path)}")


if __name__ == "__main__":
    main()
