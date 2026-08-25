# Phase 2 설정 가이드 — Supabase + 카카오 로그인

코드는 모두 작성되어 있습니다. 아래 외부 설정을 마치고 환경변수 3개를 넣으면 켜집니다.
**설정 전까지는 로그인 계층이 자동으로 꺼진 채 Phase 1 상태로 정상 동작합니다.**

소요 시간: 약 30분

> ### 지금 꼭 해야 하나?
> 아니다. **이 설정은 미룰 수 있다.**
>
> Supabase 에 매달린 것은 ① 카카오 로그인 ② 크레딧 관리 ③ 충전 코드(= 결제 수단 전체)
> 세 가지다. 에세이 생성 자체는 Supabase 없이도 완전히 동작한다.
>
> 따라서 **설정하지 않고 배포하면 "무료 도구"로 공개**된다. 이 경우 프론트엔드가
> 자동으로 무료 공개 모드로 전환되어 요금제 탭과 결제 관련 안내를 숨긴다
> (`landing.js` 의 `applyFreeMode`). 화면이 사실과 어긋나지 않으므로 그대로 배포해도 된다.
>
> **단, 무료 공개 모드에서는 생성이 사실상 무제한**이 되므로
> `RATE_LIMIT_GLOBAL_DAILY` 를 100~150 으로 낮춰야 한다. 이것이 유일한 비용 방어선이다.
>
> 나중에 이 문서대로 환경변수 3개를 넣고 재배포하면 로그인·크레딧·결제 화면이
> 저절로 켜진다. 코드를 고칠 필요가 없다.

---

## 1단계 — Supabase 프로젝트 생성 (5분)

