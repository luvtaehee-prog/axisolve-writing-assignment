# -*- coding: utf-8 -*-
"""AXISOLVE 라이팅 워크북 PDF 렌더링 코어.

docs/layout_spec.md 의 고정 양식을 따르며, 좌표·색상·서체는 기존 샘플
(AXISOLVE_Writing_001-005_Final)에서 실측한 값을 그대로 쓴다.

서버리스 함수(api/pdf.py)와 CLI(tools/make_workbook.py)가 이 모듈을 공유한다.
폰트는 배포본에 함께 넣은 api/_fonts/ 를 먼저 찾고, 없으면 시스템 폰트를 쓴다.
"""

import io
import os
import re

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from _workbook_content import (
    BRAND_LINE_1, BRAND_LINE_2, CHECKLIST, CHECKLIST_INTRO,
    FOOTER_COPYRIGHT, FOOTER_NOTICE, PAGE_LABELS, PALETTE, SUBTITLE,
)

# ---------------------------------------------------------------------------
# 서체
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))

FONT_DIRS = [
    os.path.join(_HERE, "_fonts"),          # 배포본에 함께 넣은 서브셋 (tools/build_fonts.py)
    r"C:\Windows\Fonts",
    os.path.expanduser(r"~\AppData\Local\Microsoft\Windows\Fonts"),
    "/usr/share/fonts/truetype/noto",
]

# 요구사항: 한글 Noto Sans KR / 영문 Noto Sans.
# 기존 샘플은 모델 에세이 본문에만 Noto Serif 를 썼으나, 시스템에 정적 Serif 가
# 없으면 가변 폰트가 ExtraLight 로 잡혀 본문이 너무 얇아진다.
# 정적 Serif 가 설치돼 있을 때만 쓰고, 없으면 Sans 로 통일한다.
FONT_FILES = {
    "KR":       ["NotoSansKR-Regular.ttf", "NotoSansKR-VF.ttf", "NotoSansCJKkr-Regular.otf"],
    "KR-Bold":  ["NotoSansKR-Bold.ttf",    "NotoSansKR-VF.ttf", "NotoSansCJKkr-Bold.otf"],
    "KR-Serif": ["NotoSerifKR-Regular.ttf", "NotoSerifCJKkr-Regular.otf"],
}


def _find(names):
    for d in FONT_DIRS:
        for n in names:
            p = os.path.join(d, n)
            if os.path.isfile(p):
                return p
    return None


_registered = False


def register_fonts():
    """Noto 계열을 등록한다. Serif 가 없으면 Sans 로 대체한다. (1회만 수행)"""
    global _registered
    if _registered:
        return
    missing = []
    for alias, names in FONT_FILES.items():
        path = _find(names)
        if path is None:
            missing.append(alias)
            continue
        pdfmetrics.registerFont(TTFont(alias, path))
    if "KR-Serif" in missing:
        # 모델 에세이 본문용 세리프가 없으면 본문 서체를 그대로 쓴다.
        pdfmetrics.registerFont(TTFont("KR-Serif", _find(FONT_FILES["KR"])))
        missing.remove("KR-Serif")
    if missing:
        raise SystemExit(
            "필요한 폰트를 찾지 못했습니다: " + ", ".join(missing) + "\n"
            "Noto Sans KR 을 설치한 뒤 다시 실행해 주십시오."
        )


# ---------------------------------------------------------------------------
# 레이아웃 상수 — 기존 샘플에서 실측
# ---------------------------------------------------------------------------

W, H = A4                       # 595.28 x 841.89
MX = 51.0                       # 좌우 여백
CW = 493.2                      # 본문 폭
TOPBAR_H = 6.24

INK = HexColor("#1D252B")
MUTED = HexColor("#6D777C")
MUTED_2 = HexColor("#3E494F")
LINE = HexColor("#E0E4E6")
LINE_2 = HexColor("#D7DDE0")
WHITE = HexColor("#FFFFFF")

SEC_BOX = 25.5                  # 섹션 번호 사각형 한 변
ROW_H = 29.48                   # 필기 줄 한 칸 높이


