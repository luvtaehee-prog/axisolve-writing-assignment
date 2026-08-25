# -*- coding: utf-8 -*-
"""워크북 고정 문구 — 학년별 자가 진단표와 페이지 라벨.

layout_spec.md 는 자가 진단표의 블록 구조([Target] / [1] / [2])만 정하고
실제 문항은 정하지 않는다. 아래 문항은 기존 샘플 PDF
(AXISOLVE_Writing_001-005_Final)에서 추출해 정리한 것이며, 이것이 사실상의
확정본이다. 문항을 바꾸려면 이 파일만 고치면 된다.
"""

# 학년별 subtitle (layout_spec.md)
SUBTITLE = {
    "Grade 1-2": "라이팅 워크북",
    "Grade 3-4": "논리 단락 완성 워크북",
    "Grade 5-6": "정형 4문단 아카데믹 에세이",
}

# 학년별 색 (app.js 의 GRADE_COLOR 와 동일하게 유지할 것)
PALETTE = {
    "Grade 1-2": {"accent": "#A65C46", "soft": "#F8F0EC", "deep": "#713E30"},
    "Grade 3-4": {"accent": "#39766D", "soft": "#ECF5F2", "deep": "#27554F"},
    "Grade 5-6": {"accent": "#3F5873", "soft": "#EEF2F6", "deep": "#273C51"},
}

# 2페이지 이후 러닝 헤더에 쓰는 (kicker, 제목)
PAGE_LABELS = {
    "Grade 1-2": {
        2: ("Model Writing", "아웃라인 기반 에세이 샘플 (Model Essay)"),
        3: ("Drafting & Self-Check", "실전 영작 연습장 (Practice Space)"),
    },
    "Grade 3-4": {
        2: ("Model Writing", "구조화된 모범 단락 (Model Paragraph)"),
        3: ("Drafting & Self-Check", "실전 영작 연습장 (Practice Space)"),
    },
    "Grade 5-6": {
        2: ("Model Writing", "최상위 탑반 기준 정형 4문단 모델 에세이 (Model Essay)"),
        3: ("Drafting Space", "실전 4문단 에세이 드래프팅 시트 (Formal Essay Sheet)"),
        4: ("Self-Check", "3초 감점 차단 자가 진단표"),
    },
}

CHECKLIST_INTRO = {
    "Grade 1-2": "글을 다 쓰고 난 후, 아래 체크리스트를 하나씩 체크하며 소리 내어 검토하는 습관이 '합격'을 가릅니다.",
    "Grade 3-4": "글을 다 쓰고 난 후, 아래 체크리스트를 하나씩 체크하며 소리 내어 검토하는 습관이 '합격'을 가릅니다.",
    "Grade 5-6": "글을 다 쓰고 난 후, 아래 체크리스트를 검토하는 습관이 '합격'을 가릅니다.",
}

