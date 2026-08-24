# AXISOLVE Writing Engine

주제를 하나 고르면, 학년별 합격 기준(단어 수·문장 수·문단 구조·격식)에 맞춰
AI가 영어 에세이 모범 답안을 생성하는 웹 서비스입니다.

- **프론트엔드**: 바닐라 HTML / CSS / JavaScript (프레임워크·빌드 도구 없음)
- **백엔드**: Vercel Python Serverless Function 1개 (`api/generate.py`)
- **AI**: OpenAI Responses API

## 화면 구성 (3개 섹션)

| 해시 | 섹션 | 내용 |
|---|---|---|
| `#home` | 소개 | 서비스 설명, 핵심 기능 3가지 |
| `#generator` | 에세이 생성 | 165개 주제 선택 → 학년 선택 → AI 생성 |
| `#about` | 사용법 · FAQ | 4단계 사용법, 자주 묻는 질문 5개 |

## AI 기능

1. **입력** — 주제(165개 중 택1) + 학년(초1-2 / 초3-4 / 초5-6) + 키워드(선택)
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
├── index.html          # 3개 섹션 마크업
├── styles.css          # 반응형 스타일 (브랜드: 네이비 #05152E / 라임 #CCFF00)
├── nav.js              # 섹션 해시 라우팅
├── app.js              # 주제 목록·프롬프트 생성·검증·재시도·렌더링
├── topics.json         # 165개 실전 주제 DB
├── api/generate.py     # Vercel Python Serverless Function (OpenAI API 프록시)
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
   - Key: `OPENAI_API_KEY`
   - Value: `sk-` 로 시작하는 키 ([platform.openai.com/api-keys](https://platform.openai.com/api-keys) 발급)
   - 선택: `OPENAI_MODEL` (기본값 `gpt-5.6-terra`) · `OPENAI_REASONING_EFFORT` (기본값 `medium`)
5. **Deployments > Redeploy** — 환경변수는 재배포 시점에 함수로 전달됩니다.

## 로컬에서 실행하기

```bash
npm install -g vercel
cd axisolve-writing-engine
cp .env.example .env.local     # OPENAI_API_KEY 값을 채웁니다
vercel dev                     # 기본 http://localhost:3000
```

`vercel dev` 는 정적 파일과 `api/` 의 Python 함수를 함께 구동합니다.
정적 화면만 확인하려면 `python -m http.server` 로도 열 수 있지만,
이 경우 `/api/generate` 가 없으므로 생성 기능은 동작하지 않습니다.

## 비용 관련 주의

생성 버튼을 누를 때마다 OpenAI API가 호출되며, 기준 미달 시 자동 재시도로
한 번에 최대 4회까지 호출될 수 있습니다. 공개 배포 시에는 접근 제한(비밀번호,
사용량 한도 등)을 추가하는 것을 권장합니다. 현재 버전에는 접근 제한이 없습니다.
