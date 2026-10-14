(function () {
  var D = JSON.parse(document.getElementById("i18n").textContent), T = D.js, $ = function (id) { return document.getElementById(id); };
  var form = $("cf"), statusEl = $("status"), resEl = $("result"), busy = false;
  function fmt(s, v) { return s.replace(/\{(\w+)\}/g, function (_, k) { return v && v[k] != null ? v[k] : ""; }); }
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function post(path, body) {
    return fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { return { status: r.status, body: j }; }); });
  }
  function checkText(c, res) {
    var id = c.id, st = c.status;
    if (st === "na") return T.na;
    var key = id + "_" + st;
    if (id === "crawlers" && st === "pass" && !c.robots_found) key = "crawlers_pass_norobots";
    return fmt(T[key] || "", { bots: (c.blocked || []).join(", "), words: c.words, found: (c.found || []).join(", ") });
  }
  function render(res) {
    resEl.textContent = "";
    var checks = res.checks || [], pass = checks.filter(function (c) { return c.status === "pass"; }).length;
    var counted = checks.filter(function (c) { return c.status !== "na" && c.status !== "info"; }).length;
    var h = el("h2", null, T.r_h + " " + res.site.replace(/^https?:\/\//, "")); resEl.appendChild(h);
    resEl.appendChild(el("p", "sum", fmt(T.r_sum, { pass: pass, total: counted })));
    if (res.redirected_to) resEl.appendChild(el("p", "note", fmt(T.redirected, { url: res.redirected_to.replace(/^https?:\/\//, "") })));
    var ul = el("ul", "cl");
    checks.forEach(function (c) {
      var li = el("li", "ck-" + c.status), head = el("div", "ch");
      head.appendChild(el("span", "pill " + c.status, T["s_" + c.status] || c.status));
      head.appendChild(el("b", null, T["t_" + c.id]));
      li.appendChild(head); li.appendChild(el("p", null, checkText(c, res)));
      if (c.id === "product_schema" && res.product_page) li.appendChild(el("p", "note", fmt(T.on_page, { url: res.product_page.replace(/^https?:\/\//, "") })));
      ul.appendChild(li);
    });
    resEl.appendChild(ul);
    resEl.appendChild(el("p", "note", T.method));
    snapshot(res.snapshot);
    mailBox(res);
    var fx = el("div", "fixbox"); fx.appendChild(el("h2", null, T.fix_h)); fx.appendChild(el("p", null, T.fix_p));
    var a = el("a", "btn p", T.fix_go); a.href = D.price_url; a.rel = "noopener";
    a.addEventListener("click", function () { try { navigator.sendBeacon("/api/event", new Blob([JSON.stringify({ type: "fixpack_click", lang: D.lang })], { type: "application/json" })); } catch (e) {} });
    fx.appendChild(a); resEl.appendChild(fx);
    resEl.hidden = false; resEl.focus(); try { resEl.scrollIntoView({ behavior: "smooth", block: "start" }); } catch (e) {}
  }
  function snapshot(s) {
    var box = el("div", "snap"), country = D.countries[$("f-country").value], niche = D.niches[$("f-niche").value];
    if (!s) { box.appendChild(el("p", "note", T.snap_none)); resEl.appendChild(box); return; }
    box.appendChild(el("h2", null, fmt(T.snap_h, { niche: niche, country: country })));
    var ol = el("ol", "rank");
    s.top.forEach(function (x) { var li = el("li"); li.appendChild(el("span", null, x.name)); li.appendChild(el("b", null, fmt(T.snap_count, { n: x.named, runs: s.runs }))); ol.appendChild(li); });
    box.appendChild(ol);
    box.appendChild(el("p", "note", fmt(T.snap_cap, { runs: s.runs, questions: s.questions, date: s.date })));
    if (s.other_language) box.appendChild(el("p", "note", fmt(T.snap_lang, { lang: D.langs[s.other_language] })));
    resEl.appendChild(box);
  }
  function mailBox(res) {
    var box = el("div", "mailbox"); box.appendChild(el("h2", null, T.mail_h)); box.appendChild(el("p", null, T.mail_p));
    var f = el("form", "mform"); f.noValidate = true;
    var l1 = el("label", null, T.mail_email), em = el("input"); em.type = "email"; em.name = "email"; em.autocomplete = "email"; em.required = true; l1.appendChild(em);
    var hp = el("input", "hp"); hp.type = "text"; hp.name = "website"; hp.tabIndex = -1; hp.autocomplete = "off"; hp.setAttribute("aria-hidden", "true");
    var l2 = el("label", "cons"), cb = el("input"); cb.type = "checkbox"; l2.appendChild(cb); l2.appendChild(el("span", null, T.mail_consent));
    var btn = el("button", "btn p", T.mail_go); btn.type = "submit"; var msg = el("p", "note"); msg.setAttribute("role", "status");
    f.appendChild(l1); f.appendChild(hp); f.appendChild(l2); f.appendChild(btn); f.appendChild(msg); box.appendChild(f);
    f.addEventListener("submit", function (e) {
      e.preventDefault(); if (!cb.checked || !em.value) { msg.textContent = T.mail_bad; return; }
      btn.disabled = true;
      post("/api/request", { email: em.value, website: hp.value, consent: true, url: $("f-url").value, lang: $("f-lang").value, country: $("f-country").value, niche: $("f-niche").value,
        summary: { pass: (res.summary || {}).pass, fail: (res.summary || {}).fail } }).then(function (r) {
        if (r.status === 200) { f.textContent = ""; f.appendChild(el("p", "ok", T.mail_done)); } else { msg.textContent = T.mail_bad; btn.disabled = false; }
      }).catch(function () { msg.textContent = T.e_net; btn.disabled = false; });
    });
    resEl.appendChild(box);
  }
  function fail(msg) { statusEl.textContent = msg; statusEl.className = "status err"; resEl.hidden = true; }
  form.addEventListener("submit", function (e) {
    e.preventDefault(); if (busy) return;
    var url = $("f-url").value.trim(); if (!url) { fail(T.e_bad_url); $("f-url").focus(); return; }
    busy = true; $("f-go").disabled = true; statusEl.className = "status"; statusEl.textContent = T.busy;
    post("/api/check", { url: url, lang: $("f-lang").value, country: $("f-country").value, niche: $("f-niche").value }).then(function (r) {
      var b = r.body; statusEl.textContent = "";
      if (r.status === 200 && b.ok) {
        if (b.error) { fail(fmt(T["e_" + b.error] || T.e_net, { status: b.home_status })); return; }
        render(b);
      } else fail(T["e_" + b.error] || T.e_net);
    }).catch(function () { fail(T.e_net); }).then(function () { busy = false; $("f-go").disabled = false; });
  });
})();
