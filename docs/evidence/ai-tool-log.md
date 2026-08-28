# AI 코딩 도구 사용 기록

사용한 도구: **Claude Code** (Anthropic, 모델 Claude Opus 5)

이 프로젝트는 처음부터 끝까지 AI 코딩 도구와 함께 만들었습니다.
스크린샷은 지워지고 대화창은 닫히지만, **커밋 이력은 남습니다.**
그래서 1차 증빙을 커밋 트레일러로 삼습니다 — 아래 명령 한 줄로 누구나 검증할 수 있습니다.

```bash
git log --format='%h %ad %s%n    %(trailers:key=Co-Authored-By,valueonly)' --date=short
```

11개 커밋 **전부** 에 `Co-Authored-By: Claude Opus 5` 트레일러가 붙어 있습니다.

---

## 1. 커밋별 작업 내역

| # | 커밋 | 날짜 | AI 에게 시킨 일 | 남은 결과물 |
|---|---|---|---|---|
| 1 | `2684659` | 08-24 | 기출 주제 DB 를 읽어 학년별 에세이를 생성하는 바닐라 웹앱의 뼈대 | `index.html` `app.js` `styles.css` `api/generate.py` |
| 2 | `7c7c357` | 08-24 | AI 제공자 교체 (프론트는 그대로 두고 서버 함수만) | `api/generate.py` 재작성 |
| 3 | `267be2e` | 08-25 | 비용 폭주 방어 · 카카오 로그인 · 크레딧 · 랜딩 재구성 | `api/_guard.py` `api/_supabase.py` `auth.js` `landing.css` |
| 4 | `1f06125` | 08-25 | 주제 165개와 출제 학원명이 URL 하나로 통째로 새지 않게 | `api/topics.py` `tools/build_topics.py` `.vercelignore` |
| 5 | `b7c09d9` | 08-25 | 생성 결과를 A4 워크북 PDF 로 (한글 폰트 포함) | `api/pdf.py` `api/_workbook.py` `api/_fonts/` |
| 6 | `da09e5f` | 08-25 | **버그 수정** — 생성이 전부 실패 | `app.js` 수정 + `tools/smoke_app.js` 신규 |
| 7 | `cd6de8f` | 08-25 | **버그 수정** — 어휘표에 한 글자만 | `api/_workbook.py` 수정 + `tools/smoke_workbook.py` 신규 |
| 8 | `fc7f232` | 08-25 | **버그 수정** — 표 글자 겹침 | `api/_workbook.py` 행 높이 계산 |
| 9 | `e55507c` | 08-25 | Vercel 배포 설정 보강 | `vercel.json` |
| 10 | `7d7878e` | 08-28 | **과제 대응** — README 가 안내하는 `dev_server.py` 가 없음 | `dev_server.py` 신규 |
| 11 | `bdc5e87` | 08-28 | **과제 대응** — 응답 지연/타임아웃 안내가 없음 | `app.js` `styles.css` |

## 2. "시키는 대로" 가 아니었던 지점

과제가 요구하는 것은 AI 로 코드를 뽑았다는 사실이 아니라,
**AI 가 낸 코드에서 오류를 스스로 찾고 고칠 수 있는가** 입니다. 실제로 그랬던 세 건입니다.

### 6번 커밋 — AI 가 만든 코드가 통째로 안 돌아갔다

직접 입력 주제 기능을 붙인 뒤 **모든** 생성이 실패했습니다.
`node --check app.js` 는 통과했습니다. 문법은 맞았기 때문입니다.

브라우저 콘솔에서 `customNote is not defined` 를 보고 원인을 찾았습니다.
AI 가 `customNote` 를 **쓰는 쪽만 넣고 선언을 빠뜨린** 것입니다.

여기서 고치고 끝내지 않고, **같은 종류가 다시 나올 것**이라고 보고
`tools/smoke_app.js` 를 만들어 최소 DOM 위에서 `app.js` 를 실제로 실행하게 했습니다.
수정 전 코드에 돌려서 이 버그를 실제로 잡는 것까지 확인했습니다.

### 7번 커밋 — 에러 없이 조용히 틀렸다

