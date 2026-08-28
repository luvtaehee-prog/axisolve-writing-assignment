# AXISOLVE Writing Engine

> **배포 주소** — <!-- DEPLOY_URL -->_배포 후 이 자리에 새 프로젝트 주소를 넣습니다_ → [배포 절차](docs/deploy-guide.md)
> **저장소** — https://github.com/luvtaehee-prog/axisolve-writing-assignment

어학원 레벨테스트의 채점 루브릭을 코드에 내장한 영어 라이팅 트레이닝 서비스입니다.
**기출 165개 주제에서 고르거나, 원하는 주제와 아이디어를 직접 입력**하면
학년별 합격 기준(단어 수·문장 수·문단 구조·격식)에 맞춘 모범 답안이 생성됩니다.

핵심은 "생성"이 아니라 **"기준 통과까지 생성"** 입니다. 응답을 받는 즉시 기계가
분량과 구조를 검사하고, 미달이면 최대 4회까지 자동으로 다시 씁니다.

## 기술 스택

| 계층 | 사용 기술 |
|---|---|
| 프론트엔드 | 바닐라 HTML / CSS / JavaScript — **프레임워크·빌드 도구·CDN 없음** (`package.json` 이 없습니다) |
| 라우팅 | `location.hash` 기반 섹션 전환 (`nav.js`) |
| 백엔드 | Vercel Python Serverless Functions (`api/` 아래 엔드포인트 5개) |
| AI | OpenAI Responses API (`api/generate.py`) |
| PDF | reportlab — 서버 렌더링 (`api/_workbook.py`) |
| 계정·크레딧 | Supabase / 카카오 로그인 — 환경변수 미설정 시 자동 비활성 |
| 임시 저장 | 브라우저 localStorage (생성 초안) |
| 배포 | Vercel (GitHub 연동 자동 배포) |

## 과제 산출물 문서

| 문서 | 내용 |
|---|---|
| [docs/service-plan.md](docs/service-plan.md) | **서비스 기획서** — 목적·타겟·페이지 구성·AI 기능의 입력/출력/실패 처리 |
| [docs/submission-checklist.md](docs/submission-checklist.md) | 과제 요구사항 한 줄씩과 그 근거 파일의 대응표 |
| [docs/test-cases.md](docs/test-cases.md) | 테스트 케이스와 실행 기록 (실제로 돌린 것과 아닌 것을 구분) |
| [docs/learning-notes.md](docs/learning-notes.md) | 과제 목표 6항목에 대한 답 |
| [docs/bonus.md](docs/bonus.md) | 보너스 과제 대응 (한 것과 안 한 것) |
| [docs/evidence/](docs/evidence/) | 증빙 자료 — 스크린샷 규격과 AI 코딩 도구 사용 기록 |
| [docs/deploy-guide.md](docs/deploy-guide.md) | 이 저장소로 Vercel 프로젝트를 만드는 절차와 확인 명령 |

이 문서들은 `.vercelignore` 의 `docs/` 규칙에 따라 **배포본에는 올라가지 않습니다.**

## 이용 구조

| 단계 | 내용 |
|---|---|
| 비회원 | 무료 **2회** 체험 |
| 카카오 로그인 | 가입 보너스 **3회** |
| 충전 | 라이트 30회 4,900원 · 스탠다드 100회 12,900원 · 프로 500회 39,000원 |

생성 1회 = 1크레딧. **자동 재시도는 추가 차감하지 않습니다**(최대 4회 호출돼도 1크레딧).
생성 실패 시 자동 환불되며, 모든 변동이 `credit_ledger` 에 기록됩니다.

사업자등록 전이므로 결제는 **충전 코드제**로 운영합니다.
발급 절차는 [docs/admin-codes.md](docs/admin-codes.md) 를 참조하십시오.

## 화면 구성 (4개 섹션)

| 해시 | 섹션 | 내용 |
|---|---|---|
| `#home` | 소개 (랜딩) | 히어로 · 4대 채점 루브릭 · 학년별 기준표 · 과외의 한계 · 자가진단 · 해결 흐름 · CTA |
| `#generator` | 에세이 생성 | 기출 주제 선택 또는 **직접 입력** → 학년 선택 → AI 생성 |
| — | 주제 검색 | 번호 · 주제문 · 영역으로 검색 (학원명 검색은 DB 보호를 위해 제외) |
| `#pricing` | 요금제 | 4개 상품 · 충전 코드 등록 |
| `#about` | 사용법 · FAQ | 4단계 사용법, 자주 묻는 질문 10개 |

## AI 기능

1. **입력** — 주제(165개 기출 중 택1 **또는 직접 입력**) + 학년(초1-2 / 초3-4 / 초5-6) + 아이디어(선택)
   - 직접 입력 주제는 **한글로 적어도 영어 에세이로 나옵니다.** 학년 기준은 동일하게 적용됩니다.
