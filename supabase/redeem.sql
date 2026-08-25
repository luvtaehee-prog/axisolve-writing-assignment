-- ============================================================================
-- AXISOLVE Writing Engine — 초대 코드제 (Phase 3 대체안)
--
-- 사업자등록 전이라 PG 연동이 불가능한 동안 쓰는 수동 충전 경로다.
-- 입금을 확인한 뒤 코드를 발급해 전달하면, 사용자가 화면에서 입력해 충전한다.
--
-- 나중에 PG를 붙일 때 이 테이블을 버릴 필요는 없다. 충전은 결국
-- grant_credit() 을 부르는 것이고, 원장(credit_ledger)도 그대로 공유한다.
-- schema.sql 을 먼저 실행한 뒤 이 파일을 실행한다.
-- ============================================================================

create table if not exists public.redeem_codes (
  code        text primary key,
  credits     integer not null check (credits > 0),
  max_uses    integer not null default 1 check (max_uses > 0),
  used_count  integer not null default 0,
  note        text,
  expires_at  timestamptz,
  created_at  timestamptz not null default now()
);

-- 같은 사용자가 같은 코드를 두 번 쓰지 못하게 막는다.
create table if not exists public.redemptions (
  id         bigserial primary key,
  code       text not null references public.redeem_codes(code) on delete cascade,
  user_id    uuid not null references auth.users(id) on delete cascade,
  credits    integer not null,
  created_at timestamptz not null default now(),
  unique (code, user_id)
);

alter table public.redeem_codes enable row level security;
alter table public.redemptions  enable row level security;


-- ---------------------------------------------------------------------------
-- 코드 사용. 반환 status:
--   ok / not_found / expired / exhausted / already_used
-- ---------------------------------------------------------------------------
create or replace function public.redeem_code(p_user uuid, p_code text)
returns table (status text, credits integer, balance integer)
language plpgsql security definer set search_path = public
as $$
declare
  v_code    public.redeem_codes%rowtype;
  v_norm    text := upper(regexp_replace(coalesce(p_code, ''), '[^A-Za-z0-9]', '', 'g'));
  v_balance integer;
begin
  -- 행 잠금으로 동시 사용 시 초과 지급을 막는다.
  select * into v_code from public.redeem_codes
   where upper(regexp_replace(code, '[^A-Za-z0-9]', '', 'g')) = v_norm
   for update;

  if v_code.code is null then
    return query select 'not_found'::text, 0, null::integer;  return;
  end if;

  if v_code.expires_at is not null and v_code.expires_at < now() then
    return query select 'expired'::text, 0, null::integer;    return;
  end if;

  if v_code.used_count >= v_code.max_uses then
    return query select 'exhausted'::text, 0, null::integer;  return;
  end if;

  if exists (select 1 from public.redemptions r
              where r.code = v_code.code and r.user_id = p_user) then
    return query select 'already_used'::text, 0, null::integer; return;
  end if;

  insert into public.redemptions (code, user_id, credits)
  values (v_code.code, p_user, v_code.credits);

  update public.redeem_codes set used_count = used_count + 1 where code = v_code.code;

  v_balance := public.grant_credit(p_user, v_code.credits, '코드 충전: ' || v_code.code);

  return query select 'ok'::text, v_code.credits, v_balance;
end $$;


-- ---------------------------------------------------------------------------
-- 코드 발급 (관리자용). Supabase SQL Editor 에서 직접 호출한다.
--
--   select * from create_codes(5, 30, '라이트 30회');
--
-- 헷갈리기 쉬운 글자(I, O, 0, 1)를 뺀 문자표를 쓴다. 전화로 불러주기 좋다.
-- ---------------------------------------------------------------------------
create or replace function public.create_codes(
  p_count integer, p_credits integer, p_note text default null,
  p_max_uses integer default 1, p_valid_days integer default null
) returns table (code text, credits integer)
language plpgsql security definer set search_path = public
as $$
declare
  v_alphabet text := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  v_code text;
  i integer;
  j integer;
begin
  for i in 1..p_count loop
    loop
      v_code := 'AX-';
      for j in 1..4 loop
        v_code := v_code || substr(v_alphabet, 1 + floor(random() * length(v_alphabet))::int, 1);
      end loop;
      v_code := v_code || '-';
      for j in 1..4 loop
        v_code := v_code || substr(v_alphabet, 1 + floor(random() * length(v_alphabet))::int, 1);
      end loop;
      exit when not exists (select 1 from public.redeem_codes c where c.code = v_code);
    end loop;

    insert into public.redeem_codes (code, credits, max_uses, note, expires_at)
    values (v_code, p_credits, p_max_uses, p_note,
            case when p_valid_days is null then null
                 else now() + (p_valid_days || ' days')::interval end);

    return query select v_code, p_credits;
  end loop;
end $$;


-- ---------------------------------------------------------------------------
-- 발급 현황 조회 (관리자용):  select * from code_status();
-- ---------------------------------------------------------------------------
create or replace function public.code_status()
returns table (code text, credits integer, used text, note text,
               expires_at timestamptz, created_at timestamptz)
language sql security definer set search_path = public
as $$
  select c.code, c.credits,
         c.used_count || '/' || c.max_uses as used,
         c.note, c.expires_at, c.created_at
    from public.redeem_codes c
   order by c.created_at desc;
$$;

revoke all on function public.redeem_code(uuid, text)                              from public, anon, authenticated;
revoke all on function public.create_codes(integer, integer, text, integer, integer) from public, anon, authenticated;
revoke all on function public.code_status()                                        from public, anon, authenticated;