PDF 어휘표에 `perspective: 관점` 이 `p` 와 `e` 로 찍혔습니다.
`app.js` 가 요구한 스키마는 `"단어: 뜻"` 문자열인데 손으로 만든 샘플은 `["단어","뜻"]`
리스트였고, 렌더러가 `w[0]`, `w[1]` 로 꺼냈습니다.
문자열도 리스트도 `[0]` 이 되므로 파이썬은 아무 오류도 내지 않았습니다.

### 10번 커밋 — 이번 과제를 준비하다 발견

`git clone` 을 새 폴더에 받아 README 대로 따라 해 봤더니, README 가 안내하는
`py dev_server.py` 의 그 파일이 저장소에 없었습니다.
`.gitignore` 에 `dev_server.py` 가 적혀 있어 한 번도 커밋되지 않았고,
**내 PC 에는 있으니 나만 몰랐던** 것입니다.

받아 간 사람 입장에서 README 를 따라 해 보는 것 말고는 이 종류를 잡을 방법이 없었습니다.

## 3. 이번 과제 대응 작업 (08-28) 상세

| 시킨 일 | AI 가 한 일 | 사람이 잡아낸 것 |
|---|---|---|
| "README 대로 로컬 실행이 되게 하라" | `dev_server.py` 작성 — Vercel 라우팅 규칙(`api/<이름>.py` 의 `handler`)을 흉내 | 첫 판은 `handler.do_POST(self)` 로 **메서드만 빌려** 실행했다. 함수 파일들이 자기 클래스의 `_read_json` 을 쓰기 때문에 `AttributeError` 로 500 이 났다. `__init__` 없이 만든 객체에 요청의 인스턴스 딕셔너리를 공유시키는 방식으로 고쳤다 |
| "응답이 늦을 때 안내가 없다" | `AbortController` 로 75초 타임아웃 + 20초 지연 안내 | 처음엔 `var(--warn, #C98A00)` 로 폴백만 뒀는데, `--warn` 변수가 애초에 없었다. `--good` `--bad` 옆에 `--warn` 을 제대로 정의했다 |
| "실패 처리를 문서로 정리하라" | `docs/test-cases.md` 작성 | **돌려 보지 않은 것을 돌려 본 것처럼 적지 않도록** 상태 칸(✅ 확인 / 🖐 수동 / 🔑 키 필요)을 나눠 표기하게 했다 |

`dev_server.py` 의 첫 판이 낸 실제 오류:

```
File "dev_server.py", line 124, in serve_api
    fn(self)
File "api/generate.py", line 36, in do_POST
    payload = self._read_json()
AttributeError: 'DevHandler' object has no attribute '_read_json'
```

고친 뒤 확인한 결과:

```
POST /api/generate  (키 없음)   → 500  {"error": "OPENAI_API_KEY 가 설정되지 않았습니다. …"}
POST /api/generate  (빈 프롬프트) → 400  {"error": "생성 요청이 비어 있습니다. …"}
GET  /api/topics                → 200  주제 165개, 출제 학원명 미포함
GET  /api/_guard.py             → 404
GET  /topics.json               → 404
```

## 4. 직접 채울 것 — 대화 화면 캡처

커밋 트레일러는 "AI 를 썼다" 는 것까지만 증명합니다.
**어떻게 물었는지**는 대화 화면으로 보여야 합니다. 아래 세 장을 `screenshots/` 에 넣으십시오.

| 파일명 | 담을 내용 |
|---|---|
| `14-ai-tool-prompt.png` | 기능을 요청한 프롬프트와 AI 의 응답이 함께 보이는 화면 |
| `15-ai-tool-debug.png` | **오류를 물어보고 원인을 좁혀 간 대화** — 채점에서 가장 중요한 한 장입니다 |
| `16-ai-tool-diff.png` | AI 가 제안한 수정안과 그것을 적용한 화면 |

15번은 "고쳐 줘" 보다 **오류 메시지·재현 조건·의심 지점을 적어 물은 대화**를 고르십시오.
그 화면이 과제 3절 6항(오류 원인을 파악하고 수정 방향을 말로 설명할 수 있다)의 증거가 됩니다.