2. **처리** — 브라우저가 `POST /api/generate` 호출 → Python 함수가 서버에서 OpenAI API 호출
3. **출력** — 브레인스토밍 질문, 아웃라인, 어휘·문형, 에세이 본문
   - **워크북 PDF 내려받기** — 학년별 3~4페이지 A4 서식 (`docs/layout_spec.md`)
4. **자동 검증** — 단어 수·문장 수·문단 수·축약형 사용 여부를 브라우저가 검사하고,
   기준 미달이면 부족한 항목을 프롬프트에 명시해 **최대 4회까지 자동 재생성**

### 실패 처리

| 상황 | 사용자에게 보이는 처리 |
|---|---|
| 주제 미선택 | 생성 버튼 비활성 / "왼쪽 목록에서 주제를 선택하십시오" 안내 |
| 직접 입력 주제가 2자 미만 | "주제를 입력해 주십시오." + 입력칸으로 포커스 이동 |
| 생성 진행 중 | 버튼 잠금 + 시도 횟수 표시(1/4 …) |
| **응답이 20초 초과** | "응답이 평소보다 오래 걸리고 있습니다. 창을 닫지 말고 기다려 주십시오." (요청은 계속) |
| **응답이 75초 초과** | 요청을 끊고 "응답이 75초를 넘겨 중단했습니다. 잠시 후 다시 시도해 주십시오." |
| **서버에 닿지 못함** | "AI 서버에 연결하지 못했습니다. 인터넷 연결을 확인한 뒤 다시 시도해 주십시오." |
| API 키 미설정 | "OPENAI_API_KEY 가 설정되지 않았습니다" (HTTP 500) |
| 호출량 초과 | "요청이 몰려 잠시 처리할 수 없습니다" (HTTP 429) |
| 네트워크 오류 | "AI 서버에 연결하지 못했습니다" (HTTP 504) |
| 모델 권한 없음 | "모델에 접근할 권한이 없습니다" (HTTP 500) |
| 출력 토큰 초과로 잘림 | "응답이 완성되지 않았습니다" (HTTP 502) → 자동 재시도 |
| 응답 형식 오류 | "응답에서 JSON을 찾을 수 없음" → 자동 재시도 |
| 4회 모두 기준 미달 | 가장 근접한 결과 표시 + 화면에 경고 배지 |

75초는 서버 함수 상한(`vercel.json` 의 `maxDuration` 60초)보다 길게 잡았습니다.
서버가 자기 판단으로 끝낼 기회를 먼저 주고, 그래도 아무 말이 없을 때 브라우저가 끊습니다.
반대로 잡으면 서버는 정상 처리 중인데 브라우저만 포기합니다.

재현 방법과 실행 기록은 [docs/test-cases.md](docs/test-cases.md) 에 있습니다.

## 워크북 PDF

생성 결과를 학생이 손으로 따라 쓸 수 있는 A4 워크북으로 내려받습니다.
양식은 [docs/layout_spec.md](docs/layout_spec.md) 에 고정되어 있습니다.

| 학년 | 페이지 | 구성 |
|---|---|---|
| Grade 1-2 | 3 | 브레인스토밍·아웃라인·키워드 / 모델 에세이 / 연습장+자가진단 |
| Grade 3-4 | 3 | 브레인스토밍·아웃라인·연결어 / 모델 단락 / 연습장+자가진단 |
| Grade 5-6 | 4 | 매트릭스·어휘 / 모델 에세이 / 드래프팅 시트 / 자가진단 |

**PDF는 서버에서 만듭니다**(`POST /api/pdf`). 헤더의 `Past Test · {출제 학원명}` 때문입니다.
학원명은 브라우저로 내려보내지 않으므로, 서버에서 만들어야 노출 없이 찍을 수 있습니다.
브라우저가 보낸 주제·영역·학원명은 신뢰하지 않고 `topic_no` 로 서버 DB를 조회해 덮어씁니다.

크레딧은 차감하지 않습니다. 생성 시점에 이미 받았고 PDF 자체의 추가 원가는 0입니다.

로컬에서 직접 뽑으려면:

```bash
py tools/make_workbook.py <source.json> -o <출력폴더>
py tools/make_workbook.py <source.json> --grade "Grade 1-2"
```

> **폰트** — Vercel 서버에는 한글 폰트가 없어 저장소에 동봉합니다.
> 한자를 덜어낸 서브셋이며(11.8MB → 5.55MB), `py tools/build_fonts.py` 로 다시 만듭니다.

## 주제 DB 보호