1. [supabase.com](https://supabase.com) → `Start your project` → **GitHub 계정으로 로그인**
2. `New project`
   - Name: `axisolve-writing-engine`
   - Database Password: **자동 생성 버튼을 누르고 어딘가에 보관** (나중에 DB 직접 접속할 때 필요)
   - Region: **Northeast Asia (Seoul)** — 반드시 서울로 선택. 응답 속도가 다릅니다.
   - Plan: **Free**
3. 생성까지 2분쯤 걸립니다.

---

## 2단계 — 테이블·함수 만들기 (2분)

1. 왼쪽 사이드바 **`SQL Editor`** → `New query`
2. 이 저장소의 **`supabase/schema.sql`** 내용을 통째로 복사해 붙여넣기
3. **`Run`** (Ctrl+Enter)
4. `Success. No rows returned` 가 나오면 정상입니다.
5. `New query` 를 한 번 더 열고 **`supabase/redeem.sql`** 도 같은 방식으로 실행합니다.
   (충전 코드제 — 사업자등록 전까지 쓰는 결제 대체 경로입니다.)

> 여러 번 실행해도 안전하게 작성했습니다. 나중에 스키마를 고칠 때도 그대로 다시 돌리면 됩니다.

확인: 왼쪽 `Table Editor` 에 아래 6개 테이블이 보이면 성공입니다.
`credits` · `credit_ledger` · `generation_sessions` · `anon_usage` · `redeem_codes` · `redemptions`

---

## 3단계 — 카카오 개발자 앱 등록 (10분)

### 3-1. 앱 만들기

1. [developers.kakao.com](https://developers.kakao.com) → 카카오 계정으로 로그인
2. `내 애플리케이션` → **`애플리케이션 추가하기`**
   - 앱 이름: `AXISOLVE Writing Engine`
   - 회사명: 학원명 또는 개인 이름
3. 생성된 앱 클릭

### 3-2. 키 확인

`앱 설정 > 앱 키` 에서 두 가지를 복사해 둡니다.

| 키 | 용도 |
|---|---|
| **REST API 키** | Supabase 에 넣을 Client ID |
| **Client Secret** | `제품 설정 > 카카오 로그인 > 보안` 에서 **코드 생성** 후 **활성화 상태 ON** |

> Client Secret은 기본이 비활성입니다. **반드시 ON으로 바꾸세요.** 끄면 Supabase 연동이 실패합니다.

### 3-3. 카카오 로그인 켜기

`제품 설정 > 카카오 로그인`

1. **활성화 설정: ON**
2. **Redirect URI 등록** — 아래 주소를 넣습니다. `<프로젝트ID>` 는 Supabase URL 의 앞부분입니다.

```
https://<프로젝트ID>.supabase.co/auth/v1/callback
```

예를 들어 Supabase URL이 `https://abcdefghijkl.supabase.co` 라면
`https://abcdefghijkl.supabase.co/auth/v1/callback` 입니다.

> 카카오는 **정확히 일치**하는 주소만 허용합니다. 오타 하나면 로그인이 실패합니다.

### 3-4. 동의 항목 설정

`제품 설정 > 카카오 로그인 > 동의항목`

| 항목 | 설정 | 이유 |
|---|---|---|
| 닉네임 | **필수 동의** | 화면에 이름 표시 |
| 프로필 사진 | 선택 동의 | 없어도 무방 |
| 카카오계정(이메일) | **선택 동의** | 결제·문의 대응용 |

> 이메일을 "필수 동의"로 걸면 심사가 필요합니다. **선택 동의로 두세요.**
> 이메일이 없어도 서비스는 정상 작동합니다(사용자 식별은 카카오 고유 ID로 합니다).

### 3-5. 플랫폼 등록

`앱 설정 > 플랫폼 > Web 플랫폼 등록` → 사이트 도메인에 배포 주소를 넣습니다.
아직 배포 전이면 `http://localhost:3000` 을 먼저 넣어 두면 됩니다.

---

## 4단계 — Supabase에 카카오 연결 (3분)

1. Supabase 대시보드 → **`Authentication` > `Sign In / Providers`**
2. 목록에서 **`Kakao`** 를 찾아 클릭
3. 입력:
   - **Kakao enabled**: ON
   - **Kakao Client ID**: 3-2에서 복사한 **REST API 키**
   - **Kakao Client Secret**: 3-2에서 생성한 **Client Secret**
4. `Save`

### URL 설정도 함께

`Authentication > URL Configuration`

| 항목 | 값 |
|---|---|
| Site URL | 배포 주소 (예: `https://your-app.vercel.app`) — 배포 전이면 `http://localhost:3000` |
| Redirect URLs | 위와 같은 주소를 추가. 배포 후 두 개 다 넣어 두면 편합니다. |

---

## 5단계 — 환경변수 넣기 (2분)

Supabase 대시보드 → `Project Settings` > `API` 에서 세 값을 복사합니다.

| 대시보드 표기 | 환경변수 이름 |
|---|---|
| Project URL | `SUPABASE_URL` |
| `anon` `public` | `SUPABASE_ANON_KEY` |
| `service_role` `secret` | `SUPABASE_SERVICE_ROLE_KEY` |

### 로컬 (`.env.local`)

```
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...
```

### 충전 안내 문구 (선택)

크레딧 부족 안내창에 문의처와 계좌를 띄우려면 두 개를 더 넣습니다. 비워 두면
"관리자에게 문의해 주십시오" 문구만 나옵니다.

```
PURCHASE_CONTACT=https://open.kakao.com/o/xxxxxxx
PURCHASE_BANK=국민은행 123456-78-901234 (예금주: 홍길동)
```

### 배포 (Vercel > Settings > Environment Variables)

같은 값들을 등록한 뒤 **Redeploy** 합니다.

> ⚠️ **`service_role` 키는 RLS를 우회하는 마스터 키입니다.**
> 절대 프론트엔드 코드나 GitHub에 넣지 마십시오. `.env.local` 은 `.gitignore` 처리되어 있습니다.

---

## 6단계 — 확인

```bash
py dev_server.py
```

브라우저에서 `http://localhost:3000` 접속 후:

| 확인 항목 | 기대 결과 |
|---|---|
| 우측 상단 | `무료 2회` 배지 + `카카오 로그인` 버튼 |
| 생성 2회 실행 | 정상 생성, 배지가 `무료 0회` 로 감소 |
| 3회차 생성 시도 | 카카오 로그인 모달 |
| 카카오 로그인 | 동의 화면 → 돌아오면 배지가 `3회` 로 변경 |
| 로그인 후 생성 | 배지가 `2회` 로 감소 |
| 재시도가 걸린 생성 | **크레딧은 1회만 차감** (4번 호출돼도) |
| 잔액 배지 클릭 | 충전 안내창 + 코드 입력칸 |

터미널에서도 확인할 수 있습니다.

```bash
curl http://localhost:3000/api/me
# auth_enabled 가 true 로 바뀌어 있어야 합니다.
```

---

## 문제가 생기면

| 증상 | 원인 |
|---|---|
| `auth_enabled: false` | 환경변수 3개 중 하나가 비었거나 서버를 재시작하지 않음 |
| 카카오 화면에서 `KOE006` | Redirect URI 불일치 — 3-3의 주소를 다시 확인 |
| 카카오 화면에서 `KOE101` | REST API 키가 틀림 (JavaScript 키를 넣은 경우가 많음) |
| 로그인 후 돌아왔는데 비회원 | Supabase `URL Configuration` 의 Redirect URLs 에 주소 미등록 |
| `계정 서버에 연결하지 못했습니다` | `service_role` 키 오류, 또는 2단계 SQL 미실행 |
