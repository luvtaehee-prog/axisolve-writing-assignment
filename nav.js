/* 3개 섹션(#home / #generator / #about) 해시 라우팅.
   app.js 보다 먼저 로드되지만, 두 스크립트는 서로 참조하지 않는다. */
(function () {
  "use strict";

  var PAGES = ["home", "generator", "about"];

  function currentPage() {
    var id = String(location.hash || "").replace(/^#/, "");
    return PAGES.indexOf(id) >= 0 ? id : "home";
  }

  function render() {
    var active = currentPage();
    PAGES.forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.classList.toggle("is-active", id === active);
    });
    var links = document.querySelectorAll("[data-nav]");
    for (var i = 0; i < links.length; i++) {
      var on = links[i].getAttribute("data-nav") === active;
      links[i].classList.toggle("is-current", on);
      if (on) links[i].setAttribute("aria-current", "page");
      else links[i].removeAttribute("aria-current");
    }
    document.body.classList.toggle("is-generator", active === "generator");
    window.scrollTo(0, 0);
  }

  window.addEventListener("hashchange", render);
  render();
})();
