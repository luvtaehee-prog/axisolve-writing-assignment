(function () {
  "use strict";

  // ---------- constants ----------
  var AREAS = ["취향", "상상", "경험", "자기소개", "학교사회"];
  var AREA_COLOR = {
    "취향": "#E08A5E", "상상": "#8B7FD1", "경험": "#4FA8A0",
    "자기소개": "#D6B24E", "학교사회": "#5B8FD6",
    "직접 입력": "#CCFF00"
  };
  var GRADES = ["Grade 1-2", "Grade 3-4", "Grade 5-6"];
  var GRADE_LABEL_KO = {
    "Grade 1-2": "라이팅 워크북",
    "Grade 3-4": "논리 단락 완성 워크북",
    "Grade 5-6": "정형 4문단 아카데믹 에세이"
  };
  var GRADE_COLOR = {
    "Grade 1-2": { accent: "#A65C46", soft: "#F8F0EC", deep: "#713E30" },
    "Grade 3-4": { accent: "#39766D", soft: "#ECF5F2", deep: "#27554F" },
    "Grade 5-6": { accent: "#3F5873", soft: "#EEF2F6", deep: "#273C51" }
  };
  var RUBRIC = {
    "Grade 1-2": { minWords: 60, maxWords: 80, minSent: 5, maxSent: 7 },
    "Grade 3-4": { minWords: 100, maxWords: 130 },
    "Grade 5-6": { minWords: 180, maxWords: 220 }
  };
  var RUBRIC_TEXT = {
    "Grade 1-2": "총 60~80단어, 5~7문장. 주어+동사+목적어 중심의 단순 문장. 3인칭 단수 동사 s/es, 관사 a/an, 명사 복수형 s를 정확히 지킬 것. 구어적 축약형(don't, can't 등)은 허용.",
    "Grade 3-4": "총 100~130단어, 반드시 하나의 문단(빈 줄로 나누지 말 것). Topic Sentence → Supporting Details → Closing Sentence 구조를 지킬 것. 단문과 복문을 조화롭게 섞을 것.",
    "Grade 5-6": "총 180~220단어, 정확히 4문단(Introduction / Body 1 / Body 2 / Conclusion). 포멀한 어조를 유지하고 구어적 축약형(don't, can't, isn't 등)은 절대 쓰지 말 것. 각 근거 뒤에 상술(Elaboration)을 반드시 포함할 것."
  };
  var MAX_ATTEMPTS = 4;
  var CUSTOM_AREA = "직접 입력";
  var DRAFT_PREFIX = "axisolve_essay_draft_";

  var SYSTEM_PROMPT =
    "당신은 AXISOLVE EDUTECH(문법의 축)의 초등 영어 라이팅 교재 콘텐츠 작성 엔진입니다. " +
    "사용자 메시지에 명시된 JSON 스키마를 정확히 따르는 JSON 객체 하나만 출력하십시오. " +
    "코드펜스, 설명, 인사말, 그 외 어떤 텍스트도 JSON 앞뒤에 포함하지 마십시오.";

  var CONTRACTION_RE = /\b(?:don't|can't|won't|isn't|aren't|wasn't|weren't|doesn't|didn't|haven't|hasn't|hadn't|couldn't|wouldn't|shouldn't)\b/i;

  // ---------- utils ----------
  function wordCount(t) { var m = String(t || "").match(/[A-Za-z0-9'’-]+/g); return m ? m.length : 0; }
  function sentenceCount(t) { var m = String(t || "").match(/[.!?]["'”’)]*(?:\s|$)/g); return m ? m.length : 0; }
  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function safeSlug(topic) {
    var s = String(topic || "").trim().replace(/\.+$/, "").replace(/[^A-Za-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
    return s.slice(0, 80) || "Topic";
  }
  function pad3(n) { return String(n).padStart(3, "0"); }

  // ---------- prompt building ----------
  function schemaBlock(grade) {
    if (grade === "Grade 1-2") {
      return '{\n' +
        '  "brain": [["라벨","질문(영어)","예시 답(영어)"], ...정확히 3개],\n' +
        '  "outline": [["Opening|Detail 1|Detail 2|Closing","한국어 가이드","영어 힌트/문장 시작어"], ...정확히 4개],\n' +
        '  "keywords": ["단어: 뜻", ...최소 3개],\n' +
        '  "patterns": ["문형: 설명", ...최소 3개],\n' +
        '  "essay": "영어 에세이 본문 (한 문단, 5~7문장, 60~80단어)"\n' +
        '}';
    }
    if (grade === "Grade 3-4") {
      return '{\n' +
        '  "brain": [["라벨","질문(영어)","예시 답(영어)"], ...정확히 3개],\n' +
        '  "outline": [["Topic Sentence|Supporting Detail 1|Supporting Detail 2|Closing Sentence","한국어 가이드","영어 힌트"], ...정확히 4개],\n' +
        '  "vocab": ["단어: 뜻", ...최소 3개],\n' +
        '  "trans": ["연결어: 설명", ...최소 3개],\n' +
        '  "essay": "영어 모범 단락 (반드시 한 문단, 빈 줄 금지, 100~130단어)"\n' +
        '}';
    }
    return '{\n' +
      '  "matrix": [["Introduction|Body 1|Body 2|Conclusion","문단의 핵심 내용(영어 지시문 또는 한국어 가이드)","한국어 번역 또는 보조 힌트"], ...정확히 4개],\n' +
      '  "vocab": ["고급 어휘: 뜻", ...정확히 5개],\n' +
      '  "essay_paras": ["Introduction 문단(영어)", "Body 1 문단(영어)", "Body 2 문단(영어)", "Conclusion 문단(영어)"]\n' +
      '}';
  }

  function buildPrompt(grade, doc, keywordsText, feedback) {
    var kw = keywordsText && keywordsText.trim()
      ? keywordsText.trim()
      : "지정되지 않음 — 학년과 주제에 가장 적합한 키워드를 직접 선정할 것";
    var rr = RUBRIC[grade];
    var feedbackBlock = "";
    if (feedback) {
      feedbackBlock = "\n\n[이전 시도 피드백 - 반드시 수정할 것]\n" +
        feedback.issues.map(function (i) { return "- " + i; }).join("\n") +
        "\n이전 시도의 실제 단어수: " + feedback.wc + " (목표 " + rr.minWords + "~" + rr.maxWords + "단어).\n" +
        (feedback.wc < rr.minWords
          ? "단어수가 목표 하한선에 크게 미달했습니다. 문장을 추가하거나 근거·묘사를 보강하여 이번에는 반드시 " + rr.minWords + "단어 이상으로 작성하십시오."
          : "분량 또는 형식 기준을 다시 확인하고 위 문제를 모두 해결한 버전으로 다시 작성하십시오.");
    }
    return "[주제 정보]\n" +
      "- 영역(area): " + doc.area + "\n" +
      "- 주제 번호: " + doc.topic_no + "\n" +
      '- 주제(topic, 영어 원문 그대로 유지): "' + doc.topic + '"\n' +
      "- 대상 학년 그룹: " + grade + " (" + GRADE_LABEL_KO[grade] + ")\n" +
      "- 사용자 지정 키워드/소재: " + kw + "\n\n" +
      "[이 학년의 분량/문법 규칙]\n" + RUBRIC_TEXT[grade] + "\n\n" +
      "[출력 JSON 스키마 - 이 키만 정확히 포함할 것]\n" + schemaBlock(grade) + "\n\n" +
      "[공통 규칙]\n" +
      "- 모든 영어 문장은 문법적으로 정확하고 해당 학년 수준 어휘로 작성할 것.\n" +
      "- 한국어 가이드/설명은 자연스러운 한국어로 작성할 것.\n" +
      '- 에세이(또는 essay_paras)는 주제 "' + doc.topic + '"에서 벗어나지 말 것.\n' +
      "- 단어수는 반드시 " + rr.minWords + "~" + rr.maxWords + "단어 범위를 지킬 것. 특히 하한선(" + rr.minWords + "단어) 미달은 절대 금지이며, 상한 초과보다 훨씬 심각한 오류로 간주한다. 분량이 애매하면 짧게 쓰지 말고 하한선을 넉넉히 넘기도록(가능하면 중간값 이상) 작성할 것.\n" +
      "- 스키마에 명시된 키 외 다른 키를 추가하지 말 것.\n" +
      "- 오직 위 스키마를 따르는 JSON 객체 하나만 출력할 것." +
      customNote +
      feedbackBlock;
  }

  // ---------- API call (through /api/generate; API key never touches the browser) ----------
  // 생성 1건을 식별한다. 자동 재시도는 같은 값을 재사용하므로 크레딧이 중복 차감되지 않는다.
  function newGenId() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return "gen-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
  }

  // 로그인·크레딧 문제는 일반 오류와 다르게 처리해야 하므로 표시를 붙여 던진다.
  function billingError(kind, message) {
    var e = new Error(message);
    e.billing = kind;   // "login" | "credits"
    return e;
  }

  async function callModel(prompt, ctx) {
    var headers = { "Content-Type": "application/json" };
    if (window.AXAuth) {
      var t = await AXAuth.token();
      if (t) headers.Authorization = "Bearer " + t;
    }
    var res = await fetch("/api/generate", {
      method: "POST",
      headers: headers,
      body: JSON.stringify({
        prompt: prompt,
        system: SYSTEM_PROMPT,
        gen_id: ctx && ctx.genId,
        topic_no: ctx && ctx.topicNo,
        grade: ctx && ctx.grade
      })
    });
    var data;
    try { data = await res.json(); } catch (e) { throw new Error("서버 응답을 해석할 수 없습니다."); }
    if (!res.ok) {
      var msg = (data && data.error && (data.error.message || (typeof data.error === "string" ? data.error : JSON.stringify(data.error)))) || ("API 오류 (" + res.status + ")");
      if (res.status === 401) throw billingError("login", msg);
      if (res.status === 402) throw billingError("credits", msg);
      throw new Error(msg);
    }
    if (window.AXAuth) {
      if (typeof data.credits === "number") AXAuth.setCredits(data.credits);
      if (typeof data.free_used === "number") AXAuth.markFreeUsed();
    }
    var cleaned = String(data.text || "").replace(/```json/gi, "").replace(/```/g, "").trim();
    var start = cleaned.indexOf("{");
    var end = cleaned.lastIndexOf("}");
    if (start === -1 || end === -1) throw new Error("응답에서 JSON을 찾을 수 없음");
    return JSON.parse(cleaned.slice(start, end + 1));
  }

  // ---------- validation (mirrors axisolve_workbook_renderer.py validate_document) ----------
  function assess(grade, data) {
    if (!data) return null;
    var rr = RUBRIC[grade];
    var issues = [];
    var wc = 0, sc = null;

    if (grade === "Grade 1-2") {
      wc = wordCount(data.essay);
      sc = sentenceCount(data.essay);
      if (!(data.brain && data.brain.length === 3)) issues.push("brain 3개 필요");
      if (!(data.outline && data.outline.length === 4)) issues.push("outline 4개 필요");
      if (!(data.keywords && data.keywords.length >= 3)) issues.push("keywords 3개 이상 필요");
      if (!(data.patterns && data.patterns.length >= 3)) issues.push("patterns 3개 이상 필요");
      if (!(wc >= rr.minWords && wc <= rr.maxWords)) issues.push("단어수 " + wc + " (기준 " + rr.minWords + "~" + rr.maxWords + ")");
      if (!(sc >= rr.minSent && sc <= rr.maxSent)) issues.push("문장수 " + sc + " (기준 " + rr.minSent + "~" + rr.maxSent + ")");
    } else if (grade === "Grade 3-4") {
      wc = wordCount(data.essay);
      if (!(data.brain && data.brain.length === 3)) issues.push("brain 3개 필요");
      if (!(data.outline && data.outline.length === 4)) issues.push("outline 4개 필요");
      if (!(data.vocab && data.vocab.length >= 3)) issues.push("vocab 3개 이상 필요");
      if (!(data.trans && data.trans.length >= 3)) issues.push("trans 3개 이상 필요");
      if (String(data.essay || "").indexOf("\n\n") !== -1) issues.push("한 문단이어야 함 (빈 줄 발견)");
      if (!(wc >= rr.minWords && wc <= rr.maxWords)) issues.push("단어수 " + wc + " (기준 " + rr.minWords + "~" + rr.maxWords + ")");
    } else {
      var paras = data.essay_paras || [];
      var essay = paras.join(" ");
      wc = wordCount(essay);
      if (!(data.matrix && data.matrix.length === 4)) issues.push("matrix 4개 필요");
      if (!(data.vocab && data.vocab.length === 5)) issues.push("vocab 정확히 5개 필요");
      if (paras.length !== 4) issues.push("essay_paras 정확히 4개 필요");
      if (CONTRACTION_RE.test(essay)) issues.push("격식체 위반 (구어적 축약형 발견)");
      if (!(wc >= rr.minWords && wc <= rr.maxWords)) issues.push("단어수 " + wc + " (기준 " + rr.minWords + "~" + rr.maxWords + ")");
    }
    return { wc: wc, sc: sc, ok: issues.length === 0, issues: issues, range: [rr.minWords, rr.maxWords] };
  }

  function isBetterAttempt(candidate, current) {
    if (!current) return true;
    if (candidate.issues.length !== current.issues.length) return candidate.issues.length < current.issues.length;
    var candidateMeetsMin = candidate.wc >= candidate.range[0];
    var currentMeetsMin = current.wc >= current.range[0];
    if (candidateMeetsMin !== currentMeetsMin) return candidateMeetsMin;
    return false;
  }

  async function generateWithRetry(grade, doc, keywordsText, onAttempt) {
    var best = null;
    var feedback = null;
    var lastError = null;
    var ctx = { genId: newGenId(), topicNo: doc.topic_no, grade: grade };
    for (var attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
      if (onAttempt) onAttempt(attempt, MAX_ATTEMPTS);
      var prompt = buildPrompt(grade, doc, keywordsText, feedback);
      var parsed;
      try {
        parsed = await callModel(prompt, ctx);
      } catch (e) {
        // 로그인·크레딧 문제는 재시도해도 결과가 같으므로 즉시 중단한다.
        if (e && e.billing) throw e;
        lastError = e;
        continue;
      }
      var a = assess(grade, parsed);
      if (isBetterAttempt(a, best ? best.assessment : null)) {
        best = { data: parsed, assessment: a };
      }
      if (a.ok) {
        return { data: parsed, assessment: a, attempts: attempt, forced: false };
      }
      feedback = { issues: a.issues, wc: a.wc };
    }
    if (!best) throw lastError || new Error("생성 실패");
    return { data: best.data, assessment: best.assessment, attempts: MAX_ATTEMPTS, forced: true };
  }



  // ---------- 내 주제로 직접 쓰기 ----------
  var customFormOpen = false;

  function openCustomForm() {
    customFormOpen = true;
    errorMsg = "";
    renderSidebar();
    renderMain();
    var el = document.getElementById("cf-topic");
    if (el) el.focus();
  }

  function closeCustomForm() {
    customFormOpen = false;
    renderSidebar();
    renderMain();
  }

  function renderCustomFormHtml() {
    return '<div class="custom-form">' +
      '<h2>내 주제로 직접 쓰기</h2>' +
      '<p class="cf-lede">쓰고 싶은 주제와 아이디어를 넣으면, 기출 주제와 똑같은 학년 기준으로 에세이가 만들어집니다. ' +
      '한글로 적으셔도 영어 에세이로 나옵니다.</p>' +

      '<div class="cf-field">' +
        '<label for="cf-topic">주제 <i>(필수)</i></label>' +
        '<input id="cf-topic" type="text" maxlength="200" ' +
               'placeholder="예) 내가 가장 좋아하는 계절 / Write about your best friend." />' +
        '<p class="cf-hint">학교 수행평가 주제, 독후감, 대회 주제, 아이가 쓰고 싶어 하는 이야기 모두 됩니다.</p>' +
      '</div>' +

      '<div class="cf-field">' +
        '<label for="cf-idea">아이디어 · 꼭 넣을 내용 <i>(선택)</i></label>' +
        '<textarea id="cf-idea" rows="4" maxlength="1000" ' +
                  'placeholder="예) 가을을 좋아함. 이유는 단풍, 시원한 바람, 할머니 댁 감나무. 작년 가을 소풍 이야기를 넣고 싶음."></textarea>' +
        '<p class="cf-hint">비워두면 AI가 주제에 맞는 소재를 직접 고릅니다. 구체적으로 적을수록 아이 이야기에 가까워집니다.</p>' +
      '</div>' +

      '<div class="cf-actions">' +
        '<button class="cf-submit" data-cf="submit">이 주제로 시작하기</button>' +
        '<button class="cf-cancel" data-cf="cancel">취소</button>' +
      '</div>' +
      '<p class="cf-error" id="cf-error"></p>' +
    '</div>';
  }

  function submitCustomForm() {
    var topicEl = document.getElementById("cf-topic");
    var ideaEl = document.getElementById("cf-idea");
    var errEl = document.getElementById("cf-error");
    if (!topicEl) return;

    var topic = topicEl.value.trim();
    if (topic.length < 2) {
      if (errEl) errEl.textContent = "주제를 입력해 주십시오.";
      topicEl.focus();
      return;
    }

    selectedTopic = { no: 0, area: CUSTOM_AREA, topic: topic, src: "직접 입력" };
    activeGrade = "Grade 1-2";
    errorMsg = "";

    var saved = null;
    try {
      var raw = localStorage.getItem(customKey(topic));
      saved = raw ? JSON.parse(raw) : null;
    } catch (e) { saved = null; }

    if (saved && saved.doc) {
      doc = saved.doc;
      keywordsText = saved.keywordsText || "";
    } else {
      doc = { topic_no: 0, custom: true, area: CUSTOM_AREA, topic: topic,
              source_academy: "직접 입력", grades: {} };
      keywordsText = ideaEl ? ideaEl.value.trim() : "";
    }

    customFormOpen = false;
    renderSidebar();
    renderMain();
  }

  document.addEventListener("click", function (ev) {
    var t = ev.target.closest("[data-cf]");
    if (!t) return;
    var a = t.getAttribute("data-cf");
    if (a === "submit") submitCustomForm();
    if (a === "cancel") closeCustomForm();
  });

  document.addEventListener("keydown", function (ev) {
    if (ev.key !== "Enter" || !customFormOpen) return;
    if (ev.target && ev.target.id === "cf-topic") {
      ev.preventDefault();
      submitCustomForm();
    }
  });

  // ---------- 로그인 / 크레딧 UI ----------
  function closeAuthModal() {
    var m = document.getElementById("auth-modal");
    if (m) m.remove();
  }

  // kind: "login"  무료 체험 소진 → 카카오 로그인 유도
  //       "credits" 크레딧 소진   → 충전 안내
  function showAuthModal(kind, message) {
    closeAuthModal();
    var A = window.AXAuth;
    var bonus = (A && A.state.signupBonus) || 3;

    var cfg = (A && A.state.config) || {};
    var contact = cfg.purchase_contact || "";
    var bank = cfg.purchase_bank || "";

    var inner;
    if (kind === "credits") {
      inner =
        '<h3 class="auth-title">크레딧이 부족합니다</h3>' +
        '<p class="auth-desc">' + escapeHtml(message || "충전 후 계속 이용하실 수 있습니다.") + '</p>' +
        '<div class="auth-plans">' +
          '<div class="auth-plan"><b>라이트</b><span>30회</span><em>4,900원</em></div>' +
          '<div class="auth-plan"><b>스탠다드</b><span>100회</span><em>12,900원</em></div>' +
          '<div class="auth-plan"><b>프로</b><span>500회</span><em>39,000원</em></div>' +
        '</div>' +
        (bank ? '<p class="auth-bank">' + escapeHtml(bank) + '</p>' : '') +
        (contact
          ? '<a class="auth-contact" href="' + escapeHtml(contact) + '" target="_blank" rel="noopener">충전 문의하기</a>'
          : '<p class="auth-note">충전을 원하시면 관리자에게 문의해 주십시오.</p>') +
        '<div class="redeem-box">' +
          '<label class="redeem-label" for="redeem-input">충전 코드를 받으셨나요?</label>' +
          '<div class="redeem-row">' +
            '<input id="redeem-input" class="redeem-input" type="text" autocomplete="off" ' +
                   'placeholder="AX-XXXX-XXXX" maxlength="20" spellcheck="false">' +
            '<button class="redeem-btn" data-auth="redeem">등록</button>' +
          '</div>' +
          '<p class="redeem-msg" id="redeem-msg"></p>' +
        '</div>' +
        '<button class="auth-close-btn" data-auth="close">닫기</button>';
    } else {
      inner =
        '<h3 class="auth-title">무료 체험을 모두 사용하셨습니다</h3>' +
        '<p class="auth-desc">카카오 로그인 한 번이면 <b>' + bonus + '회</b>를 더 드립니다.<br>' +
        '한 주제에 대해 세 학년 답안을 모두 받아보실 수 있는 분량입니다.</p>' +
        '<button class="kakao-btn" data-auth="login">' +
          '<span class="kakao-icon" aria-hidden="true"></span>카카오로 계속하기</button>' +
        '<button class="auth-close-btn" data-auth="close">나중에 하기</button>';
    }

    var el = document.createElement("div");
    el.id = "auth-modal";
    el.className = "auth-backdrop";
    el.innerHTML = '<div class="auth-card" role="dialog" aria-modal="true">' + inner + '</div>';
    el.addEventListener("click", function (ev) {
      var act = ev.target.closest("[data-auth]");
      if (act) {
        var a = act.getAttribute("data-auth");
        if (a === "login") { AXAuth.login(); return; }
        if (a === "close") { closeAuthModal(); return; }
        if (a === "redeem") { submitRedeem(act); return; }
      }
      if (ev.target === el) closeAuthModal();
    });
    document.body.appendChild(el);

    var input = document.getElementById("redeem-input");
    if (input) {
      input.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter") {
          ev.preventDefault();
          var btn = el.querySelector('[data-auth="redeem"]');
          if (btn && !btn.disabled) submitRedeem(btn);
        }
      });
    }
  }

  async function submitRedeem(btn) {
    var input = document.getElementById("redeem-input");
    var msg = document.getElementById("redeem-msg");
    if (!input || !msg) return;

    var code = input.value.trim();
    if (!code) { msg.className = "redeem-msg bad"; msg.textContent = "코드를 입력해 주십시오."; return; }

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
        btn.disabled = false;
        input.disabled = false;
        return;
      }

      AXAuth.setCredits(d.balance);
      msg.className = "redeem-msg good";
      msg.textContent = d.credits + "회가 충전되었습니다. (잔액 " + d.balance + "회)";
      setTimeout(closeAuthModal, 1600);
    } catch (e) {
      msg.className = "redeem-msg bad";
      msg.textContent = "충전 서버에 연결하지 못했습니다.";
      btn.disabled = false;
      input.disabled = false;
    }
  }

  function renderAuthBar(st) {
    var host = document.getElementById("auth-slot");
    if (!host) return;

    if (!st.authEnabled) { host.innerHTML = ""; return; }

    if (st.loggedIn) {
      host.innerHTML =
        '<button class="credit-badge' + (st.credits === 0 ? ' empty' : '') +
          '" data-authbar="topup" title="크레딧 충전">' +
          '<span class="credit-num">' + st.credits + '</span>회' +
        '</button>' +
        '<span class="auth-user">' + escapeHtml(st.name || "회원") + '</span>' +
        '<button class="auth-link" data-authbar="logout">로그아웃</button>';
    } else {
      var left = AXAuth.freeRemaining();
      host.innerHTML =
        '<span class="credit-badge free" title="비회원 무료 체험">무료 ' + left + '회</span>' +
        '<button class="kakao-btn small" data-authbar="login">' +
          '<span class="kakao-icon" aria-hidden="true"></span>카카오 로그인</button>';
    }
  }

  document.addEventListener("click", function (ev) {
    var t = ev.target.closest("[data-authbar]");
    if (!t) return;
    var a = t.getAttribute("data-authbar");
    if (a === "login") AXAuth.login();
    if (a === "logout") AXAuth.logout();
    if (a === "topup") showAuthModal("credits", "충전 코드를 등록하시거나 아래 상품을 확인해 주십시오.");
  });

  // ---------- persistence (browser localStorage) ----------
  function draftKey(no) { return DRAFT_PREFIX + no; }

  // 커스텀 주제는 번호가 없으므로 주제문에서 안정적인 키를 만든다.
  function customKey(topic) {
    var h = 0, str = String(topic || "");
    for (var i = 0; i < str.length; i++) { h = (h * 31 + str.charCodeAt(i)) | 0; }
    return DRAFT_PREFIX + "c" + (h >>> 0).toString(36);
  }
  function docKey(d) { return d.custom ? customKey(d.topic) : draftKey(d.topic_no); }

  function saveDraft(d, kw) {
    try { localStorage.setItem(docKey(d), JSON.stringify({ doc: d, keywordsText: kw })); } catch (e) {}
  }
  function loadDraft(no) {
    try {
      var raw = localStorage.getItem(draftKey(no));
      return raw ? JSON.parse(raw) : null;
    } catch (e) { return null; }
  }
  function hasSavedDraft(no) {
    try { return localStorage.getItem(draftKey(no)) !== null; } catch (e) { return false; }
  }

  // ---------- state ----------
  var TOPICS = [];
  var selectedTopic = null;
  var doc = null;
  var keywordsText = "";
  var activeGrade = "Grade 1-2";
  var loadingInfo = {};
  var errorMsg = "";
  var expandedAreas = {};
  var search = "";

  function matchesQuery(t, q) {
    return !q || t.topic.toLowerCase().indexOf(q) !== -1 || String(t.no).indexOf(q) !== -1 || t.src.toLowerCase().indexOf(q) !== -1;
  }

  // ---------- rendering: sidebar ----------
  function syncCustomBtn() {
    var b = document.getElementById("custom-topic-btn");
    if (b) b.classList.toggle("is-on", customFormOpen || !!(doc && doc.custom));
  }

  function renderSidebar() {
    var query = search.trim().toLowerCase();
    var html = "";
    AREAS.forEach(function (area) {
      var totalInArea = TOPICS.filter(function (t) { return t.area === area; }).length;
      var list = TOPICS.filter(function (t) { return t.area === area && matchesQuery(t, query); });
      var open = !!query || !!expandedAreas[area];
      html += '<div>' +
        '<button type="button" class="area-header ' + (open ? "open" : "") + '" data-area="' + escapeHtml(area) + '">' +
        '<svg class="chev" width="13" height="13" viewBox="0 0 24 24" fill="none"><path d="M9 6l6 6-6 6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
        '<span class="dot" style="background:' + AREA_COLOR[area] + '"></span>' +
        '<span class="name">' + escapeHtml(area) + '</span>' +
        '<span class="count">' + totalInArea + '</span>' +
        '</button>';
      if (open) {
        if (list.length === 0) {
          html += '<div style="padding:8px 12px 8px 26px; font-size:12px; color:var(--muted-3);">검색 결과 없음</div>';
        } else {
          list.forEach(function (t) {
            var active = selectedTopic && t.no === selectedTopic.no;
            html += '<button type="button" class="topic-item ' + (active ? "active" : "") + '" data-topic-no="' + t.no + '">' +
              '<span class="no">' + pad3(t.no) + '</span>' +
              '<span class="txt"><span class="t">' + escapeHtml(t.topic) + '</span><span class="s">' + escapeHtml(t.src) + (t.isNew ? " · 신규" : "") + '</span></span>' +
              (hasSavedDraft(t.no) ? '<span class="saved">✓</span>' : "") +
              '</button>';
          });
        }
      }
      html += '</div>';
    });
    document.getElementById("sidebar-list").innerHTML = html;
  }

  // ---------- rendering: main ----------
  function section(title, color, inner) {
    return '<div class="section">' +
      '<div class="section-title" style="color:' + color.accent + '"><span class="bar" style="background:' + color.accent + '"></span>' + escapeHtml(title) + '</div>' +
      inner + '</div>';
  }
  function listBoxRows(items) {
    return (items || []).map(function (item) {
      var s = String(item);
      var left = "", right = s;
      var idx = s.indexOf(":");
      if (idx !== -1) { left = s.slice(0, idx).trim(); right = s.slice(idx + 1).trim(); }
      return '<div class="row">' + (left ? "<b>" + escapeHtml(left) + "</b>: " : "") + escapeHtml(right) + '</div>';
    }).join("");
  }
  function listBoxHtml(items) { return '<div class="list-box">' + listBoxRows(items) + '</div>'; }

  function renderGradePanelHtml(grade) {
    var color = GRADE_COLOR[grade];
    var data = doc.grades[grade];
    var loading = loadingInfo[grade];
    var attemptLabel = loading && loading.attempt > 1 ? " (재시도 " + loading.attempt + "/" + loading.max + ")" : "";

    var html = '<div class="panel-top">' +
      '<div class="panel-rubric">' + escapeHtml(RUBRIC_TEXT[grade]) + '</div>' +
      '<button type="button" class="btn" id="generate-grade-btn" style="background:' + color.accent + '; color:#fff;" ' + (loading ? "disabled" : "") + '>' +
      (loading ? '<span class="spinner"></span>' : "↻") + " " + (data ? "다시 생성" : "이 학년 생성") + attemptLabel +
      '</button></div>';

    if (!data && !loading) { return html + '<div class="panel-empty">아직 생성되지 않았습니다.</div>'; }
    if (loading && !data) { return html + '<div class="panel-loading"><span class="spinner"></span> 생성 중' + attemptLabel + '...</div>'; }

    var assessment = assess(grade, data);
    var min = assessment.range[0], max = assessment.range[1];
    var span = max * 1.35;
    var pct = Math.min(100, (assessment.wc / span) * 100);
    var minPct = (min / span) * 100;
    var maxPct = (max / span) * 100;
    var inRange = assessment.wc >= min && assessment.wc <= max;

    html += '<div class="gauge-box">' +
      '<div class="gauge-row"><span>합격 기준 ' + min + '~' + max + '단어</span><span style="color:' + (inRange ? "var(--good)" : "var(--bad)") + '; font-weight:700;">' + assessment.wc + '단어</span></div>' +
      '<div class="gauge-track"><div class="gauge-zone" style="left:' + minPct + '%; width:' + Math.max(0, maxPct - minPct) + '%; background:' + color.accent + ';"></div>' +
      '<div class="gauge-fill" style="width:' + pct + '%; background:' + (inRange ? "var(--good)" : "var(--bad)") + ';"></div></div>' +
      (assessment.issues.length > 0 ? '<ul class="gauge-issues">' + assessment.issues.map(function (i) { return "<li>⚠ " + escapeHtml(i) + "</li>"; }).join("") + '</ul>' : "") +
      '</div>';

    if (grade !== "Grade 5-6") {
      var brainInner = '<div class="card-grid">' + (data.brain || []).map(function (item) {
        var arr = item.length === 3 ? item : ["", item[0], item[1]];
        return '<div class="brain-card" style="background:' + color.soft + '; border-top-color:' + color.accent + ';">' +
          (arr[0] ? '<div class="label" style="color:' + color.deep + '">' + escapeHtml(arr[0]) + '</div>' : "") +
          '<div class="q">' + escapeHtml(arr[1]) + '</div><div class="a">' + escapeHtml(arr[2]) + '</div></div>';
      }).join("") + '</div>';
      html += section("브레인스토밍", color, brainInner);

      var outlineInner = (data.outline || []).map(function (row) {
        return '<div class="outline-row"><div class="role" style="color:' + color.accent + '">' + escapeHtml(row[0]) + '</div>' +
          '<div class="content">' + escapeHtml(row[1]) + '<div class="hint">' + escapeHtml(row[2]) + '</div></div></div>';
      }).join("");
      html += section(grade === "Grade 1-2" ? "스토리 뼈대 아웃라인" : "단락 구조 아웃라인", color, outlineInner);
    }

    if (grade === "Grade 1-2") {
      html += section("키워드 & 문장 패턴", color, '<div class="list2">' + listBoxHtml(data.keywords) + listBoxHtml(data.patterns) + '</div>');
    }
    if (grade === "Grade 3-4") {
      html += section("핵심 어휘 & 연결어", color, '<div class="list2">' + listBoxHtml(data.vocab) + listBoxHtml(data.trans) + '</div>');
    }
    if (grade === "Grade 5-6") {
      var matrixInner = (data.matrix || []).map(function (row) {
        return '<div class="outline-row"><div class="role" style="color:' + color.accent + '">' + escapeHtml(row[0]) + '</div>' +
          '<div class="content">' + escapeHtml(row[1]) + '<div class="hint">' + escapeHtml(row[2]) + '</div></div></div>';
      }).join("");
      html += section("4문단 아웃라인 매트릭스", color, matrixInner);
      html += section("고급 아카데믹 어휘 5종", color, '<div class="list-box">' + listBoxRows(data.vocab) + '</div>');
    }

    var paras = grade === "Grade 5-6" ? (data.essay_paras || []) : [data.essay];
    var essayInner = '<div class="essay-box" style="border-top-color:' + color.accent + ';">' + paras.map(function (p) { return "<p>" + escapeHtml(p) + "</p>"; }).join("") + '</div>';
    html += section(grade === "Grade 5-6" ? "모델 에세이 (4문단)" : "모델 에세이", color, essayInner);

    return html;
  }

  function renderMain() {
    var mainEl = document.getElementById("main");
    syncCustomBtn();
    if (customFormOpen) {
      mainEl.innerHTML = renderCustomFormHtml();
      return;
    }
    if (!selectedTopic || !doc) {
      mainEl.innerHTML = '<div class="empty-state">왼쪽에서 주제를 고르거나, ' +
        '<b>내 주제로 직접 쓰기</b>를 눌러 시작하십시오.</div>';
      return;
    }
    var generatedCount = GRADES.filter(function (g) { return !!doc.grades[g]; }).length;
    var anyLoading = Object.keys(loadingInfo).length > 0;

    var html = '<div class="topic-head">' +
      '<div class="meta"><span class="area-tag" style="color:' + AREA_COLOR[doc.area] + '">' + escapeHtml(doc.area) + '</span>' +
      (doc.custom
        ? '<span class="custom-badge">직접 입력</span>'
        : '<span class="no">No.' + pad3(doc.topic_no) + '</span><span>· ' + escapeHtml(doc.source_academy || "") + '</span>') +
      '</div>' +
      '<h1>' + escapeHtml(doc.topic) + '</h1></div>';

    html += '<div class="controls">' +
      '<div><label>사용자 지정 키워드/소재 (선택 — 비워두면 학년·주제에 맞게 자동 선정)</label>' +
      '<textarea id="keywords-input" rows="2" placeholder="예: 우리 집 강아지 초코, 여름방학 캠핑">' + escapeHtml(keywordsText) + '</textarea></div>' +
      '<div class="controls-actions">' +
      '<button type="button" class="btn btn-primary" id="generate-all-btn" ' + (anyLoading ? "disabled" : "") + '>✦ 3개 학년 전체 생성</button>' +
      '<button type="button" class="btn btn-secondary" id="export-btn" ' + (generatedCount === 0 ? "disabled" : "") + '>⬇ JSON 내보내기</button>' +
      '<span class="status-note">' + generatedCount + '/3 학년 생성됨</span>' +
      '</div>' +
      (errorMsg ? '<div class="error-box">⚠ ' + escapeHtml(errorMsg) + '</div>' : "") +
      '<div class="hint">내보낸 JSON은 axisolve_workbook_renderer.py의 SOURCE 폴더에 넣어 PDF로 렌더링합니다.</div>' +
      '</div>';

    html += '<div class="grade-tabs">';
    GRADES.forEach(function (g) {
      var color = GRADE_COLOR[g];
      var active = activeGrade === g;
      var has = !!doc.grades[g];
      var loading = loadingInfo[g];
      var statHtml = "";
      if (loading) {
        statHtml = '<span class="gstat" style="color:var(--muted-2)"><span class="spinner"></span> ' + loading.attempt + '/' + loading.max + '</span>';
      } else if (has) {
        var a = assess(g, doc.grades[g]);
        statHtml = '<span class="gstat" style="color:' + (a.ok ? "var(--good)" : "var(--bad)") + '">' + (a.ok ? "✓" : "✕") + ' ' + a.wc + '단어</span>';
      }
      html += '<button type="button" class="grade-tab ' + (active ? "active" : "") + '" style="border-bottom-color:' + (active ? color.accent : "transparent") + '" data-grade="' + g + '">' +
        '<span class="glabel">' + g + '</span><span class="gsub">' + GRADE_LABEL_KO[g] + '</span>' + statHtml + '</button>';
    });
    html += '</div>';

    html += '<div class="panel" id="grade-panel">' + renderGradePanelHtml(activeGrade) + '</div>';

    mainEl.innerHTML = html;
  }

  // ---------- actions ----------
  async function handleGenerate(grade) {
    if (!doc) return;
    errorMsg = "";
    loadingInfo[grade] = { attempt: 1, max: MAX_ATTEMPTS };
    renderMain();
    try {
      var result = await generateWithRetry(grade, doc, keywordsText, function (attempt, max) {
        loadingInfo[grade] = { attempt: attempt, max: max };
        renderMain();
      });
      doc.grades[grade] = result.data;
      saveDraft(doc, keywordsText);
      renderSidebar();
      if (result.forced) {
        errorMsg = GRADE_LABEL_KO[grade] + ": " + MAX_ATTEMPTS + "회 시도 후에도 기준 미달 (" + result.assessment.issues.join(", ") + "). 필요 시 다시 생성하십시오.";
      }
    } catch (e) {
      if (e && e.billing) {
        showAuthModal(e.billing, e.message);
        errorMsg = "";
      } else {
        errorMsg = GRADE_LABEL_KO[grade] + " 생성 실패: " + ((e && e.message) || "알 수 없는 오류");
      }
    } finally {
      delete loadingInfo[grade];
      renderMain();
    }
  }

  async function handleGenerateAll() {
    for (var i = 0; i < GRADES.length; i++) {
      await handleGenerate(GRADES[i]);
      // 로그인·크레딧 때문에 막혔다면 남은 학년을 시도해도 같은 결과다.
      if (document.getElementById("auth-modal")) return;
    }
  }

  function handleExport() {
    if (!doc) return;
    var clean = { topic_no: doc.topic_no, area: doc.area, topic: doc.topic, source_academy: doc.source_academy, grades: {} };
    GRADES.forEach(function (g) {
      if (doc.grades[g]) {
        var rest = Object.assign({}, doc.grades[g]);
        delete rest.word_count;
        clean.grades[g] = rest;
      }
    });
    var blob = new Blob([JSON.stringify(clean, null, 2)], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = pad3(doc.topic_no) + "_" + safeSlug(doc.topic) + ".json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function selectTopicByNo(no) {
    var t = null;
    for (var i = 0; i < TOPICS.length; i++) { if (TOPICS[i].no === no) { t = TOPICS[i]; break; } }
    if (!t) return;
    selectedTopic = t;
    errorMsg = "";
    activeGrade = "Grade 1-2";
    var draft = loadDraft(no);
    if (draft && draft.doc) {
      doc = draft.doc;
      keywordsText = draft.keywordsText || "";
    } else {
      doc = { topic_no: t.no, area: t.area, topic: t.topic, source_academy: t.src, grades: {} };
      keywordsText = "";
    }
    renderSidebar();
    renderMain();
  }

  function toggleArea(area) {
    expandedAreas[area] = !expandedAreas[area];
    renderSidebar();
  }

  // ---------- event delegation ----------
  document.getElementById("sidebar-list").addEventListener("click", function (e) {
    var areaBtn = e.target.closest(".area-header");
    if (areaBtn) { toggleArea(areaBtn.getAttribute("data-area")); return; }
    var topicBtn = e.target.closest(".topic-item");
    if (topicBtn) { selectTopicByNo(parseInt(topicBtn.getAttribute("data-topic-no"), 10)); return; }
  });

  document.getElementById("main").addEventListener("click", function (e) {
    var gradeTab = e.target.closest(".grade-tab");
    if (gradeTab) { activeGrade = gradeTab.getAttribute("data-grade"); renderMain(); return; }
    if (e.target.closest("#generate-all-btn")) { handleGenerateAll(); return; }
    if (e.target.closest("#export-btn")) { handleExport(); return; }
    if (e.target.closest("#generate-grade-btn")) { handleGenerate(activeGrade); return; }
  });

  document.getElementById("main").addEventListener("input", function (e) {
    if (e.target.id === "keywords-input") { keywordsText = e.target.value; }
  });
  document.getElementById("main").addEventListener("change", function (e) {
    if (e.target.id === "keywords-input" && doc) { keywordsText = e.target.value; saveDraft(doc, keywordsText); }
  });

  var searchInput = document.getElementById("search-input");
  if (searchInput) {
    searchInput.addEventListener("input", function (e) {
      search = e.target.value;
      renderSidebar();
    });
  }

  // ---------- init ----------
  async function init() {
    try {
      var res = await fetch("topics.json");
      TOPICS = await res.json();
    } catch (e) {
      document.getElementById("sidebar-list").innerHTML = '<div style="padding:16px; color:var(--bad); font-size:13px;">topics.json을 불러오지 못했습니다.</div>';
      return;
    }
    var countEl = document.getElementById("topic-count");
    if (countEl) countEl.textContent = TOPICS.length;
    renderSidebar();

    var customBtn = document.getElementById("custom-topic-btn");
    if (customBtn) customBtn.addEventListener("click", openCustomForm);

    if (window.AXAuth) {
      AXAuth.onChange(function (st) {
        renderAuthBar(st);
        // 로그인 직후 보너스가 지급됐으면 열려 있던 안내를 닫는다.
        if (st.loggedIn) closeAuthModal();
      });
    }
  }

  init();

  // expose a few internals for testing
  window.__axisolveApp = {
    wordCount: wordCount, sentenceCount: sentenceCount, assess: assess, buildPrompt: buildPrompt,
    generateWithRetry: generateWithRetry, selectTopicByNo: selectTopicByNo, toggleArea: toggleArea,
    handleGenerate: handleGenerate, handleExport: handleExport, renderSidebar: renderSidebar, renderMain: renderMain,
    showAuthModal: showAuthModal, renderAuthBar: renderAuthBar,
    openCustomForm: openCustomForm, submitCustomForm: submitCustomForm,
    getState: function () {
      return { TOPICS: TOPICS, selectedTopic: selectedTopic, doc: doc, keywordsText: keywordsText, activeGrade: activeGrade, loadingInfo: loadingInfo, errorMsg: errorMsg };
    }
  };
})();
