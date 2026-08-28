# 배포 절차 — 이 저장소로 새 Vercel 프로젝트 만들기

기존 배포본(`axisolve-writing.vercel.app`)은 저장소 `luvtaehee-prog/writing` 에 물려 있고,
**이번에 넣은 지연·타임아웃 처리가 들어 있지 않습니다.**
과제 제출용 주소는 이 저장소로 **새 프로젝트**를 만들어 얻습니다.

소요 시간 약 10분. 순서가 중요합니다 — `ALLOWED_ORIGINS` 는 **주소를 알아야** 넣을 수 있으므로
1차 배포를 먼저 하고 환경변수를 채운 뒤 재배포합니다.

---

## 1단계 — 프로젝트 만들기

1. [vercel.com/new](https://vercel.com/new) 접속
2. **Import Git Repository** 에서 `luvtaehee-prog/axisolve-writing-assignment` 선택
   - 목록에 없으면 **Adjust GitHub App Permissions** 로 이 저장소에 접근 권한을 줍니다
3. 설정은 이렇게 둡니다

   | 항목 | 값 |
   |---|---|
   | Framework Preset | **Other** |
   | Root Directory | `./` (그대로) |
   | Build Command | **비움** |
   | Output Directory | **비움** |
   | Install Command | **비움** |

   `requirements.txt` 가 있으므로 Vercel 이 `api/` 의 Python 함수를 알아서 잡습니다.

## 2단계 — 필수 환경변수 하나만 먼저

**Environment Variables** 에 이것만 넣고 배포합니다.

| 이름 | 값 |
|---|---|
| `OPENAI_API_KEY` | `sk-` 로 시작하는 키 ([platform.openai.com/api-keys](https://platform.openai.com/api-keys)) |

**Deploy** 를 누릅니다.

> 기존 프로젝트와 **같은 키를 씁니다.** 배포가 둘이 되므로 과금 창구도 둘입니다.
> OpenAI 대시보드에서 **Budget limit** 을 반드시 걸어 두십시오.
> 이 서비스는 생성 한 번이 최대 4회 호출이 될 수 있습니다.

### 빌드가 이 오류로 실패하면

```
Build Failed
No python entrypoint found in default locations, but found potential entrypoints:
api/generate.py (variable: handler) api/me.py (variable: handler) ...
Add this to your pyproject.toml: [tool.vercel] entrypoint = "api.generate:handler"
```

Vercel 이 루트의 `requirements.txt` 를 보고 이 저장소를 **"파이썬 앱 하나"** 로 잡은 것입니다.
이 프로젝트는 파이썬 앱이 아니라 **정적 파일 + `api/` 서버리스 함수 5개**이므로
진입점이 없는 것이 맞습니다.

**안내대로 `pyproject.toml` 에 `entrypoint` 를 넣지 마십시오.**
그러면 함수 5개가 앱 하나로 뭉개져 `/api/topics` 도 `/api/pdf` 도 사라집니다.

고치는 법:

1. `vercel.json` 에 `"framework": null` 이 들어 있는지 확인합니다 (이 저장소에는 있습니다)
2. 그래도 같은 오류가 나면 대시보드가 이깁니다 —
   **Settings > Build and Deployment > Framework Settings > Framework Preset** 을
   **Other** 로 바꾸고 **Save**
3. Build Command · Output Directory · Install Command 의 Override 토글이 켜져 있으면 모두 끕니다
4. **Deployments > 맨 위 > ⋯ > Redeploy**

## 3단계 — 주소 확인

배포가 끝나면 주소가 나옵니다. 저장소 이름을 따르므로 보통 이렇게 됩니다.

```
https://axisolve-writing-assignment.vercel.app
```

**Settings > Domains** 에서 실제 주소를 확인하십시오. 이름이 겹치면 뒤에 문자가 붙습니다.

## 4단계 — 나머지 환경변수를 넣고 재배포

**Settings > Environment Variables** 에서 추가합니다.

| 이름 | 값 | 없으면 |
|---|---|---|
| `ALLOWED_ORIGINS` | 3단계에서 확인한 주소 (끝에 `/` 없이) | **누구나 외부에서 호출할 수 있습니다** |
| `IP_SALT` | 아무 긴 임의 문자열 | 재시작마다 호출 카운터가 초기화됩니다 |
| `RATE_LIMIT_GLOBAL_DAILY` | `150` 권장 | 기본 500 — 최악의 경우 월 21만원 |

선택 항목은 [.env.example](../.env.example) 에 전부 주석으로 적혀 있습니다.

그다음 **Deployments > 맨 위 배포 > ⋯ > Redeploy**.
**환경변수는 재배포 시점에 함수로 전달됩니다.** 값만 바꾸고 재배포하지 않으면 옛 값이 그대로입니다.

## 5단계 — 동작 확인

`$URL` 을 3단계 주소로 바꿔 그대로 붙여 넣으십시오.

```bash
URL=https://axisolve-writing-assignment.vercel.app

curl -s -o /dev/null -w "site           %{http_code}\n" $URL/
curl -s -o /dev/null -w "topics(무Origin) %{http_code}\n" $URL/api/topics
curl -s -o /dev/null -w "topics(정상)     %{http_code}\n" -H "Origin: $URL" $URL/api/topics
curl -s -o /dev/null -w "topics(타Origin) %{http_code}\n" -H "Origin: https://evil.example" $URL/api/topics
curl -s -o /dev/null -w "topics.json     %{http_code}\n" $URL/topics.json
curl -s -o /dev/null -w "docs 유출        %{http_code}\n" $URL/docs/unit-economics.md
curl -s -o /dev/null -w "내부 모듈        %{http_code}\n" $URL/api/_guard.py
```

기대값:

```
site            200
topics(무Origin) 403     ← ALLOWED_ORIGINS 가 걸렸다는 뜻. 403 이 정상입니다
topics(정상)     200
topics(타Origin) 403
topics.json     404
docs 유출        404
내부 모듈        404
```

`topics(무Origin)` 이 **200** 이면 `ALLOWED_ORIGINS` 가 안 들어갔거나 재배포를 안 한 것입니다.

브라우저에서도 확인합니다.

- 섹션 4개(`#home` `#generator` `#pricing` `#about`)가 상단 링크로 이동되는가
- 개발자도구 기기 모드 390×844 에서 가로 스크롤이 없는가
- 주제를 고르고 생성이 실제로 되는가
- 개발자도구 Network 를 `Slow 3G` 로 두고 생성 → 20초 뒤 지연 안내가 뜨는가
  (이 항목이 **기존 배포본에는 없던 것**입니다)

## 6단계 — 문서에 주소 넣기

`README.md` 3행의 `<!-- DEPLOY_URL -->` 자리에 주소를 넣습니다.
[submission-checklist.md](submission-checklist.md) 의 배포 URL 칸도 함께 채웁니다.
[test-cases.md](test-cases.md) 의 E2 표는 5단계 결과로 다시 채웁니다.

## 기존 배포본은 어떻게 하나

`axisolve-writing.vercel.app` 은 그대로 살아 있고 저장소 `luvtaehee-prog/writing` 에 물려 있습니다.

| 선택 | 결과 |
|---|---|
| 그대로 둔다 | 옛 코드가 계속 서비스됩니다. 같은 키를 쓰므로 과금 창구가 둘입니다 |
| 나중에 새 코드로 맞춘다 | 기존 프로젝트의 Git 연결을 이 저장소로 바꾸면 주소를 유지한 채 최신 코드가 갑니다 |
| 정리한다 | Vercel 에서 프로젝트를 삭제하면 주소가 사라집니다 |

**과제 제출에는 새 주소를 씁니다.** 기존 주소를 적으면 문서에 있는 지연·타임아웃 안내가
실제로는 동작하지 않아 어긋납니다.
