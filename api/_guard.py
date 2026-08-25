# -*- coding: utf-8 -*-
"""Phase 1 — 비용 방어 계층.

인증이 없는 상태에서 /api/generate 가 무제한 OpenAI 프록시로 악용되는 것을 막는다.
세 겹으로 구성한다.

  1. 출처 검증   — 허용된 도메인에서 온 요청만 통과 (ALLOWED_ORIGINS)
  2. IP 레이트리밋 — IP 해시 기준 시간당·일일 상한
  3. 전역 상한   — 서비스 전체의 하루 호출 수 상한 (최종 비용 방어선)

한계: 카운터는 함수 인스턴스의 메모리에 있다. Vercel이 인스턴스를 여러 개
띄우면 상한이 인스턴스 수만큼 곱해지고, 인스턴스가 재활용되면 초기화된다.
따라서 이 계층은 "정확한 과금"이 아니라 "비용 폭주 차단"이 목적이다.
정확한 횟수 관리는 Phase 2에서 DB로 옮긴다. (docs/monetization-plan.md 참조)
"""

import hashlib
import os
import threading
import time
from urllib.parse import urlparse

HOUR = 3600
DAY = 86400


def _int_env(name, default):
    try:
        return max(0, int(os.environ.get(name, "")))
    except ValueError:
        return default


# 0 이면 해당 검사를 끈다.
PER_IP_HOURLY = _int_env("RATE_LIMIT_IP_HOURLY", 12)
PER_IP_DAILY = _int_env("RATE_LIMIT_IP_DAILY", 30)
GLOBAL_DAILY = _int_env("RATE_LIMIT_GLOBAL_DAILY", 500)

# 콤마로 구분. 비어 있으면 출처 검사를 하지 않는다(로컬 개발).
ALLOWED_ORIGINS = [
    o.strip().lower().rstrip("/")
    for o in os.environ.get("ALLOWED_ORIGINS", "").split(",")
    if o.strip()
]

# IP 를 원문으로 남기지 않기 위한 솔트. 미설정 시 프로세스마다 임의값이라
# 재시작하면 카운터가 초기화된다 — 운영에서는 반드시 지정할 것.
_SALT = os.environ.get("IP_SALT") or hashlib.sha256(
    (os.environ.get("OPENAI_API_KEY", "") + "axisolve").encode()
).hexdigest()

_lock = threading.Lock()
_ip_hits = {}      # ip_hash -> [timestamp, ...]
_global_hits = []  # [timestamp, ...]
_MAX_TRACKED_IPS = 5000


class Rejected(Exception):
    """요청을 거절해야 할 때. status 와 사용자에게 보일 message 를 담는다."""

    def __init__(self, status, message, retry_after=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.retry_after = retry_after


def client_ip(headers):
    """프록시 뒤에 있으므로 X-Forwarded-For 의 첫 항목이 실제 클라이언트다."""
    xff = headers.get("X-Forwarded-For") or ""
    if xff:
        return xff.split(",")[0].strip()
    return (headers.get("X-Real-IP") or "unknown").strip()


def ip_hash(headers):
    return hashlib.sha256((_SALT + client_ip(headers)).encode()).hexdigest()[:32]


def _check_origin(headers):
    if not ALLOWED_ORIGINS:
        return
    origin = (headers.get("Origin") or "").strip().lower().rstrip("/")
    if not origin:
        # 일부 브라우저는 same-origin POST 에 Origin 을 안 붙인다. Referer 로 대체.
        referer = (headers.get("Referer") or "").strip()
        if referer:
            p = urlparse(referer)
            origin = f"{p.scheme}://{p.netloc}".lower()
    if origin not in ALLOWED_ORIGINS:
        raise Rejected(403, "이 도메인에서는 사용할 수 없습니다.")


def _prune(seq, window, now):
    cutoff = now - window
    return [t for t in seq if t > cutoff]


def check(headers):
    """통과하면 None, 막아야 하면 Rejected 를 던진다. 통과 시 호출을 1건 기록한다."""
    _check_origin(headers)

    now = time.time()
    key = ip_hash(headers)

    with _lock:
        global _global_hits
        _global_hits = _prune(_global_hits, DAY, now)
        if GLOBAL_DAILY and len(_global_hits) >= GLOBAL_DAILY:
            raise Rejected(
                503,
                "오늘 제공 가능한 무료 생성 횟수를 모두 소진했습니다. 내일 다시 이용해 주십시오.",
                retry_after=HOUR,
            )

        hits = _prune(_ip_hits.get(key, []), DAY, now)

        if PER_IP_DAILY and len(hits) >= PER_IP_DAILY:
            _ip_hits[key] = hits
            raise Rejected(
                429,
                f"하루 이용 한도({PER_IP_DAILY}회)를 초과했습니다. 내일 다시 이용해 주십시오.",
                retry_after=int(hits[0] + DAY - now) + 1,
            )

        recent = _prune(hits, HOUR, now)
        if PER_IP_HOURLY and len(recent) >= PER_IP_HOURLY:
            _ip_hits[key] = hits
            raise Rejected(
                429,
                f"짧은 시간에 요청이 너무 많습니다. 시간당 {PER_IP_HOURLY}회까지 이용할 수 있습니다.",
                retry_after=int(recent[0] + HOUR - now) + 1,
            )

        # 딕셔너리가 무한정 커지지 않도록, 가득 차면 만료된 항목부터 정리한다.
        if key not in _ip_hits and len(_ip_hits) >= _MAX_TRACKED_IPS:
            for k in [k for k, v in _ip_hits.items() if not _prune(v, DAY, now)]:
                del _ip_hits[k]
            if len(_ip_hits) >= _MAX_TRACKED_IPS:
                del _ip_hits[min(_ip_hits, key=lambda k: _ip_hits[k][-1])]

        hits.append(now)
        _ip_hits[key] = hits
        _global_hits.append(now)


def refund(headers):
    """OpenAI 호출이 실패했을 때 방금 기록한 1건을 되돌린다."""
    key = ip_hash(headers)
    with _lock:
        if _ip_hits.get(key):
            _ip_hits[key].pop()
        if _global_hits:
            _global_hits.pop()


def snapshot():
    """운영 확인용 현재 상태."""
    now = time.time()
    with _lock:
        return {
            "global_today": len(_prune(_global_hits, DAY, now)),
            "global_limit": GLOBAL_DAILY,
            "tracked_ips": len(_ip_hits),
            "per_ip_hourly": PER_IP_HOURLY,
            "per_ip_daily": PER_IP_DAILY,
            "origin_check": bool(ALLOWED_ORIGINS),
        }
