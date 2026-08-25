# AXISOLVE WRITING WORKBOOK — PDF Layout Specification

## 공통 헤더 (모든 학년 공통)
- 좌상단: "AREA · {area}  No. {topic_no}"
- 우상단: "Past Test · {source_academy}"
- 그 아래 줄: "Grade {grade} | {subtitle}"
- Name / Date 입력란 포함

## 학년별 subtitle
- Grade 1-2: "라이팅 워크북"
- Grade 3-4: "논리 단락 완성 워크북"
- Grade 5-6: "정형 4문단 아카데믹 에세이"

## 공통 푸터 (모든 페이지)
- 1행: "AXISOLVE WRITING | 영어교육의 바른 축"
- 2행: "Premium Writing Workbook · For AXISOLVE Students"
- 3행: "© AXISOLVE · FOR AUTHORIZED STUDENTS ONLY"
- 4행: "본 워크북은 AXISOLVE 학습자 전용 교육자료입니다. 무단 복제·촬영·스캔·공유·배포 및 온라인 게시를 금합니다."
- 5행: "No. {topic_no:03d} · {현재페이지}/{총페이지}"

## 용지
- A4, 세로

## 섹션 번호 표기
- 두 자리 숫자: 01, 02, 03, 04, 05
- 섹션 타이틀: 국문 (영문) 병기

---

## Grade 1-2 — 3페이지 구성

### Page 1
- 01 생각 확장 브레인스토밍 (Brainstorming)
  - Q1 / Q2 / Q3 카드 형태 (질문 + 답변)
- 02 스토리 뼈대 아웃라인 (Writing Outline)
  - 4행: Opening / Detail 1 / Detail 2 / Closing
  - 각 행: 한글 설명 + 영문 키워드
- 03 키워드 & 핵심 문장 패턴 (Key Words & Patterns)
  - keywords 리스트 (좌측)
  - patterns 리스트 (우측)

### Page 2
- 04 아웃라인 기반 에세이 샘플 (Model Essay)
  - Topic 표기
  - 에세이 본문
  - "Word count: {n}" 표기

### Page 3
- 05 실전 영작 연습장 (Practice Space)
  - 필기 줄 공간
  - 자가 진단표 (Self-Evaluation Checklist)
    - [Target] 학년별 합격 기준 가드 (Grade 1-2)
    - [1] 필수 문법 감점 가드 (Grammar Guard)
    - [2] 논리 구조 감점 가드 (Logical Layout)

---

## Grade 3-4 — 3페이지 구성

### Page 1
- 01 생각 확장 브레인스토밍 (Brainstorming)
  - 3개 카드: 번호 + 카테고리명 + 한글 질문 + 영문 답변
- 02 단락 구조 아웃라인 (Topic-Supporting-Closing)
  - 4행: Topic Sentence / Supporting 1 / Supporting 2 / Closing
  - 각 행: 한글 설명 + 영문 키워드
- 03 핵심 논리 연결어 & 표현 (Key Transitions)
  - vocab 리스트 (좌측)
  - trans 리스트 (우측)

### Page 2
- 04 구조화된 모범 단락 (Model Paragraph)
  - Topic 표기
  - 에세이 본문
  - "Word count: {n}" 표기

### Page 3
- 05 실전 영작 연습장 (Practice Space)
  - 필기 줄 공간
  - 자가 진단표
    - [Target] 학년별 합격 기준 가드 (Grade 3-4)
    - [1] 필수 문법 감점 가드 (Grammar Guard)
    - [2] 논리 구조 감점 가드 (Logical Layout)

---

## Grade 5-6 — 4페이지 구성

### Page 1
- 01 정형 4문단 에세이 아웃라인 매트릭스 (4-Paragraph Matrix)
  - 4행: Introduction / Body 1 / Body 2 / Conclusion
  - 각 행: 한글 설명 + 영문 도입 문장
- 02 합격을 가르는 고급 아카데믹 어휘 5종 (Advanced Academic Vocabulary)
  - 단어 + 한글 뜻 (5개)

### Page 2
- 03 최상위 탑반 기준 정형 4문단 모델 에세이 (Model Essay)
  - Topic 표기
  - 4문단 에세이 본문
  - "Word count: {n}" 표기

