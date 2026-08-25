-- ============================================================================
-- AXISOLVE Writing Engine — Phase 2 스키마
-- Supabase 대시보드 > SQL Editor 에 붙여넣고 실행한다. 여러 번 실행해도 안전하다.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. 테이블
-- ---------------------------------------------------------------------------

-- 사용자별 크레딧 잔액
create table if not exists public.credits (
  user_id               uuid primary key references auth.users(id) on delete cascade,
  balance               integer not null default 0 check (balance >= 0),
  signup_bonus_granted  boolean not null default false,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now()
);

-- 크레딧 변동 원장. 환불·CS 대응의 근거가 되므로 삭제하지 않는다.
create table if not exists public.credit_ledger (
  id         bigserial primary key,
  user_id    uuid references auth.users(id) on delete set null,
  kind       text not null check (kind in ('consume', 'refund', 'grant', 'purchase')),
  amount     integer not null,          -- 양수. 방향은 kind 가 결정한다.
  balance_after integer,
  topic_no   integer,
  grade      text,
  note       text,
  created_at timestamptz not null default now()
);

create index if not exists credit_ledger_user_idx
  on public.credit_ledger (user_id, created_at desc);

-- 생성 세션. "생성 1회"의 단위이며, 자동 재시도(최대 4회)를 하나로 묶는다.
-- 이 테이블이 있어야 재시도가 크레딧을 중복 차감하지 않는다.
create table if not exists public.generation_sessions (
  gen_id     uuid primary key,
  user_id    uuid references auth.users(id) on delete cascade,
  ip_hash    text,
  attempts   integer not null default 1,
  created_at timestamptz not null default now()
);

create index if not exists generation_sessions_created_idx
  on public.generation_sessions (created_at);

-- 비회원 무료 사용량. IP 원문이 아니라 해시만 저장하며 하루 단위로 관리한다.
create table if not exists public.anon_usage (
  ip_hash    text not null,
  day        date not null default current_date,
  count      integer not null default 0,
  created_at timestamptz not null default now(),
  primary key (ip_hash, day)
);

-- ---------------------------------------------------------------------------
-- 2. RLS — 클라이언트의 직접 접근을 전면 차단한다.
--    이 테이블들은 오직 서버 함수(service_role 키)만 만진다.
--    service_role 은 RLS 를 우회하므로 정책을 따로 만들지 않는다.
-- ---------------------------------------------------------------------------

alter table public.credits       enable row level security;
alter table public.credit_ledger enable row level security;
alter table public.anon_usage    enable row level security;
alter table public.generation_sessions enable row level security;

-- ---------------------------------------------------------------------------
-- 3. 함수
--    전부 security definer. 잔액 변경은 단일 UPDATE 문 안에서 원자적으로 일어나
--    동시 요청으로 잔액보다 많이 쓰는 것이 불가능하다.
-- ---------------------------------------------------------------------------

-- 계정 초기화 + 가입 보너스 1회 지급. 이미 지급했으면 잔액만 돌려준다.
create or replace function public.ensure_account(p_user uuid, p_bonus integer)
returns table (balance integer, bonus_granted boolean)
language plpgsql security definer set search_path = public
as $$
declare
  v_row public.credits%rowtype;
  v_granted boolean := false;
begin
  insert into public.credits (user_id, balance, signup_bonus_granted)
  values (p_user, 0, false)
  on conflict (user_id) do nothing;

  select * into v_row from public.credits where user_id = p_user for update;

  if not v_row.signup_bonus_granted then
    update public.credits
       set balance = balance + p_bonus,
           signup_bonus_granted = true,
           updated_at = now()
     where user_id = p_user
    returning * into v_row;

    insert into public.credit_ledger (user_id, kind, amount, balance_after, note)
    values (p_user, 'grant', p_bonus, v_row.balance, '가입 보너스');

    v_granted := true;
  end if;

  return query select v_row.balance, v_granted;
end $$;


-- 크레딧 차감. 반환값:
--    >= 0  차감 후 잔액 (또는 재시도라 차감 없이 현재 잔액)
--      -1  잔액 부족
--      -2  이 생성 세션의 재시도 한도 초과
--
-- 같은 gen_id 로 다시 들어오면 자동 재시도로 간주해 차감하지 않는다.
-- 품질 보증(기준 미달 시 재생성)은 서비스 책임이므로 사용자에게 전가하지 않는다.
create or replace function public.consume_credit(
  p_user uuid, p_gen_id uuid, p_amount integer,
  p_topic_no integer, p_grade text, p_max_attempts integer
) returns integer
language plpgsql security definer set search_path = public
as $$
declare
  v_balance  integer;
  v_attempts integer;