# ---------------------------------------------------------------------------
# 데이터 정규화
#
# 같은 필드라도 출처에 따라 형태가 다르다.
#   - 앱이 AI 에게 요구하는 스키마(app.js) : "단어: 뜻" 같은 문자열
#   - 손으로 만든 샘플 JSON               : ["단어", "뜻"] 같은 리스트
# 문자열에 [0], [1] 로 접근하면 첫 글자·둘째 글자가 나오므로 반드시 거쳐야 한다.
# ---------------------------------------------------------------------------

def _split(text, sep=":", parts=2):
    """'단어: 뜻' 처럼 구분자로 나뉜 문자열을 조각낸다. 모자라면 빈 문자열로 채운다."""
    out = [p.strip() for p in str(text).split(sep, parts - 1)]
    return out + [""] * (parts - len(out))


def as_pair(item):
    """(앞, 뒤) 두 조각으로 정규화한다."""
    if isinstance(item, (list, tuple)):
        vals = [str(v) for v in item] + ["", ""]
        return vals[0], vals[1]
    return tuple(_split(item, ":", 2))


def as_triple(item):
    """(라벨, 한글 설명, 영문 힌트) 세 조각으로 정규화한다."""
    if isinstance(item, (list, tuple)):
        vals = [str(v) for v in item] + ["", "", ""]
        return vals[0], vals[1], vals[2]
    # 문자열 하나로 온 경우: '라벨: 설명 | 힌트' 정도까지만 받아준다.
    label, rest = _split(item, ":", 2)
    ko, en = _split(rest, "|", 2)
    return label, ko, en