### Page 3
- 04 실전 4문단 에세이 드래프팅 시트 (Formal Essay Sheet)
  - 필기 줄 공간 (넓게)

### Page 4
- 05 (Self-Check 페이지)
  - 3초 감점 차단 자가 진단표 (Self-Evaluation Checklist)
    - [Target] 학년별 합격 기준 가드 (Grade 5-6)
    - [1] 필수 문법 감점 가드 (Grammar)
    - [2] 논리 구조 감점 가드 (Logical Layout)

---
---

# 구현 노트 (스펙 원문 아님)

> **구현 완료 (2026-08-25)** — 아래 1~8항의 결정은 모두 반영되었습니다.
> 렌더링 코어 `api/_workbook.py` · 엔드포인트 `api/pdf.py` · CLI `tools/make_workbook.py`

아래는 위 스펙을 실제로 구현하기 전에 정리·확정해야 할 사항입니다.
스펙 본문은 위에서 끝났으며, 이 절은 개발 참고용입니다.

## 1. ✅ `{source_academy}` — 서버 생성으로 해결

공통 헤더 우상단의 `"Past Test · {source_academy}"` 는 **지금 구조에서 채울 수 없습니다.**

주제 DB 보호 조치(커밋 `1f06125`)로 출제 학원명(`src`)을 다음과 같이 처리했기 때문입니다.

| 위치 | 학원명 존재 여부 |
|---|---|
| `topics.json` (저장소) | ✅ 있음 |
| 배포본 | ❌ `.vercelignore` 로 제외 |
| `api/_topics.py` | ❌ 생성 시 제거 |
| `GET /api/topics` 응답 | ❌ 없음 |
| 브라우저 `TOPICS` 배열 | ❌ 없음 |

### 이것이 PDF 생성 방식을 결정합니다

| | 브라우저 생성 (jsPDF 등) | 서버 생성 (`/api/pdf`) |
|---|---|---|
| 학원명 표기 | **불가** — 넣으려면 브라우저로 내려보내야 하고, 그 순간 보호가 무너짐 | **가능** — 서버에만 두고 PDF에만 찍음 |
| 서버 부하 | 없음 | 함수 실행 시간·용량 소모 |
| 한글 폰트 | 폰트 파일을 브라우저로 내려받아야 함 (수 MB) | 배포본에 번들 |
| 레이아웃 제어 | 브라우저 렌더링에 의존 | 완전 제어 |
| 크레딧 차감 | 불가(클라이언트 신뢰 불가) | 가능 |

**서버 생성을 채택했습니다.** 구현 결과:

1. `tools/build_topics.py` 가 `api/_topics_full.py`(학원명 포함)를 함께 생성
2. `api/topics.py` 는 학원명 없는 버전만 응답 (변경 없음)
3. `api/pdf.py` 만 `_topics_full` 을 참조해 헤더에 찍음

또한 `api/pdf.py` 는 **브라우저가 보낸 주제·영역·학원명을 신뢰하지 않습니다.**
`topic_no` 로 서버 DB 를 조회해 덮어씁니다. 위조된 값을 보내도 반영되지 않습니다.

## 2. ✅ 직접 입력 주제

`custom: true` 인 문서는 `topic_no = 0` 이고 출처가 없습니다.

| 항목 | 기출 주제 | 직접 입력 |
|---|---|---|
| `No. {topic_no:03d}` | `No. 001` | `No. 000` — 표기 규칙 필요 |
| `Past Test · {source_academy}` | 학원명 | 출처 없음 — 대체 문구 필요 |

확정: 좌상단 `"AREA · 직접 입력"`, 우상단 `"Past Test · Custom Topic"`, 번호는 `No. 000`.

## 3. ✅ 자가 진단표 문항

스펙은 `[Target]` / `[1] Grammar Guard` / `[2] Logical Layout` 세 블록이 있다는 것만
정하고 있고, **실제 체크 문항이 없습니다.** 학년별로 문항을 확정해야 합니다.

다행히 `app.js` 의 `RUBRIC` 과 `assess()` 가 이미 기계적으로 검사하는 항목이 있으므로,
`[Target]` 블록은 이 값에서 자동 생성할 수 있습니다.