165개 주제와 출제 학원명은 이 서비스의 자산이므로 배포본에서 직접 내려받을 수 없게 했습니다.

| 파일 | 배포 | 내용 |
|---|---|---|
| `topics.json` | ❌ `.vercelignore` 로 제외 | 원본. **출제 학원명(`src`) 포함** |
| `api/_topics.py` | ✅ | `src` 를 제거한 사본. 파이썬 모듈이라 정적 서빙 불가 |
| `api/_topics_full.py` | ✅ | `src` 포함. **서버 전용** — PDF 헤더에만 쓰이고 응답에 넣지 않음 |

브라우저는 `GET /api/topics` 로만 목록을 받으며, 이 응답에는 학원명이 들어가지 않습니다.
엔드포인트에는 출처 검증과 IP당 시간 40회 상한이 걸려 있습니다.

`docs/`, `supabase/`, `tools/`, `README.md` 도 배포에서 제외됩니다.
그대로 두면 `/docs/unit-economics.md` 같은 경로로 원가·마진 자료가 공개됩니다.

> **주제를 수정한 뒤에는 반드시 다시 생성하십시오.**
> ```bash
> py tools/build_topics.py
> ```
> `topics.json` 만 고치고 커밋하면 배포본에는 반영되지 않습니다.

완전한 차단은 불가능합니다. 목록은 결국 화면에 렌더되므로 마음먹으면 수집할 수 있습니다.
목적은 "URL 하나로 전부 받기"를 막는 것입니다.

## API 키 보안

브라우저는 같은 도메인의 `/api/generate` 만 호출합니다.
OpenAI API 호출과 인증은 전부 서버 함수 안에서 일어나며,
키는 Vercel 환경변수 `OPENAI_API_KEY` 에만 존재합니다.
프론트엔드 코드·네트워크 응답 어디에도 키가 포함되지 않습니다.

## 파일 구성

```
axisolve-writing-engine/
├── index.html          # 4개 섹션 마크업
├── styles.css          # 생성기 다크 UI (브랜드: 네이비 #05152E / 라임 #CCFF00)
├── landing.css         # 랜딩 · 요금제 · FAQ (밝은 배경 + 다크 밴드 교차)
├── landing.js          # 자가진단 체크리스트 · 충전 문의 · 코드 등록
├── nav.js              # 섹션 해시 라우팅
├── app.js              # 주제 목록·프롬프트 생성·검증·재시도·렌더링
├── topics.json         # 165개 실전 주제 DB (원본, 배포 제외)
├── tools/build_topics.py  # topics.json → api/_topics.py 생성
├── api/topics.py       # 주제 목록 엔드포인트
├── api/_topics.py      # 자동 생성 (출제 학원명 제거본)
├── api/_topics_full.py # 자동 생성 (서버 전용, 학원명 포함)
├── api/pdf.py          # 워크북 PDF 생성·내려받기
├── api/_workbook.py    # PDF 렌더링 코어 (CLI 와 공유)
├── api/_fonts/         # Noto Sans KR 서브셋 (배포본 동봉)
├── tools/build_fonts.py   # 폰트 서브셋 생성
├── api/generate.py     # Vercel Python Serverless Function (OpenAI API 프록시)
├── api/_guard.py       # 비용 방어 (출처 검증 · 레이트리밋 · 전역 상한)
├── api/_supabase.py    # 로그인 검증 · 크레딧 조작
├── api/me.py           # 로그인 상태 · 잔액 조회
├── api/redeem.py       # 충전 코드 등록
├── auth.js             # 카카오 로그인 (의존성 없음)
├── privacy.html        # 개인정보 처리방침
├── terms.html          # 이용약관 (생성물 제출 금지 조항)
├── refund.html         # 환불 규정
├── legal.css           # 위 세 문서 공용 스타일
├── supabase/           # DB 스키마 (schema.sql · redeem.sql)
├── dev_server.py       # 로컬 개발 서버 (Vercel 라우팅 흉내, 배포 제외)
├── tools/smoke_app.js     # app.js 회귀 테스트 (브라우저 없이 실행)
├── tools/smoke_workbook.py # 워크북 PDF 회귀 테스트
├── docs/               # 기획서 · 테스트 · 학습 정리 · 증빙 (배포 제외)
├── requirements.txt    # openai · reportlab
├── vercel.json         # 함수 실행 시간 · 보안 헤더 · 내부 모듈 차단
├── .env.example        # 로컬 개발용 환경변수 예시
└── .vercelignore       # 배포본에서 뺄 것 (주제 원본 · 문서 · 도구)
```

프론트엔드(루트의 `*.html` `*.css` `*.js`)와 백엔드(`api/`)가 폴더로 갈려 있습니다.

## 배포 방법 (Vercel)