begin
  -- 이미 존재하는 세션이면 재시도다. 원자적으로 시도 횟수만 올린다.
  update public.generation_sessions
     set attempts = attempts + 1
   where gen_id = p_gen_id and user_id = p_user
  returning attempts into v_attempts;

  if v_attempts is not null then
    if v_attempts > p_max_attempts then
      return -2;
    end if;
    select balance into v_balance from public.credits where user_id = p_user;
    return coalesce(v_balance, 0);
  end if;

  -- 새 생성이다. 잔액을 확인하고 차감한다.
  update public.credits
     set balance = balance - p_amount, updated_at = now()
   where user_id = p_user and balance >= p_amount
  returning balance into v_balance;

  if v_balance is null then
    return -1;                      -- 잔액 부족
  end if;

  insert into public.generation_sessions (gen_id, user_id) values (p_gen_id, p_user);

  insert into public.credit_ledger (user_id, kind, amount, balance_after, topic_no, grade)
  values (p_user, 'consume', p_amount, v_balance, p_topic_no, p_grade);

  return v_balance;
end $$;


-- 생성 실패 시 차감분 되돌리기.
create or replace function public.refund_credit(
  p_user uuid, p_amount integer, p_note text
) returns integer
language plpgsql security definer set search_path = public
as $$
declare v_balance integer;
begin
  update public.credits
     set balance = balance + p_amount, updated_at = now()
   where user_id = p_user
  returning balance into v_balance;

  if v_balance is null then
    return -1;
  end if;

  insert into public.credit_ledger (user_id, kind, amount, balance_after, note)
  values (p_user, 'refund', p_amount, v_balance, p_note);

  return v_balance;
end $$;


-- 결제/초대코드로 크레딧 지급. Phase 3 에서 사용한다.
create or replace function public.grant_credit(
  p_user uuid, p_amount integer, p_note text
) returns integer
language plpgsql security definer set search_path = public
as $$
declare v_balance integer;
begin
  insert into public.credits (user_id, balance) values (p_user, 0)
  on conflict (user_id) do nothing;

  update public.credits
     set balance = balance + p_amount, updated_at = now()
   where user_id = p_user
  returning balance into v_balance;

  insert into public.credit_ledger (user_id, kind, amount, balance_after, note)
  values (p_user, 'purchase', p_amount, v_balance, p_note);

  return v_balance;
end $$;


-- 비회원 사용량 1 증가. 반환값:
--    >= 1  현재 일일 사용 횟수 (또는 재시도라 증가 없이 현재값)
--      -1  IP 일일 한도 초과
--      -2  이 생성 세션의 재시도 한도 초과
create or replace function public.bump_anon(
  p_ip_hash text, p_gen_id uuid, p_limit integer, p_max_attempts integer
) returns integer
language plpgsql security definer set search_path = public
as $$
declare
  v_count    integer;
  v_attempts integer;
begin
  update public.generation_sessions
     set attempts = attempts + 1
   where gen_id = p_gen_id and ip_hash = p_ip_hash
  returning attempts into v_attempts;

  if v_attempts is not null then
    if v_attempts > p_max_attempts then
      return -2;
    end if;
    select count into v_count from public.anon_usage
     where ip_hash = p_ip_hash and day = current_date;
    return coalesce(v_count, 1);
  end if;

  insert into public.anon_usage (ip_hash, day, count)
  values (p_ip_hash, current_date, 1)
  on conflict (ip_hash, day) do update
     set count = public.anon_usage.count + 1
   where public.anon_usage.count < p_limit
  returning count into v_count;

  if v_count is null then
    return -1;                      -- 일일 한도 초과
  end if;

  insert into public.generation_sessions (gen_id, ip_hash) values (p_gen_id, p_ip_hash);
  return v_count;
end $$;


-- 비회원 사용량 되돌리기 (생성 실패 시).
create or replace function public.unbump_anon(p_ip_hash text)
returns void
language sql security definer set search_path = public
as $$
  update public.anon_usage set count = greatest(count - 1, 0)
   where ip_hash = p_ip_hash and day = current_date;
$$;


-- 오래된 비회원 기록 정리. Supabase 대시보드의 Cron 으로 하루 1회 돌린다.
create or replace function public.purge_anon_usage()
returns void
language sql security definer set search_path = public
as $$
  delete from public.anon_usage where day < current_date - interval '7 days';
  delete from public.generation_sessions where created_at < now() - interval '1 day';
$$;

-- ---------------------------------------------------------------------------
-- 4. 권한 — 익명/로그인 사용자에게는 어떤 실행 권한도 주지 않는다.
-- ---------------------------------------------------------------------------

revoke all on function public.ensure_account(uuid, integer)                from public, anon, authenticated;
revoke all on function public.consume_credit(uuid, uuid, integer, integer, text, integer) from public, anon, authenticated;
revoke all on function public.refund_credit(uuid, integer, text)           from public, anon, authenticated;
revoke all on function public.grant_credit(uuid, integer, text)            from public, anon, authenticated;
revoke all on function public.bump_anon(text, uuid, integer, integer)      from public, anon, authenticated;
revoke all on function public.unbump_anon(text)                            from public, anon, authenticated;
