/* AXISOLVE Writing Engine — 랜딩 / 요금제 화면 동작
 *
 *  1. 자가진단 체크리스트 (체크 개수에 따른 진단 문구)
 *  2. 요금제의 "충전하기" → 문의처 안내
 *  3. 요금제 화면의 충전 코드 등록
 *
 * app.js(생성기)와는 분리한다. 두 스크립트는 window.AXAuth 만 공유한다.
 */
(function () {
  "use strict";

  // ---------------------------------------------------------------- 자가진단
  var VERDICTS = [
    { min: 0, cls: "",     html: "항목을 체크하면 진단 결과가 표시됩니다." },
    { min: 1, cls: "cool", html: "<b>1~2개 해당</b> — 특정 영역에서만 감점이 발생하고 있습니다. 해당 학년 기준에 맞는 모범 답안을 반복해서 따라 쓰면 빠르게 교정됩니다." },
    { min: 3, cls: "warm", html: "<b>3개 해당</b> — 구조와 문법 두 축에서 동시에 감점되고 있는 상태입니다. 감으로 쓰는 단계를 벗어나 <b>템플릿 구조를 손으로 익히는 훈련</b>이 필요합니다." },
    { min: 4, cls: "hot",  html: "<b>4개 이상 해당</b> — 말하기 실력과 쓰기 점수의 격차가 벌어지는 전형적인 패턴입니다. 레벨테스트 라이팅에서 <b>과락 위험이 높습니다.</b> 학년 기준에 맞춘 모범 답안 필사부터 시작하십시오." }
  ];

  function verdictFor(n) {
    var pick = VERDICTS[0];
    for (var i = 0; i < VERDICTS.length; i++) {
      if (n >= VERDICTS[i].min) pick = VERDICTS[i];
    }
    return pick;
  }

  function initDiagnostic() {
    var list = document.getElementById("diag-list");
    var countEl = document.getElementById("diag-count");
    var verdictEl = document.getElementById("diag-verdict");
    if (!list || !countEl || !verdictEl) return;

    var boxes = list.querySelectorAll('input[type="checkbox"]');

    function update() {
      var n = 0;
      for (var i = 0; i < boxes.length; i++) { if (boxes[i].checked) n++; }
      countEl.textContent = n;
      var v = verdictFor(n);
      verdictEl.className = "diag-verdict" + (v.cls ? " " + v.cls : "");
      verdictEl.innerHTML = v.html;
    }

    for (var i = 0; i < boxes.length; i++) {
      boxes[i].addEventListener("change", update);
    }
    update();
  }

  // ---------------------------------------------------------------- 충전 문의
  function contactInfo() {
    var cfg = (window.AXAuth && AXAuth.state.config) || {};
    return { url: cfg.purchase_contact || "", bank: cfg.purchase_bank || "" };
  }

  function initBuyButtons() {
    document.addEventListener("click", function (ev) {
      var btn = ev.target.closest("[data-buy]");
      if (!btn) return;
      var plan = btn.getAttribute("data-buy");
      var info = contactInfo();

      if (info.url) {
        // 어떤 상품을 문의하는지 알 수 있도록 새 창으로 문의처를 연다.
        window.open(info.url, "_blank", "noopener");
        return;
      }
      alert(
        plan + " 충전을 원하시면 관리자에게 문의해 주십시오.\n\n" +
        (info.bank ? "입금 계좌: " + info.bank + "\n\n" : "") +
        "입금 확인 후 충전 코드를 보내드립니다.\n받으신 코드는 아래 '충전 코드' 칸에 입력하시면 즉시 반영됩니다."
      );
    });
  }

  // ---------------------------------------------------------------- 코드 등록
  function initRedeemPanel() {
    var input = document.getElementById("pricing-code");
    var btn = document.getElementById("pricing-redeem");
    var msg = document.getElementById("pricing-redeem-msg");
    if (!input || !btn || !msg) return;

    async function submit() {
      var code = input.value.trim();
      if (!code) {
        msg.className = "redeem-msg bad";
        msg.textContent = "코드를 입력해 주십시오.";
        return;
      }
      if (!window.AXAuth || !AXAuth.state.loggedIn) {
        msg.className = "redeem-msg bad";
        msg.textContent = "충전 코드는 로그인 후 등록하실 수 있습니다.";
        return;
      }

      btn.disabled = true;
      input.disabled = true;
      msg.className = "redeem-msg";
      msg.textContent = "확인 중…";

      try {
        var headers = { "Content-Type": "application/json" };
        var t = await AXAuth.token();
        if (t) headers.Authorization = "Bearer " + t;

        var res = await fetch("/api/redeem", {
          method: "POST", headers: headers, body: JSON.stringify({ code: code })
        });
        var d = await res.json();

        if (!res.ok) {
          msg.className = "redeem-msg bad";
          msg.textContent = d.error || "코드를 사용할 수 없습니다.";
        } else {
          AXAuth.setCredits(d.balance);
          msg.className = "redeem-msg good";
          msg.textContent = d.credits + "회가 충전되었습니다. (잔액 " + d.balance + "회)";
          input.value = "";
        }
      } catch (e) {
        msg.className = "redeem-msg bad";
        msg.textContent = "충전 서버에 연결하지 못했습니다.";
      }

      btn.disabled = false;
      input.disabled = false;
    }

    btn.addEventListener("click", submit);
    input.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter") { ev.preventDefault(); submit(); }
    });
  }

  // ------------------------------------------------- 무료 공개 모드
  // Supabase 미설정 = 로그인·크레딧·결제가 없는 상태.
  // 이때 요금제와 무료 횟수 안내를 그대로 두면 화면이 사실과 달라진다.
  // 환경변수를 넣는 순간 이 함수는 아무 일도 하지 않고 유료 화면으로 돌아온다.
  var FREE_MODE_COPY = {
    "hero-cta-primary": "지금 바로 써보기",
    "cta-h2": "지금 바로 써보세요.",
    "cta-p": "가입도, 결제도 없습니다. 주제만 고르시면 됩니다."
  };

  function applyFreeMode() {
    document.body.classList.add("is-free-mode");

    // 요금제 탭과 섹션을 숨긴다.
    var navLink = document.querySelector('[data-nav="pricing"]');
    if (navLink) navLink.style.display = "none";
    if ((location.hash || "").replace("#", "") === "pricing") location.hash = "#home";

    // 히어로 · CTA 문구를 사실에 맞게 바꾼다.
    var heroBtn = document.querySelector(".hero-cta .btn-primary");
    if (heroBtn) heroBtn.textContent = FREE_MODE_COPY["hero-cta-primary"];

    var ghost = document.querySelector('.hero-cta .btn-ghost[href="#pricing"]');
    if (ghost) { ghost.setAttribute("href", "#about"); ghost.textContent = "사용법 먼저 보기"; }

    var ctaH2 = document.querySelector(".band-cta .cta-h2");
    if (ctaH2) ctaH2.textContent = FREE_MODE_COPY["cta-h2"];

    var ctaP = document.querySelector(".band-cta .cta-p");
    if (ctaP) ctaP.textContent = FREE_MODE_COPY["cta-p"];

    // FAQ 중 크레딧·결제 관련 항목을 감춘다.
    var faqs = document.querySelectorAll("#about .faq details");
    for (var i = 0; i < faqs.length; i++) {
      var q = faqs[i].querySelector("summary");
      if (!q) continue;
      var t = q.textContent;
      if (t.indexOf("크레딧") >= 0 || t.indexOf("결제") >= 0 || t.indexOf("충전") >= 0) {
        faqs[i].style.display = "none";
      }
    }
  }

  function watchMode() {
    if (!window.AXAuth) { applyFreeMode(); return; }
    AXAuth.onChange(function (st) {
      if (st.ready && !st.authEnabled) applyFreeMode();
    });
  }

  initDiagnostic();
  initBuyButtons();
  initRedeemPanel();
  watchMode();
})();