1. 이 폴더를 GitHub 저장소에 푸시합니다.
2. [vercel.com](https://vercel.com) → **Add New… > Project** → 저장소를 선택합니다.
3. Framework Preset은 **Other**, Build Command·Output Directory는 비워 둡니다.
   (`requirements.txt` 가 있으면 Vercel이 `api/` 의 Python 함수를 자동으로 인식합니다.)
4. **Settings > Environment Variables** 에 추가합니다.
   - `OPENAI_API_KEY` — `sk-` 로 시작하는 키 ([platform.openai.com/api-keys](https://platform.openai.com/api-keys) 발급)
   - `ALLOWED_ORIGINS` — 배포된 도메인 (예: `https://your-app.vercel.app`). **비워 두면 누구나 외부에서 호출할 수 있습니다.**
   - `IP_SALT` — 임의의 긴 문자열. 미설정 시 재시작마다 호출 카운터가 초기화됩니다.
   - 선택: `OPENAI_MODEL` (기본값 `gpt-5.6-terra`) · `OPENAI_REASONING_EFFORT` (기본값 `medium`)
   - 선택: `RATE_LIMIT_IP_HOURLY` (12) · `RATE_LIMIT_IP_DAILY` (30) · `RATE_LIMIT_GLOBAL_DAILY` (500)
5. **Deployments > Redeploy** — 환경변수는 재배포 시점에 함수로 전달됩니다.

## 로컬에서 실행하기

```bash
cp .env.example .env.local     # OPENAI_API_KEY 값을 채웁니다
py -m pip install -r requirements.txt
py dev_server.py               # http://localhost:3000
```

`dev_server.py` 는 Vercel 없이 정적 파일과 `api/` 의 모든 엔드포인트를 함께 구동합니다.
Vercel의 파일 기반 라우팅을 흉내내므로 `api/` 에 파일을 추가하면 자동으로 잡힙니다.

배포본에 없는 경로(`topics.json` · `docs/` · `tools/`)와 `/api/_*` 를 로컬에서도 404 로
막습니다. **"로컬은 되는데 배포하면 404"** 를 배포 전에 잡기 위해서입니다.

`OPENAI_API_KEY` 없이도 뜹니다. 화면은 전부 열리고 생성만 500 으로 막히므로,
키 없이 화면·네비게이션·반응형을 확인할 수 있습니다.

회귀 테스트:

```bash
node tools/smoke_app.js       # app.js 를 최소 DOM 위에서 실제로 실행 (13항목)
py tools/smoke_workbook.py    # 워크북 PDF 렌더링
```

`vercel dev` 를 쓰셔도 됩니다(`npm i -g vercel`). 다만 로그인과 프로젝트 연결이 필요합니다.

## Phase 2 설정 (카카오 로그인 · 크레딧)

Supabase 프로젝트와 카카오 개발자 앱 등록이 필요합니다.
**환경변수를 넣기 전까지는 로그인 계층이 꺼진 채 정상 동작합니다.**

→ [docs/setup-phase2.md](docs/setup-phase2.md) (약 30분)

## 비용 방어

생성 버튼을 누를 때마다 OpenAI API가 호출되며, 기준 미달 시 자동 재시도로
한 번에 최대 4회까지 호출될 수 있습니다. `api/_guard.py` 가 세 겹으로 막습니다.

| 계층 | 초과 시 | 기본 상한 |
|---|---|---|
| 출처 검증 (`ALLOWED_ORIGINS`) | 403 | 미설정 시 검사 안 함 |
| IP 시간당 | 429 + `Retry-After` | 12회 |
| IP 일일 | 429 + `Retry-After` | 30회 |
| 전역 일일 | 503 | 500회 |

IP는 `IP_SALT` 를 섞은 SHA-256 해시로만 보관하며 원문은 저장하지 않습니다.

**한계** — 카운터가 함수 인스턴스 메모리에 있어, 인스턴스가 여러 개면 상한이
그만큼 곱해지고 재활용 시 초기화됩니다. 즉 정확한 과금 장치가 아니라
**비용 폭주 차단 장치**입니다. 최종 방어선은 OpenAI 계정의 Budget limit이므로
반드시 함께 설정하십시오. 정확한 횟수 관리는 로그인·DB 도입 시 해소됩니다
([docs/monetization-plan.md](docs/monetization-plan.md) 참조).

### 실측 원가 (`gpt-5.6-luna`, 2026-08-25)

| 학년 | 1회 생성 원가 |
|---|---|
| 초1-2 | 약 1.6원 |
| 초3-4 | 약 2.2원 |
| 초5-6 | 약 14.2원 (추론 토큰이 원가의 대부분) |

"전체 생성"(3학년 일괄) 1건 = 약 18원.
