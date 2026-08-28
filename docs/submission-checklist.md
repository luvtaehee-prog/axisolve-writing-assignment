# 제출 점검표 — 과제 요구사항과 근거의 대응

과제의 모든 요구 항목을 한 줄씩 옮기고, **어느 파일의 무엇이 그 근거인지**를 붙였습니다.
채점자가 이 표만 따라가면 전부 확인할 수 있게 하는 것이 목적입니다.

| 표기 | 뜻 |
|---|---|
| ✅ | 저장소 안에서 확인 가능 |
| 🖐 | 사람이 채워야 함 (스크린샷 등) |

---

## 2절 — 최종 결과물 (필수 5종)

### ① 배포된 웹 서비스 (Vercel URL)

| 요구 | 상태 | 근거 |
|---|---|---|
| 배포 URL 이 있다 | ✅ | https://axisolve-writing.vercel.app — `README.md` 최상단 |
| 최소 3개 이상의 페이지/섹션, 메뉴 이동 가능 | ✅ | **4개** — `#home` `#generator` `#pricing` `#about`. 해시 라우팅은 [nav.js](../nav.js), 상단 링크는 `index.html` 의 `data-nav` |
| 반응형, 모바일에서 정상 표시 | ✅ | `<meta name="viewport">` + 중단점 — `styles.css` 820/720/640/520px, `landing.css` 1000/980/900/720/620/560px |
| AI API 연동 기능 1개 이상 (입력→출력) | ✅ | 에세이 생성 — 입력 `#generator`, 처리 [api/generate.py](../api/generate.py), 출력 결과 패널 |

### ② GitHub 저장소

| 요구 | 상태 | 근거 |
|---|---|---|
| 프로젝트 코드가 업로드되어 있다 | ✅ | 이 저장소 |
| 프론트와 백엔드 구조가 구분되어 있다 | ✅ | 프론트 `index.html` `*.css` `*.js` (루트) / 백엔드 `api/` |
| 커밋 이력을 남긴다 | ✅ | 11개 커밋. `git log --oneline` |

### ③ README.md

| 요구 | 상태 | 근거 |
|---|---|---|
| 서비스 소개 | ✅ | `README.md` 서두 |
| 기술 스택 | ✅ | `README.md` "기술 스택" |
| 실행 방법 | ✅ | `README.md` "로컬에서 실행하기" — `py dev_server.py` |
| 배포 방법 | ✅ | `README.md` "배포 방법 (Vercel)" 5단계 |
| 배포 URL | ✅ | `README.md` 최상단 |
| 환경 변수(키) 설정 방법 | ✅ | `README.md` "API 키 보안" + [.env.example](../.env.example) |

### ④ 서비스 기획서 → [service-plan.md](service-plan.md)

| 요구 | 상태 | 근거 |
|---|---|---|
| 서비스 목적 | ✅ | 1절 · 2절 문제 정의 |
| 타겟 사용자 | ✅ | 1절 (1차: 학원 강사 / 2차: 초3-6 학습자) |
| 페이지 구성 | ✅ | 4절 (섹션 4개 + 법적 고지 3개 + 네비게이션 방식) |
| 핵심 기능 | ✅ | 3절 "기준 통과까지 생성" · 5절 |
| AI 기능의 입력 기준 | ✅ | 5.2 |
| AI 기능의 출력 기준 | ✅ | 5.3 |
| AI 기능의 실패 처리 기준 | ✅ | 5.4 (빈 입력 / API 오류 / 지연·타임아웃 **3종 모두**) |

### ⑤ 증빙 자료 → [evidence/](evidence/)

| 요구 | 상태 | 근거 |
|---|---|---|
| 데스크톱 스크린샷 | 🖐 | `evidence/screenshots/01~04` |
| 모바일 스크린샷 | 🖐 | `evidence/screenshots/05~07` |
| AI 기능 동작 장면 | 🖐 | `evidence/screenshots/08~10` |
| AI 코딩 도구 사용 과정 | ✅ / 🖐 | 커밋 트레일러 11건은 [ai-tool-log.md](evidence/ai-tool-log.md) 로 검증 가능. 대화 화면 `14~16` 은 직접 |

---

## 4절 — 기능 요구 사항