class Sheet:
    """A4 한 장. top(위에서부터의 거리) 좌표계를 쓰고 내부에서 뒤집는다."""

    def __init__(self, c, grade, doc, page_no, total):
        self.c = c
        self.grade = grade
        self.doc = doc
        self.page_no = page_no
        self.total = total
        self.pal = PALETTE[grade]
        self.accent = HexColor(self.pal["accent"])
        self.soft = HexColor(self.pal["soft"])
        self.deep = HexColor(self.pal["deep"])

    # ---------- 저수준 ----------
    def text(self, x, top, s, font="KR", size=10, color=INK, align="left"):
        c = self.c
        c.setFont(font, size)
        c.setFillColor(color)
        y = H - top - size * 0.80
        if align == "right":
            c.drawRightString(x, y, s)
        elif align == "center":
            c.drawCentredString(x, y, s)
        else:
            c.drawString(x, y, s)

    def box(self, x, top, w, h, fill=None, stroke=None, lw=0.8, radius=0):
        c = self.c
        y = H - top - h
        c.setLineWidth(lw)
        if fill is not None:
            c.setFillColor(fill)
        if stroke is not None:
            c.setStrokeColor(stroke)
        mode = (1 if fill is not None else 0, 1 if stroke is not None else 0)
        if radius:
            c.roundRect(x, y, w, h, radius, stroke=mode[1], fill=mode[0])
        else:
            c.rect(x, y, w, h, stroke=mode[1], fill=mode[0])

    def rule(self, x, top, w, color=LINE_2, lw=0.8):
        c = self.c
        c.setStrokeColor(color)
        c.setLineWidth(lw)
        y = H - top
        c.line(x, y, x + w, y)

    def wrap(self, s, font, size, width):
        """폭에 맞춰 줄바꿈. 한글은 글자 단위, 영문은 단어 단위로 끊는다."""
        out, line = [], ""
        tokens = re.findall(r"[^\s]+|\s+", s)
        for tok in tokens:
            trial = line + tok
            if pdfmetrics.stringWidth(trial, font, size) <= width:
                line = trial
                continue
            if tok.strip() == "":
                out.append(line.rstrip())
                line = ""
                continue
            if line:
                out.append(line.rstrip())
                line = ""
            # 한 토큰이 통째로 넘칠 때는 글자 단위로 자른다.
            for ch in tok:
                if pdfmetrics.stringWidth(line + ch, font, size) > width and line:
                    out.append(line)
                    line = ""
                line += ch
        if line.strip():
            out.append(line.rstrip())
        return out

    def para(self, x, top, s, font="KR", size=10, color=INK, width=None, leading=None):
        """줄바꿈해서 그린 뒤, 다음 요소가 시작할 top 을 돌려준다."""
        width = width or (CW - (x - MX))
        leading = leading or size * 1.62
        for i, ln in enumerate(self.wrap(s, font, size, width)):
            self.text(x, top + i * leading, ln, font, size, color)
        return top + len(self.wrap(s, font, size, width)) * leading

    # ---------- 공통 요소 ----------
    def chrome(self):
        """모든 페이지에 공통으로 들어가는 상단 바 · 브랜드 · 푸터."""
        self.box(0, 0, W, TOPBAR_H, fill=self.accent)

        self.text(MX, 15.8, BRAND_LINE_1, "KR-Bold", 8.6, self.deep)
        self.text(MX, 28.1, BRAND_LINE_2, "KR", 7.2, MUTED)
        self.rule(MX, 40.0, CW, LINE)

        self.rule(MX, 794.5, CW, LINE)
        self.text(MX, 801.5, FOOTER_COPYRIGHT, "KR-Bold", 7.5, MUTED_2)
        self.text(MX + CW, 809.7, f"No. {self.doc['topic_no']:03d} · {self.page_no}/{self.total}",
                  "KR-Bold", 7.4, self.accent, align="right")
        self.text(MX, 813.5, FOOTER_NOTICE, "KR", 6.8, MUTED)

    def cover_header(self):
        """1페이지 헤더 — AREA / 출처 / 학년 / Name·Date / 주제."""
        d = self.doc
        self.text(MX, 52.4, f"AREA · {d['area']}", "KR-Bold", 9.5, self.accent)
        self.text(MX + 132, 52.4, f"No. {d['topic_no']:03d}", "KR-Bold", 9.5, MUTED_2)
        self.text(MX, 70.1, f"Past Test · {d.get('source_academy') or '—'}",
                  "KR-Bold", 8.8, MUTED)
        self.text(MX, 87.3, f"{self.grade} | {SUBTITLE[self.grade]}", "KR-Bold", 11.0, self.deep)

        self.text(422.4, 72.8, "Name", "KR", 10.5, MUTED_2)
        self.rule(456.8, 80.3, 65.2, LINE_2, 0.8)
        self.text(422.4, 93.8, "Date", "KR", 10.5, MUTED_2)
        self.rule(450.3, 101.3, 71.7, LINE_2, 0.8)

        end = self.para(MX, 110.0, d["topic"], "KR-Bold", 16.0, INK, width=CW - 130, leading=20)
        return max(end, 132.0)

    def running_header(self, extra=None):
        """2페이지 이후 헤더."""
        d = self.doc
        kicker, title = PAGE_LABELS[self.grade][self.page_no]
        self.text(MX, 53.3, f"{self.grade} | {kicker}", "KR-Bold", 10.2, self.accent)
        end = self.para(MX, 75.2, title, "KR-Bold", 18.0, INK, width=CW, leading=22)
        meta = (f"AREA · {d['area']}   |   No. {d['topic_no']:03d} · "
                f"Past Test · {d.get('source_academy') or '—'}")
        self.text(MX, max(end + 2, 100.2), meta, "KR", 11.0, MUTED)
        line2 = extra or f"Topic: {d['topic']}"
        self.text(MX, max(end + 18, 115.8), line2, "KR", 11.0, MUTED_2)
        return 139.7

    def section(self, num, title, top):
        """번호 사각형 + 제목. 본문이 시작할 top 을 돌려준다."""
        self.box(MX, top, SEC_BOX, SEC_BOX, fill=self.accent)
        self.text(MX + SEC_BOX / 2, top + 7.6, num, "KR-Bold", 10.0, WHITE, align="center")
        self.text(MX + 36.9, top + 8.9, title, "KR-Bold", 14.0, self.deep)
        return top + SEC_BOX + 8.5

    # ---------- 블록 ----------
    def cards(self, top, items, h=96.4):
        """가로 3분할 카드.

        items = [(제목, 본문), ...] 또는 [(카테고리, 질문, 답변), ...]
        3요소일 때는 카테고리를 별도 줄로 올린다 (Grade 3-4 형식).
        """
        gap = 11.3
        w = (CW - gap * 2) / 3
        inner = w - 20

        # 카드 높이는 가장 긴 카드에 맞춘다.
        need = 0
        for it in items[:3]:
            n = 0
            if len(it) > 2:
                n += len(self.wrap(it[0], "KR-Bold", 10.0, inner)) * 13.6
                n += len(self.wrap(it[1], "KR-Bold", 10.6, inner)) * 15.2 + 2
                n += len(self.wrap(it[2], "KR", 10.6, inner)) * 15.2 + 8
            else:
                n += len(self.wrap(it[0], "KR-Bold", 10.6, inner)) * 15.2 + 6
                n += len(self.wrap(it[1], "KR", 10.6, inner)) * 15.2
            need = max(need, n)
        h = max(h, need + 34.0)

        for i, it in enumerate(items[:3]):
            x = MX + i * (w + gap)
            self.box(x, top, w, h, fill=self.soft, stroke=LINE_2)
            self.box(x, top, 2.6, h, fill=self.accent)
            t = top + 15.5
            if len(it) > 2:
                t = self.para(x + 10.2, t, it[0], "KR-Bold", 10.0, self.accent,
                              width=inner, leading=13.6) + 2
                t = self.para(x + 10.2, t, it[1], "KR-Bold", 10.6, self.deep,
                              width=inner, leading=15.2) + 8
                self.para(x + 10.2, t, it[2], "KR", 10.6, INK, width=inner, leading=15.2)
            else:
                t = self.para(x + 10.2, t + 4.3, it[0], "KR-Bold", 10.6, self.deep,
                              width=inner, leading=15.2) + 6
                self.para(x + 10.2, t, it[1], "KR", 10.6, INK, width=inner, leading=15.2)
        return top + h + 21.0

    def label_table(self, top, rows, label_w=102.1, row_h=49.3):
        """좌측 라벨 + 우측 2행(한글 설명 / 영문 힌트) 표."""
        self.box(MX, top, CW, row_h * len(rows), stroke=LINE_2)
        for i, (label, ko, en) in enumerate(rows):
            t = top + i * row_h
            if i % 2 == 0:
                self.box(MX, t, CW, row_h, fill=HexColor("#FCFCFD"))
            self.box(MX, t, CW, row_h, stroke=LINE)
            self.box(MX, t, 2.6, row_h, fill=self.accent)
            self.text(MX + 9.5, t + 13.8, label, "KR-Bold", 11.5, self.deep)
            self.para(MX + label_w, t + 12.8, ko, "KR", 11.0, INK,
                      width=CW - label_w - 12, leading=14.2)
            self.text(MX + label_w, t + 30.6, en, "KR", 10.2, MUTED)
        return top + row_h * len(rows) + 21.0

    def two_lists(self, top, left, right, row_h=29.9):
        """좌우 2열 리스트 (키워드 / 패턴)."""
        gap = 22.7
        w = (CW - gap) / 2
        n = max(len(left), len(right))
        for col, items in ((0, left), (1, right)):
            x = MX + col * (w + gap)
            self.box(x, top, w, row_h * n, stroke=LINE_2)
            for i in range(n):
                t = top + i * row_h
                self.box(x, t, w, row_h, stroke=LINE)
                if i < len(items):
                    it = items[i]
                    if isinstance(it, (list, tuple)):
                        it = ": ".join(str(v) for v in it if str(v).strip())
                    self.box(x + 9.5, t + row_h / 2 - 1.6, 3.2, 3.2, fill=self.accent)
                    self.para(x + 19.0, t + 9.0, str(it), "KR", 10.6, INK,
                              width=w - 28, leading=13)
        return top + row_h * n + 21.0

    def essay_box(self, top, paragraphs, word_count, size=11.0, leading=19.7):
        """모델 에세이 본문 상자 + Word count."""
        inner_w = CW - 47.0
        lines = []
        for p in paragraphs:
            lines.append(self.wrap(p, "KR-Serif", size, inner_w))
        total_lines = sum(len(b) for b in lines) + (len(lines) - 1)
        h = total_lines * leading + 58.0

        self.box(MX, top, CW, h, fill=WHITE, stroke=LINE_2)
        self.box(MX, top, CW, h, stroke=LINE_2)
        self.box(MX, top, 3.4, h, fill=self.accent)

        t = top + 29.0
        for bi, block in enumerate(lines):
            for ln in block:
                self.text(MX + 23.5, t, ln, "KR-Serif", size, INK)
                t += leading
            if bi != len(lines) - 1:
                t += leading * 0.62

        self.text(MX + CW - 18, top + h - 22.0, f"Word count: {word_count}",
                  "KR-Bold", 9.6, self.accent, align="right")
        return top + h + 21.0

    def writing_rows(self, top, n):
        """필기 줄 (테두리 행)."""
        for i in range(n):
            t = top + i * ROW_H
            self.box(MX, t, CW, ROW_H, stroke=LINE_2, lw=0.7)
        return top + n * ROW_H + 21.0

    def checklist(self, top):
        """자가 진단표 — [Target] 전폭 + [1]/[2] 좌우 2단."""
        cl = CHECKLIST[self.grade]

        self.text(MX, top, "■ 3초 감점 차단 자가 진단표 (Self-Evaluation Checklist)",
                  "KR-Bold", 11.5, self.deep)
        top += 17.5
        top = self.para(MX, top, CHECKLIST_INTRO[self.grade], "KR", 9.2, MUTED,
                        width=CW, leading=13.5) + 10.0

        def block(x, w, title, items, top_):
            lines = 0
            wrapped = []
            for it in items:
                ws = self.wrap("□  " + it, "KR", 9.4, w - 24)
                wrapped.append(ws)
                lines += len(ws)
            h = 27.5 + lines * 13.6 + len(items) * 5.0 + 10.0
            self.box(x, top_, w, h, fill=self.soft, stroke=LINE_2)
            self.box(x, top_, w, 2.4, fill=self.accent)
            self.text(x + 11.5, top_ + 12.0, title, "KR-Bold", 9.8, self.deep)
            t = top_ + 31.5
            for ws in wrapped:
                for j, ln in enumerate(ws):
                    self.text(x + (11.5 if j == 0 else 24.0), t, ln, "KR", 9.4, INK)
                    t += 13.6
                t += 5.0
            return h

        h = block(MX, CW, *cl["target"], top)
        top += h + 12.0

        gap = 19.6
        w = (CW - gap) / 2
        h1 = block(MX, w, *cl["grammar"], top)
        h2 = block(MX + w + gap, w, *cl["logic"], top)
        return top + max(h1, h2) + 12.0


