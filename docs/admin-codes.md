# 운영 매뉴얼 — 충전 코드 발급

사업자등록 전까지 쓰는 수동 충전 절차입니다. PG 결제를 붙일 수 없는 동안
입금을 직접 확인하고 코드를 발급합니다.

작업 위치: **Supabase 대시보드 > SQL Editor**

---

## 1. 코드 발급

```sql
-- 라이트(30회) 코드 5장 발급
select * from create_codes(5, 30, '라이트 30회');
```

결과로 코드가 표시됩니다. 이 화면을 벗어나면 다시 볼 수 있지만(3번 참조),
발급 즉시 복사해 두는 편이 편합니다.

```
code           credits
AX-K7MP-R4XQ   30
AX-B2WD-HTNY   30
...
```

### 상품별 발급 예시

```sql
select * from create_codes(1, 30,  '라이트 30회');      -- 4,900원
select * from create_codes(1, 100, '스탠다드 100회');   -- 12,900원
select * from create_codes(1, 500, '프로 500회');       -- 39,000원
```

### 옵션

```sql
-- 30일 후 만료되는 코드
select * from create_codes(1, 30, '라이트', 1, 30);

-- 여러 명이 함께 쓰는 코드 (예: 수업용 체험 코드 20명분)
select * from create_codes(1, 5, '3월 특강 체험', 20, 14);
--                            ↑ 1인당 5회  ↑ 20명까지  ↑ 14일 유효
```

인자 순서: `create_codes(장수, 크레딧, 메모, 최대사용인원, 유효일수)`

---

## 2. 입금 확인 → 코드 전달

1. 사용자가 화면의 `충전 문의하기` 로 연락
2. 입금 확인
3. 위 SQL로 코드 발급
4. 카카오톡 등으로 코드 전달
5. 사용자가 화면 우측 상단 잔액 배지 클릭 → 코드 입력 → 즉시 충전

> 코드는 `I` `O` `0` `1` 같은 헷갈리는 글자를 빼고 만듭니다.
> 전화로 불러줘도 오해가 없습니다. 입력할 때 대소문자·하이픈은 무시됩니다.

---

## 3. 발급 현황 확인

```sql
select * from code_status();
```

| 열 | 뜻 |
|---|---|
| `code` | 코드 |
| `credits` | 1인당 지급 크레딧 |
| `used` | `사용인원/최대인원` |
| `note` | 발급 시 적은 메모 |
| `expires_at` | 만료일 (비어 있으면 무기한) |

### 누가 썼는지 확인

```sql
select r.code, r.credits, r.created_at, u.email
  from redemptions r
  join auth.users u on u.id = r.user_id
 order by r.created_at desc
 limit 50;
```

---

## 4. 사용량·매출 확인

```sql
-- 최근 생성 이력
select created_at, kind, amount, balance_after, grade, topic_no
  from credit_ledger
 order by created_at desc
 limit 50;

-- 사용자별 잔액
select u.email, c.balance, c.updated_at
  from credits c join auth.users u on u.id = c.user_id
 order by c.updated_at desc;

-- 이번 달 총 생성 건수 (= 원가 추산의 기준)
select count(*) from credit_ledger
 where kind = 'consume' and created_at >= date_trunc('month', now());
```

1건당 평균 원가는 약 6원입니다([monetization-plan.md](monetization-plan.md) 4장).

---

## 5. 코드 취소 / 문제 대응

```sql
-- 아직 안 쓴 코드 폐기
delete from redeem_codes where code = 'AX-K7MP-R4XQ';

-- 특정 사용자에게 직접 크레딧 지급 (사과·보상 등)
select grant_credit(
  (select id from auth.users where email = 'someone@example.com'),
  10, '오류 보상'
);
```

---

## 6. 나중에 PG 결제를 붙일 때

사업자등록 후 토스페이먼츠·포트원을 연동하더라도 **지금 만든 구조를 버리지 않습니다.**

- 충전은 결국 `grant_credit()` 을 호출하는 일이고, PG 결제 승인 콜백에서
  같은 함수를 부르면 됩니다.
- `credit_ledger` 원장도 그대로 공유하므로 코드 충전과 카드 결제가 한 곳에 쌓입니다.
- 코드제는 그 뒤에도 남겨 두면 수업용 체험 코드, 이벤트 쿠폰으로 계속 쓸 수 있습니다.

추가로 필요한 것은 결제 준비/승인/웹훅 엔드포인트 3개와
이용약관·환불규정입니다([monetization-plan.md](monetization-plan.md) 9장 Phase 3~4).