| # | 요구 | 상태 | 근거 |
|---|---|---|---|
| 4-1 | 아이디어 정의 | ✅ | [service-plan.md](service-plan.md) 1절 |
| 4-1 | 목적·타겟 정의 | ✅ | 같은 문서 1·2절 |
| 4-1 | 섹션 3개 이상 설계 + 메뉴 이동 방식 | ✅ | 같은 문서 4절 |
| 4-1 | AI 기능 정의 (입력/출력/가치) | ✅ | 같은 문서 5.2 / 5.3 / 5.5 |
| 4-2 | 폴더 구조 구성 | ✅ | `README.md` "파일 구성" |
| 4-2 | `requirements.txt` | ✅ | [requirements.txt](../requirements.txt) — `openai`, `reportlab` |
| 4-2 | GitHub 저장소 + 커밋 이력 | ✅ | 11개 커밋 |
| 4-3 | 메인 및 추가 섹션 구현 | ✅ | `index.html` 467줄 |
| 4-3 | 섹션 간 네비게이션 | ✅ | [nav.js](../nav.js) |
| 4-3 | 레이아웃·스타일 | ✅ | `styles.css` `landing.css` `legal.css` |
| 4-4 | 모바일/태블릿/데스크톱 대응 | ✅ | 중단점 위 표 참조 |
| 4-4 | 최소 2가지 화면 크기에서 확인 | 🖐 | [test-cases.md](test-cases.md) F절 · 스크린샷 01~07 |
| 4-5 | 사용자 입력 UI | ✅ | 주제 선택 사이드바 + 직접 입력 폼 + 아이디어 textarea |
| 4-5 | AI 결과를 화면에 표시 | ✅ | 결과 패널 4블록 |
| 4-5 | 실패 안내 **1개 이상** | ✅ | **3종 모두** 구현 — [service-plan.md](service-plan.md) 5.4 |
| 4-6 | `api/` 에 Python 엔드포인트 | ✅ | `generate` `topics` `pdf` `me` `redeem` **5개** |
| 4-6 | AI API 호출 후 결과 반환 | ✅ | [api/generate.py](../api/generate.py) |
| 4-6 | `requirements.txt` 에 패키지 정의 | ✅ | 위와 같음 |
| 4-6 | 프론트에서 `fetch('/api/...')` 호출 | ✅ | `app.js` — `/api/generate` `/api/topics` `/api/pdf` `/api/redeem` |
| 4-7 | GitHub–Vercel 연동 배포 | 🖐 | `README.md` "배포 방법" |
| 4-7 | 배포 URL 에서 전체 기능 동작 확인 | 🖐 | 스크린샷 |
| 4-8 | README 정리 | ✅ | 위 ③ |
| 4-8 | 스크린샷·AI 도구 증빙 준비 | 🖐 | [evidence/](evidence/) |
| 4-8 | 기획서를 제출 패키지에 포함 | ✅ | [service-plan.md](service-plan.md) |

## 5절 — 보너스 과제 → [bonus.md](bonus.md)

| 갈래 | 상태 |
|---|---|
| 운영 자동화 / 데이터 저장 고도화 | ✅ Supabase 크레딧 원장·세션·충전 코드 |
| UX — 마이크로 인터랙션 | ✅ 6종 |
| UX — 다크 모드 | 🔶 화면별 고정, 토글 없음 |
| UX — 방문자 분석 | ❌ 미구현 (이유를 문서에 적음) |

## 6절 — 개발 환경

| 요구 | 상태 | 확인 방법 |
|---|---|---|
| 프론트는 순수 HTML/CSS/JS, **프레임워크 금지** | ✅ | `package.json` 이 없습니다. `<script src>` 는 전부 같은 폴더의 자체 파일이고 CDN 이 없습니다 |
| 백엔드는 Vercel Python Serverless (`api/`) | ✅ | `api/*.py` 5개 |
| AI 기능 1개 이상 | ✅ | 에세이 생성 |

## 7절 — 제약 사항

| 요구 | 상태 | 근거 |
|---|---|---|
| API 키를 환경변수로 관리, 코드·README·스크린샷에 노출 금지 | ✅ | `git grep "sk-"` → `.env.example` 자리표시자와 README 설명뿐. [test-cases.md](test-cases.md) E-5 |
| 과금·쿼터를 인지하고 호출 빈도·실패를 고려 | ✅ | `api/_guard.py` 3중 상한, 자동 재시도는 1크레딧, 실패 시 자동 환불 |
| 키 유출 시 폐기·재발급·이력 정리 절차 | ✅ | [learning-notes.md](learning-notes.md) 4절에 순서를 적음 |
| 제출 패키지 5종 누락 없음 | 🖐 | 이 문서 위쪽 |
| 템플릿을 그대로 복제하지 않음 | ✅ | 예시(멍냥케어)와 무관한 자체 주제. 165개 기출 DB·학년별 루브릭·워크북 PDF 는 이 서비스 고유 |
| 배포 URL 에서 재현 가능 | 🖐 | 동료 접속 테스트 |

---

## 제출 직전 확인

- [x] `README.md` 최상단에 실제 배포 URL 을 넣었다
- [ ] 배포 URL 을 시크릿 창에서 열어 4개 섹션이 다 동작한다
- [ ] 휴대폰으로 열어 가로 스크롤이 없다
- [ ] AI 생성을 한 번 돌려 결과가 나온다
- [ ] `docs/evidence/screenshots/` 에 01~10 이 있다
- [ ] Vercel 환경변수에 `OPENAI_API_KEY` 와 `ALLOWED_ORIGINS` 가 들어 있다
- [ ] OpenAI 계정에 Budget limit 을 걸어 두었다