# ---------------------------------------------------------------------------
# 학년별 페이지 구성
# ---------------------------------------------------------------------------

def build_g12(c, doc, g):
    d = doc["grades"][g]
    total = 3

    s = Sheet(c, g, doc, 1, total); s.chrome(); top = s.cover_header()
    top = s.section("01", "생각 확장 브레인스토밍 (Brainstorming)", top)
    top = s.cards(top, [_norm_card(b) for b in d["brain"]])
    top = s.section("02", "스토리 뼈대 아웃라인 (Writing Outline)", top)
    top = s.label_table(top, [as_triple(r) for r in d["outline"]])
    top = s.section("03", "키워드 & 핵심 문장 패턴 (Key Words & Patterns)", top)
    s.two_lists(top, d["keywords"], d["patterns"])
    c.showPage()

    s = Sheet(c, g, doc, 2, total); s.chrome(); top = s.running_header()
    top = s.section("04", "아웃라인 기반 에세이 샘플 (Model Essay)", top)
    s.essay_box(top, [d["essay"]], d["word_count"])
    c.showPage()

    s = Sheet(c, g, doc, 3, total); s.chrome(); top = s.running_header()
    top = s.section("05", "실전 영작 연습장 (Practice Space)", top)
    top = s.writing_rows(top, 8)
    s.checklist(top)
    c.showPage()