| 학년 | 자동 생성 가능한 [Target] 문항 |
|---|---|
| Grade 1-2 | 60~80단어인가 / 5~7문장인가 / 한 문단인가 |
| Grade 3-4 | 100~130단어인가 / 한 문단인가(빈 줄 없음) |
| Grade 5-6 | 180~220단어인가 / 정확히 4문단인가 / 축약형을 쓰지 않았는가 |

확정: 기존 샘플 PDF 에서 학년별 문항 8~9개를 추출해 `api/_workbook_content.py` 에
정리했습니다. 문항을 바꾸려면 그 파일만 고치면 됩니다.

## 4. 미확정 수치

| 항목 | 확정 필요 |
|---|---|
| 필기 줄 공간 | 줄 수, 줄 간격(mm), 줄 색상 |
| 여백 | 상하좌우 마진(mm) |
| 본문 서체 크기 | 학년별로 다르게 할지 (초1-2는 크게) |
| 영문 서체 | 필기 연습용이면 4선지 형태가 필요한지 |

## 5. ✅ 폰트

Noto Sans KR(OFL, 임베드 가능)을 씁니다. Vercel 서버에는 한글 폰트가 없으므로
저장소에 함께 넣어야 하는데, 원본 Regular/Bold 합계가 11.8MB 로 큽니다.

`tools/build_fonts.py` 가 **한자 8,138자를 덜어낸 서브셋**을 만들어
`api/_fonts/` 에 넣습니다. 11.8MB → 5.55MB(53% 감소).

유지 범위: 한글 완성형 전체 · 자모 · 라틴 · 문장부호 · 화살표(→) · 도형(□) ·
CJK 문장부호 · 통화 기호. **한자는 렌더링되지 않습니다.**

원본 샘플은 모델 에세이 본문에만 Noto Serif 를 썼으나, 정적 Serif 가 없으면
가변 폰트가 ExtraLight 로 잡혀 본문이 지나치게 얇아집니다. 현재는 Sans 로
통일했고, `NotoSerifKR-Regular.ttf` 를 넣으면 자동으로 다시 쓰입니다.

## 6. ✅ Word count 산출

`"Word count: {n}"` 은 `app.js` 의 `wordCount()` 와 **같은 규칙**을 써야 합니다.
화면에 표시된 수치와 PDF 수치가 다르면 신뢰를 잃습니다.

```js
String(t || "").match(/[A-Za-z0-9'’-]+/g)
```

`api/pdf.py` 의 `_word_count()` 가 같은 정규식을 쓰며, 브라우저가 보낸 값을
무시하고 **서버가 다시 셉니다.** 화면 수치와 어긋날 수 없습니다.

## 7. 저작권 문구와 실제 보호 수준

푸터 3~4행의 `"FOR AUTHORIZED STUDENTS ONLY"` / `"무단 복제·촬영·스캔·공유·배포 금지"` 는
법적 고지이지 기술적 보호가 아닙니다. PDF는 배포되는 순간 통제할 수 없습니다.

실질적인 억제 수단으로 검토할 만한 것:

- 다운로드한 학생의 이름을 헤더 `Name` 란에 미리 인쇄 (유출 시 추적 가능)
- 페이지 배경에 옅은 워터마크로 계정 식별자 삽입
- PDF 생성 시 다운로드 이력을 `credit_ledger` 에 기록

**미결** — 아직 넣지 않았습니다. 유출 추적이 필요해지면 그때 검토합니다.

## 8. ✅ 크레딧 정책

PDF 다운로드에 크레딧을 차감할지 결정해야 합니다.

| 안 | 설명 |
|---|---|
| A | 생성에만 차감, 다운로드는 무료 (**권장** — 이미 낸 값에 대한 결과물) |
| B | 다운로드마다 차감 |
| C | 첫 다운로드 무료, 재다운로드 차감 |

**A 를 채택했습니다.** 생성 1회에 이미 1크레딧을 받았고 PDF 자체의 추가 원가는
사실상 0입니다. 대신 `api/pdf.py` 에 IP 기준 시간당 40회 상한을 걸어 남용을 막습니다.
