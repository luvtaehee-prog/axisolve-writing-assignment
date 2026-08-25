/* AXISOLVE Writing Engine — 카카오 로그인 · 크레딧 상태 관리
 *
 * Supabase Auth 를 라이브러리 없이 REST 로 직접 다룬다. 이 프로젝트는
 * 빌드 도구를 쓰지 않으므로 CDN 의존성을 새로 만들지 않는 편이 낫다.
 *
 * 흐름
 *   1. 로그인 → Supabase authorize 엔드포인트로 리다이렉트 → 카카오 동의
 *   2. 돌아올 때 URL 조각(#access_token=...)에 토큰이 실려 온다
 *   3. 토큰을 localStorage 에 보관하고 URL 을 정리한다
 *   4. 만료 전에 refresh_token 으로 갱신한다
 *
 * 전역: window.AXAuth
 */
(function () {
  "use strict";

  var TOKEN_KEY = "axisolve_session";
  var FREE_KEY = "axisolve_free_used";
  var listeners = [];

  var state = {
    ready: false,
    authEnabled: false,
    loggedIn: false,
    credits: 0,
    name: null,
    avatar: null,
    freeAllowance: 2,
    signupBonus: 3,
    config: null,
    error: null
  };

  // ---------- 세션 보관 ----------
  function readSession() {
    try {
      var raw = localStorage.getItem(TOKEN_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) { return null; }
  }
  function writeSession(s) {
    try {
      if (s) localStorage.setItem(TOKEN_KEY, JSON.stringify(s));
      else localStorage.removeItem(TOKEN_KEY);
    } catch (e) { /* 시크릿 모드 등에서 저장 실패 — 세션만 유지된다 */ }
  }

  // ---------- 비회원 무료 사용 횟수 (UX 표시용) ----------
  // 서버가 IP 기준으로 별도 검증하므로 이 값은 안내에만 쓴다.
  function freeUsed() {
    var n = parseInt(localStorage.getItem(FREE_KEY) || "0", 10);
    return isNaN(n) ? 0 : n;
  }
  function markFreeUsed() {
    try { localStorage.setItem(FREE_KEY, String(freeUsed() + 1)); } catch (e) {}
  }
  function freeRemaining() {
    return Math.max(0, state.freeAllowance - freeUsed());
  }

  // ---------- OAuth 콜백 처리 ----------
  function captureCallback() {
    if (!location.hash || location.hash.indexOf("access_token=") === -1) return false;
    var p = new URLSearchParams(location.hash.replace(/^#/, ""));
    var access = p.get("access_token");
    if (!access) return false;

    writeSession({
      access_token: access,
      refresh_token: p.get("refresh_token"),
      expires_at: Date.now() + (parseInt(p.get("expires_in") || "3600", 10) * 1000)
    });
    // 주소창에서 토큰을 지운다. 원래 보던 섹션으로 돌려보낸다.
    history.replaceState(null, "", location.pathname + location.search + "#generator");
    return true;
  }

  // ---------- 토큰 갱신 ----------
  async function refreshIfNeeded() {
    var s = readSession();
    if (!s || !s.refresh_token) return s;
    if (s.expires_at && s.expires_at - Date.now() > 60000) return s;   // 1분 이상 남음

    var cfg = state.config;
    if (!cfg || !cfg.supabase_url) return s;
    try {
      var res = await fetch(cfg.supabase_url + "/auth/v1/token?grant_type=refresh_token", {
        method: "POST",
        headers: { "Content-Type": "application/json", apikey: cfg.anon_key },
        body: JSON.stringify({ refresh_token: s.refresh_token })
      });
      if (!res.ok) { writeSession(null); return null; }
      var d = await res.json();
      var next = {
        access_token: d.access_token,
        refresh_token: d.refresh_token || s.refresh_token,
        expires_at: Date.now() + ((d.expires_in || 3600) * 1000)
      };
      writeSession(next);
      return next;
    } catch (e) {
      return s;   // 네트워크 문제면 기존 토큰으로 시도한다
    }
  }

  async function token() {
    var s = await refreshIfNeeded();
    return s ? s.access_token : null;
  }

  // ---------- 상태 동기화 ----------
  async function refresh() {
    var headers = {};
    var t = await token();
    if (t) headers.Authorization = "Bearer " + t;

    try {
      var res = await fetch("/api/me", { headers: headers, cache: "no-store" });
      var d = await res.json();

      state.config = d.config || state.config;
      if (d.config) {
        state.authEnabled = !!d.config.auth_enabled;
        state.freeAllowance = d.config.free_anon_uses != null ? d.config.free_anon_uses : 2;
        state.signupBonus = d.config.signup_bonus != null ? d.config.signup_bonus : 3;
      }
      state.loggedIn = !!d.logged_in;
      state.credits = d.credits || 0;
      state.name = d.name || null;
      state.avatar = d.avatar || null;
      state.error = d.error || null;

      // 서버가 토큰을 거부했다면 죽은 세션이므로 지운다.
      if (t && !d.logged_in && !d.error) writeSession(null);
    } catch (e) {
      state.error = "계정 상태를 확인하지 못했습니다.";
    }
    state.ready = true;
    emit();
    return state;
  }

  // ---------- 로그인 / 로그아웃 ----------
  function login() {
    var cfg = state.config;
    if (!cfg || !cfg.supabase_url) {
      alert("로그인 설정이 아직 완료되지 않았습니다.");
      return;
    }
    var back = location.origin + location.pathname;
    location.href = cfg.supabase_url + "/auth/v1/authorize?provider=kakao&redirect_to="
      + encodeURIComponent(back);
  }

  async function logout() {
    var s = readSession();
    var cfg = state.config;
    if (s && cfg && cfg.supabase_url) {
      try {
        await fetch(cfg.supabase_url + "/auth/v1/logout", {
          method: "POST",
          headers: { apikey: cfg.anon_key, Authorization: "Bearer " + s.access_token }
        });
      } catch (e) { /* 서버 정리 실패해도 로컬 세션은 지운다 */ }
    }
    writeSession(null);
    await refresh();
  }

  // ---------- 구독 ----------
  function emit() { listeners.forEach(function (fn) { try { fn(state); } catch (e) {} }); }
  function onChange(fn) { listeners.push(fn); if (state.ready) fn(state); }

  function setCredits(n) {
    if (typeof n === "number") { state.credits = n; emit(); }
  }

  window.AXAuth = {
    state: state,
    token: token,
    login: login,
    logout: logout,
    refresh: refresh,
    onChange: onChange,
    setCredits: setCredits,
    markFreeUsed: markFreeUsed,
    freeUsed: freeUsed,
    freeRemaining: freeRemaining
  };

  captureCallback();
  refresh();
})();