def build_g34(c, doc, g):
    d = doc["grades"][g]
    total = 3

    s = Sheet(c, g, doc, 1, total); s.chrome(); top = s.cover_header()
    top = s.section("01", "생각 확장 브레인스토밍 (Brainstorming)", top)
    top = s.cards(top, [_norm_card(b) for b in d["brain"]])
    top = s.section("02", "단락 구조 아웃라인 (Topic-Supporting-Closing)", top)
    top = s.label_table(top, [as_triple(r) for r in d["outline"]])
    top = s.section("03", "핵심 논리 연결어 & 표현 (Key Transitions)", top)
    s.two_lists(top, d["vocab"], d["trans"])
    c.showPage()

    s = Sheet(c, g, doc, 2, total); s.chrome(); top = s.running_header()
    top = s.section("04", "구조화된 모범 단락 (Model Paragraph)", top)
    s.essay_box(top, [d["essay"]], d["word_count"])
    c.showPage()

    s = Sheet(c, g, doc, 3, total); s.chrome(); top = s.running_header()
    top = s.section("05", "실전 영작 연습장 (Practice Space)", top)
    top = s.writing_rows(top, 8)
    s.checklist(top)
    c.showPage()


def build_g56(c, doc, g):
    d = doc["grades"][g]
    total = 4

    s = Sheet(c, g, doc, 1, total); s.chrome(); top = s.cover_header()
    top = s.section("01", "정형 4문단 에세이 아웃라인 매트릭스 (4-Paragraph Matrix)", top)
    top = s.label_table(top, [as_triple(r) for r in d["matrix"]], label_w=112.0)
    top = s.section("02", "합격을 가르는 고급 아카데믹 어휘 5종 (Advanced Academic Vocabulary)", top)
    rows = [as_pair(w) for w in d["vocab"]]
    row_h = 26.6
    s.box(MX, top, CW, row_h * len(rows), stroke=LINE_2)
    for i, (word, mean) in enumerate(rows):
        t = top + i * row_h
        if i % 2 == 0:
            s.box(MX, t, CW, row_h, fill=s.soft)
        s.box(MX, t, CW, row_h, stroke=LINE)
        s.text(MX + 12.0, t + 8.0, word, "KR-Bold", 11.0, s.deep)
        s.text(MX + 148.0, t + 8.4, mean, "KR", 10.6, INK)
    c.showPage()

    s = Sheet(c, g, doc, 2, total); s.chrome(); top = s.running_header()
    top = s.section("03", "최상위 탑반 기준 정형 4문단 모델 에세이 (Model Essay)", top)
    paras = d["essay_paras"]
    if isinstance(paras, str):                      # 문단이 통째로 올 때
        paras = [q for q in paras.split(chr(10) * 2) if q.strip()] or [paras]
    s.essay_box(top, [str(p) for p in paras], d["word_count"], size=10.6, leading=17.4)
    c.showPage()

    s = Sheet(c, g, doc, 3, total); s.chrome(); top = s.running_header()
    top = s.section("04", "실전 4문단 에세이 드래프팅 시트 (Formal Essay Sheet)", top)
    s.writing_rows(top, 18)
    c.showPage()

    s = Sheet(c, g, doc, 4, total); s.chrome()
    top = s.running_header(extra=f"Self-Evaluation Checklist | Topic: {doc['topic']}")
    top = s.section("05", "3초 감점 차단 자가 진단표", top)
    s.checklist(top)
    c.showPage()


