# -*- coding: utf-8 -*-
"""Supabase 연동 — 토큰 검증과 크레딧 조작.

새 의존성을 만들지 않기 위해 표준 라이브러리(urllib)만 쓴다.
서버는 service_role 키로 PostgREST 의 RPC 만 호출하며, 테이블을 직접
읽고 쓰지 않는다. 잔액 변경 로직은 전부 DB 함수 안에 있다(supabase/schema.sql).

필요한 환경변수
  SUPABASE_URL              https://xxxx.supabase.co
  SUPABASE_ANON_KEY         토큰 검증용 (공개되어도 되는 키)
  SUPABASE_SERVICE_ROLE_KEY RPC 호출용 (절대 브라우저에 노출 금지)
"""

import json
import os
import urllib.error
import urllib.request

SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
ANON_KEY = os.environ.get("SUPABASE_ANON_KEY") or ""
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or ""

SIGNUP_BONUS = int(os.environ.get("SIGNUP_BONUS_CREDITS", "3"))
FREE_ANON_USES = int(os.environ.get("FREE_ANON_USES", "2"))
# 공용 IP(학원·학교)에서 여러 명이 체험할 수 있도록 IP 기준은 넉넉하게 둔다.
ANON_IP_DAILY = int(os.environ.get("ANON_IP_DAILY", "10"))

# 결제 준비 전까지 안내에 쓰는 문구. 비워 두면 화면에 표시하지 않는다.
PURCHASE_CONTACT = os.environ.get("PURCHASE_CONTACT", "")
PURCHASE_BANK = os.environ.get("PURCHASE_BANK", "")

TIMEOUT = 10


class SupabaseError(Exception):
    pass


def configured():
    return bool(SUPABASE_URL and ANON_KEY and SERVICE_KEY)


def _request(path, method="POST", body=None, headers=None):
    url = f"{SUPABASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw.strip() else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(raw)
        except ValueError:
            return exc.code, {"message": raw[:300]}
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SupabaseError(f"Supabase 연결 실패: {exc}") from exc


def _rpc(fn, params):
    status, body = _request(
        f"/rest/v1/rpc/{fn}",
        body=params,
        headers={"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}"},
    )
    if status >= 400:
        msg = (body or {}).get("message") if isinstance(body, dict) else str(body)
        raise SupabaseError(f"{fn} 실패 (HTTP {status}): {msg}")
    return body


# ---------------------------------------------------------------------------
# 인증
# ---------------------------------------------------------------------------

def verify_token(auth_header):
    """Authorization 헤더의 액세스 토큰을 검증하고 사용자 정보를 돌려준다.

    JWT 를 직접 파싱하지 않고 Supabase 에 물어본다. 서명 알고리즘이나 키 교체
    방식이 바뀌어도 영향을 받지 않고, 로그아웃·차단된 토큰도 즉시 걸러진다.
    유효하지 않으면 None.
    """
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header[7:].strip()
    if not token:
        return None

    status, body = _request(
        "/auth/v1/user",
        method="GET",
        headers={"apikey": ANON_KEY, "Authorization": f"Bearer {token}"},
    )
    if status != 200 or not isinstance(body, dict) or not body.get("id"):
        return None
    meta = body.get("user_metadata") or {}
    return {
        "id": body["id"],
        "email": body.get("email"),
        "name": meta.get("name") or meta.get("full_name") or meta.get("nickname"),
        "avatar": meta.get("avatar_url") or meta.get("picture"),
    }


# ---------------------------------------------------------------------------
# 크레딧
# ---------------------------------------------------------------------------

def ensure_account(user_id):
    """계정 행을 만들고 가입 보너스를 1회 지급한다. (balance, bonus_granted) 반환."""
    rows = _rpc("ensure_account", {"p_user": user_id, "p_bonus": SIGNUP_BONUS})
    row = (rows or [{}])[0] if isinstance(rows, list) else (rows or {})
    return int(row.get("balance", 0)), bool(row.get("bonus_granted"))


def consume(user_id, gen_id, amount, topic_no=None, grade=None, max_attempts=4):
    """차감 결과. >=0 잔액 / -1 잔액 부족 / -2 재시도 한도 초과.

    같은 gen_id 로 다시 오면 자동 재시도로 보고 추가 차감하지 않는다.
    """
    return int(_rpc("consume_credit", {
        "p_user": user_id, "p_gen_id": gen_id, "p_amount": amount,
        "p_topic_no": topic_no, "p_grade": grade, "p_max_attempts": max_attempts,
    }))


def refund(user_id, amount, note="생성 실패 환불"):
    return int(_rpc("refund_credit", {
        "p_user": user_id, "p_amount": amount, "p_note": note,
    }))


def grant(user_id, amount, note):
    return int(_rpc("grant_credit", {
        "p_user": user_id, "p_amount": amount, "p_note": note,
    }))


# ---------------------------------------------------------------------------
# 비회원
# ---------------------------------------------------------------------------

def redeem(user_id, code):
    """충전 코드 사용. {"status": ..., "credits": n, "balance": n} 반환.

    status: ok / not_found / expired / exhausted / already_used
    """
    rows = _rpc("redeem_code", {"p_user": user_id, "p_code": code})
    row = (rows or [{}])[0] if isinstance(rows, list) else (rows or {})
    return {
        "status": row.get("status", "not_found"),
        "credits": int(row.get("credits") or 0),
        "balance": row.get("balance"),
    }


def bump_anon(ip_hash, gen_id, max_attempts=4):
    """비회원 사용 1건 기록. >=1 사용횟수 / -1 IP 일일한도 / -2 재시도 한도."""
    return int(_rpc("bump_anon", {
        "p_ip_hash": ip_hash, "p_gen_id": gen_id,
        "p_limit": ANON_IP_DAILY, "p_max_attempts": max_attempts,
    }))


def unbump_anon(ip_hash):
    try:
        _rpc("unbump_anon", {"p_ip_hash": ip_hash})
    except SupabaseError:
        pass  # 환불 실패가 생성 결과를 가려서는 안 된다.