# (블록 제목, [문항, ...])
CHECKLIST = {
    "Grade 1-2": {
        "target": ("[Target] 학년별 합격 기준 가드 (Grade 1-2)", [
            "합격선 분량: 5~7문장(약 70단어 전후)을 충분히 채웠는가?",
            "문장 기본기: 단순 단어 나열을 피하고 주어+동사+목적어가 조화된 완전한 기본 문장을 "
            "구사했는가? (단, don't, can't 등 자연스러운 구어적 표현이나 줄임말은 허용됨)",
        ]),
        "grammar": ("[1] 필수 문법 감점 가드 (Grammar Guard)", [
            "시제 앵커 일치: 현재와 과거 동사가 혼용되지 않고 글의 상황에 맞는 시제가 "
            "일관되게 이어지는가?",
            "주어-동사 수일치: 3인칭 단수 주어 뒤 동사에 s/es가 올바르게 붙어 있는가?",
            "관사 및 단복수: 셀 수 있는 명사 앞 a/an이 누락되거나 복수형 s가 빠지지 않았는가?",
        ]),
        "logic": ("[2] 논리 구조 감점 가드 (Logical Layout)", [
            "글의 흐름: Opening → Detail 1 → Detail 2 → Closing의 순서가 자연스럽게 이어지는가?",
            "연결어 활용: and, then, because 등의 연결어가 문맥에 맞게 자연스럽게 쓰였는가?",
            "소리 내어 읽기: 글을 소리 내어 읽었을 때 막힘없이 자연스럽게 이어지는가?",
        ]),
    },
    "Grade 3-4": {
        "target": ("[Target] 학년별 합격 기준 가드 (Grade 3-4)", [
            "합격선 분량: 약 120단어 전후의 1문단 구조를 완성했는가?",
            "논리 뼈대 체화: 단순 사건 나열에서 벗어나 Topic Sentence → Supporting Details → "
            "Closing의 구조를 지켰는가?",
            "문장 조화: 단문과 복문(접속사 활용)을 조화롭게 섞어 구성했는가?",
        ]),
        "grammar": ("[1] 필수 문법 감점 가드 (Grammar Guard)", [
            "시제 앵커 일치: 글의 상황과 목적에 맞는 시제를 일관되게 유지했는가?",
            "주어-동사 수일치: 3인칭 단수 주어 뒤 동사에 s/es가 올바르게 붙어 있는가?",
            "관사 및 단복수: 셀 수 있는 명사 앞 a/an이 누락되거나 복수형 s가 빠지지 않았는가?",
        ]),
        "logic": ("[2] 논리 구조 감점 가드 (Logical Layout)", [
            "단락 구조: 하나의 Paragraph 안에서 Topic Sentence → Supporting Details → "
            "Closing Sentence가 명확히 연결되는가?",
            "연결어 활용: 문장 사이의 관계를 보여주는 전환어가 과하지 않게 사용되었는가?",
            "소리 내어 읽기: 문장이 끊기지 않고 하나의 중심 생각으로 자연스럽게 이어지는가?",
        ]),
    },
    "Grade 5-6": {
        "target": ("[Target] 학년별 합격 기준 가드 (Grade 5-6)", [
            "합격선 분량: 정형화된 4문단 에세이(서론-본론1-본론2-결론) 형태와 약 200단어를 "
            "달성했는가?",
            "포멀 에세이 어조: 구어체 축약형 단어(don't, can't 등)를 배제하고 문장 표현을 "
            "정돈했는가?",
            "시점 및 어휘: Prompt 유형에 맞는 시점을 일관되게 유지하고, 포멀한 어조와 적절한 "
            "고급 어휘를 사용했는가?",
        ]),
        "grammar": ("[1] 필수 문법 감점 가드 (Grammar)", [
            "시제 앵커: 문단 전체에서 상황에 맞는 시제가 일관되게 유지되는가?",
            "수일치: 주어와 동사의 수가 정확하게 일치하는가?",
            "단복수·관사: 명사의 단복수와 a/an/the 사용이 정확한가?",
        ]),
        "logic": ("[2] 논리 구조 감점 가드 (Logical Layout)", [
            "문단 구조: Introduction → Body 1 → Body 2 → Conclusion의 역할이 명확한가?",
            "Evidence & Elaboration: 근거·예시 뒤에 그 의미를 설명하는 상술이 충분한가?",
            "Coherence: Thesis와 두 본론이 직접 연결되고 결론이 단순 반복을 넘어 의미를 "
            "확장하는가?",
        ]),
    },
}

# 푸터 (layout_spec.md 공통 푸터)
BRAND_LINE_1 = "AXISOLVE WRITING | 영어교육의 바른 축"
BRAND_LINE_2 = "Premium Writing Workbook · For AXISOLVE Students"
FOOTER_COPYRIGHT = "© AXISOLVE · FOR AUTHORIZED STUDENTS ONLY"
FOOTER_NOTICE = ("본 워크북은 AXISOLVE 학습자 전용 교육자료입니다. "
                 "무단 복제·촬영·스캔·공유·배포 및 온라인 게시를 금합니다.")