def _norm_card(item):
    """브레인스토밍 카드. 3요소면 (카테고리, 질문, 답변), 2요소면 (질문, 답변)."""
    if isinstance(item, (list, tuple)):
        vals = [str(v) for v in item]
        return tuple(vals[:3]) if len(vals) >= 3 else (vals + [""])[:2]
    return tuple(_split(item, ":", 2))


BUILDERS = {"Grade 1-2": build_g12, "Grade 3-4": build_g34, "Grade 5-6": build_g56}


# ---------------------------------------------------------------------------



def render(doc, grade):
    """워크북 PDF 를 만들어 bytes 로 돌려준다.

    doc  — {topic_no, area, topic, source_academy?, grades: {grade: {...}}}
    grade — "Grade 1-2" | "Grade 3-4" | "Grade 5-6"
    """
    if grade not in BUILDERS:
        raise ValueError(f"알 수 없는 학년: {grade}")
    if grade not in doc.get("grades", {}):
        raise ValueError(f"{grade} 데이터가 없습니다.")

    register_fonts()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"{doc['topic']} - {grade}")
    c.setAuthor("AXISOLVE EDUTECH")
    c.setSubject("AXISOLVE Writing Workbook")
    c.setCreator("AXISOLVE Writing Engine")
    BUILDERS[grade](c, doc, grade)
    c.save()
    return buf.getvalue()


def slugify(topic):
    s = re.sub(r"[^\w\s-]", "", topic, flags=re.UNICODE).strip()
    return re.sub(r"[\s-]+", "_", s)


def filename(doc, grade):
    return f"{doc['topic_no']:03d}_{grade.replace(' ', '_')}_{slugify(doc['topic'])}.pdf"
