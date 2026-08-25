# AXISOLVE Writing Engine

어학원 레벨테스트의 채점 루브릭을 코드에 내장한 영어 라이팅 트레이닝 서비스입니다.
**기출 165개 주제에서 고르거나, 원하는 주제와 아이디어를 직접 입력**하면
학년별 합격 기준(단어 수·문장 수·문단 구조·격식)에 맞춘 모범 답안이 생성됩니다.

핵심은 "생성"이 아니라 **"기준 통과까지 생성"** 입니다. 응답을 받는 즉시 기계가
분량과 구조를 검사하고, 미달이면 최대 4회까지 자동으로 다시 씁니다.

- **프론트엔드**: 바닐라 HTML / CSS / JavaScript (프레임워크·빌드 도구 없음)
- **백엔드**: Vercel Python Serverless Functions (`api/`)
- **AI**: OpenAI Responses API
- **계정·크레딧**: Supabase (카카오 로그인) — 미설정 시 자동 비활성

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
| `#pricing` | 요금제 | 4개 상품 · 충전 코드 등록 |
| `#about` | 사용법 · FAQ | 4단계 사용법, 자주 묻는 질문 10개 |

## AI 기능

1. **입력** — 주제(165개 기출 중 택1 **또는 직접 입력**) + 학년(초1-2 / 초3-4 / 초5-6) + 아이디어(선택)
   - 직접 입력 주제는 **한글로 적어도 영어 에세이로 나옵니다.** 학년 기준은 동일하게 적용됩니다.
2. **처리** — 브라우저가 `POST /api/generate` 호출 → Python 함수가 서버에서 OpenAI API 호출
3. **출력** — 브레인스토밍 질문, 아웃라인, 어휘·문형, 에세이 본문
4. **자동 검증** — 단어 수·문장 수·문단 수·축약형 사용 여부를 브라우저가 검사하고,
   기준 미달이면 부족한 항목을 프롬프트에 명시해 **최대 4회까지 자동 재생성**

### 실패 처리

| 상황 | 사용자에게 보이는 처리 |
|---|---|
| 주제 미선택 | 생성 버튼 비활성 / "왼쪽 목록에서 주제를 선택하십시오" 안내 |
| 생성 진행 중 | 버튼 잠금 + 시도 횟수 표시(1/4 …) |
| API 키 미설정 | "OPENAI_API_KEY 가 설정되지 않았습니다" (HTTP 500) |
| 호출량 초과 | "요청이 몰려 잠시 처리할 수 없습니다" (HTTP 429) |
| 네트워크 오류 | "AI 서버에 연결하지 못했습니다" (HTTP 504) |
| 모델 권한 없음 | "모델에 접근할 권한이 없습니다" (HTTP 500) |
| 출력 토큰 초과로 잘림 | "응답이 완성되지 않았습니다" (HTTP 502) → 자동 재시도 |
| 응답 형식 오류 | "응답에서 JSON을 찾을 수 없음" → 자동 재시도 |
| 4회 모두 기준 미달 | 가장 근접한 결과 표시 + 화면에 경고 배지 |

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
├── topics.json         # 165개 실전 주제 DB
├── api/generate.py     # Vercel Python Serverless Function (OpenAI API 프록시)
├── api/_guard.py       # 비용 방어 (출처 검증 · 레이트리밋 · 전역 상한)
├── api/_supabase.py    # 로그인 검증 · 크레딧 조작
├── api/me.py           # 로그인 상태 · 잔액 조회
├── api/redeem.py       # 충전 코드 등록
├── auth.js             # 카카오 로그인 (의존성 없음)
├── supabase/           # DB 스키마 (schema.sql · redeem.sql)
├── requirements.txt    # openai
├── vercel.json         # 함수 실행 시간 설정
└── .env.example        # 로컬 개발용 환경변수 예시
```

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
