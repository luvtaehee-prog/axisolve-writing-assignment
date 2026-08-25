/* app.js 스모크 테스트 — 브라우저 없이 런타임 오류를 잡는다.
 *
 * 문법 검사(node --check)는 "customNote is not defined" 같은 오류를 잡지 못한다.
 * 선언이 빠진 채 사용부만 남아도 파싱은 통과하기 때문이다.
 * 이 스크립트는 최소한의 DOM 을 흉내내 app.js 를 실제로 실행하고,
 * 핵심 함수를 호출해 본다.
 *
 *     node tools/smoke_app.js
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.dirname(__dirname);

// ---------- 최소 DOM 스텁 ----------
function makeEl(id) {
  const el = {
    id,
    innerHTML: "",
    value: "",
    className: "",
    textContent: "",
    style: {},
    disabled: false,
    isConnected: true,
    classList: { toggle() {}, add() {}, remove() {}, contains() { return false; } },
    addEventListener() {},
    removeEventListener() {},
    appendChild() {},
    remove() {},
    focus() {},
    setAttribute() {},
    getAttribute() { return null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    closest() { return null; },
  };
  return el;
}

const els = {};
const document = {
  getElementById(id) { return (els[id] = els[id] || makeEl(id)); },
  createElement(tag) { return makeEl(tag); },
  querySelector() { return null; },
  querySelectorAll() { return []; },
  addEventListener() {},
  body: makeEl("body"),
};

const store = {};
const localStorage = {
  getItem(k) { return k in store ? store[k] : null; },
  setItem(k, v) { store[k] = String(v); },
  removeItem(k) { delete store[k]; },
};

const sandbox = {
  document,
  localStorage,
  console,
  setTimeout,
  clearTimeout,
  URL: { createObjectURL: () => "blob:x", revokeObjectURL() {} },
  crypto: { randomUUID: () => "00000000-0000-4000-8000-000000000000" },
  location: { hash: "#generator", pathname: "/", origin: "http://localhost:3000" },
  history: { replaceState() {} },
  alert() {},
  // 주제 목록 요청만 응답한다. 나머지 호출은 테스트하지 않는다.
  fetch: async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      topics: JSON.parse(fs.readFileSync(path.join(ROOT, "topics.json"), "utf8"))
        .map(({ no, area, topic, isNew }) => ({ no, area, topic, isNew })),
      count: 165,
    }),
  }),
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;

// ---------- 실행 ----------
const code = fs.readFileSync(path.join(ROOT, "app.js"), "utf8");
const ctx = vm.createContext(sandbox);

let failed = 0;
function check(name, fn) {
  try {
    fn();
    console.log(`  OK   ${name}`);
  } catch (e) {
    failed++;
    console.log(`  FAIL ${name}: ${e && e.message}`);
  }
}

try {
  vm.runInContext(code, ctx, { filename: "app.js" });
  console.log("  OK   app.js 로드");
} catch (e) {
  console.log(`  FAIL app.js 로드: ${e && e.message}`);
  process.exit(1);
}

const app = sandbox.window.__axisolveApp;
if (!app) {
  console.log("  FAIL __axisolveApp 이 노출되지 않았습니다.");
  process.exit(1);
}

const GRADES = ["Grade 1-2", "Grade 3-4", "Grade 5-6"];

// buildPrompt — 기출 주제
const preset = {
  topic_no: 1, area: "취향", topic: "Write about your favorite book.", grades: {},
};
GRADES.forEach((g) => {
  check(`buildPrompt(${g}) 기출`, () => {
    const p = app.buildPrompt(g, preset, "강아지 초코", null);
    if (!p || p.length < 400) throw new Error("프롬프트가 너무 짧습니다");
    if (p.indexOf("[직접 입력 주제 처리 규칙]") !== -1) {
      throw new Error("기출 주제인데 직접 입력 규칙이 붙었습니다");
    }
  });
});

// buildPrompt — 직접 입력 주제
const custom = {
  topic_no: 0, custom: true, area: "직접 입력", topic: "내가 가장 좋아하는 계절", grades: {},
};
GRADES.forEach((g) => {
  check(`buildPrompt(${g}) 직접입력`, () => {
    const p = app.buildPrompt(g, custom, "가을, 단풍", null);
    if (p.indexOf("[직접 입력 주제 처리 규칙]") === -1) {
      throw new Error("직접 입력 규칙이 붙지 않았습니다");
    }
  });
});

// buildPrompt — 재시도 피드백
check("buildPrompt 재시도 피드백", () => {
  const p = app.buildPrompt("Grade 1-2", preset, "", { issues: ["단어 수 부족"], wc: 40 });
  if (p.indexOf("[이전 시도 피드백") === -1) throw new Error("피드백 블록이 없습니다");
});

// 검증 로직
check("wordCount / sentenceCount", () => {
  if (app.wordCount("I like cats. You do too.") !== 6) throw new Error("wordCount 불일치");
  if (app.sentenceCount("I like cats. You do too.") !== 2) throw new Error("sentenceCount 불일치");
});

check("assess(Grade 1-2)", () => {
  const a = app.assess("Grade 1-2", { essay: "I like cats. " .repeat(20) });
  if (!a || typeof a.wc !== "number") throw new Error("assess 결과 형식 오류");
});

// 렌더링 경로
check("renderSidebar / renderMain", () => {
  app.renderSidebar();
  app.renderMain();
});

check("showAuthModal(login/credits)", () => {
  app.showAuthModal("login", "테스트");
  app.showAuthModal("credits", "테스트");
});

check("openCustomForm", () => { app.openCustomForm(); });

console.log();
if (failed) {
  console.log(`  ${failed}건 실패`);
  process.exit(1);
}
console.log("  전부 통과");
