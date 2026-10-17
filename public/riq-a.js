/* riq-a.js: cookieless PostHog (EU) client, RES-1071. One copy per site, served from the site's own origin.
   No cookies, no localStorage/sessionStorage: PostHog's server-side cookieless hash ties a visitor's events for one day.
   Honours Do Not Track and Global Privacy Control. Sends the path only (never the query string) and never an email or name.
   Install: <script src="/riq-a.js" data-key="phc_..." data-site="resaleiq" defer></script>
   Events: window.riq("check_started", {kind: "..."}). Allowed names are listed in EVENTS. */
(function () {
  var s = document.currentScript;
  var key = s && s.getAttribute("data-key");
  var site = (s && s.getAttribute("data-site")) || location.hostname;
  var internal = false;
  try { internal = localStorage.getItem("riq_internal") === "1" || /(?:^|;\s*)riq_internal=1/.test(document.cookie); } catch (e) {}  // team browsers (read only)
  var off = !key || internal || navigator.doNotTrack === "1" || window.doNotTrack === "1" || navigator.msDoNotTrack === "1" || navigator.globalPrivacyControl === true;
  var EVENTS = { check_started: 1, check_finished: 1, signup: 1, checkout_started: 1, paid: 1, mock_started: 1, mock_finished: 1, checkout_completed: 1, cta_click: 1 };
  var URL_ = (s && s.getAttribute("data-endpoint")) || "https://eu.i.posthog.com/i/v0/e/";  // same-origin relay (/riq-e) so blockers do not drop it and CSP stays connect-src self
  function base() {
    var q = new URLSearchParams(location.search), p = {
      $cookieless_mode: true, $raw_user_agent: navigator.userAgent, $lib: "riq-a", $lib_version: "1",
      $host: location.host, $pathname: location.pathname, $current_url: location.origin + location.pathname,
      $screen_width: screen.width, $screen_height: screen.height, $viewport_width: innerWidth, $viewport_height: innerHeight,
      $timezone: (Intl.DateTimeFormat().resolvedOptions() || {}).timeZone, $language: navigator.language, site: site
    };
    ["utm_source", "utm_medium", "utm_campaign", "utm_content", "ref"].forEach(function (k) { if (q.get(k)) p[k] = String(q.get(k)).slice(0, 80); });
    if (document.referrer) { try { var r = new URL(document.referrer); p.$referrer = r.origin + r.pathname; p.$referring_domain = r.host; } catch (e) {} }
    return p;
  }
  function send(event, extra) {
    if (off) return;
    var p = base();
    if (extra) for (var k in extra) if (Object.prototype.hasOwnProperty.call(extra, k)) p[k] = typeof extra[k] === "string" ? extra[k].slice(0, 80) : extra[k];
    try {
      fetch(URL_, { method: "POST", keepalive: true, credentials: "omit",
        body: JSON.stringify({ api_key: key, event: event, distinct_id: "$posthog_cookieless", properties: p, timestamp: new Date().toISOString() }) }).catch(function () {});
    } catch (e) {}
  }
  window.riq = function (name, props) { if (EVENTS[name]) send(name, props); };
  send("$pageview");
  // single-page apps: one pageview per client-side route change
  var last = location.pathname;
  function route() { if (location.pathname !== last) { last = location.pathname; send("$pageview"); } }
  ["pushState", "replaceState"].forEach(function (m) { var o = history[m]; history[m] = function () { var r = o.apply(this, arguments); route(); return r; }; });
  addEventListener("popstate", route);
  // primary calls to action: mark the button with data-cta="primary" (optional data-cta-id="hero"); one delegated listener, no query text or link targets sent
  document.addEventListener("click", function (e) {
    var el = e.target && e.target.closest && e.target.closest("[data-cta]");
    if (el) send("cta_click", { cta: el.getAttribute("data-cta"), cta_id: el.getAttribute("data-cta-id") || undefined });
  }, true);
  // payment links and Stripe buy buttons: the click is the checkout start
  document.addEventListener("click", function (e) {
    var a = e.target && e.target.closest && e.target.closest("a[href]");
    if (a && /^https:\/\/(buy|checkout)\.stripe\.com\//.test(a.href)) send("checkout_started", { via: "payment_link" });
  }, true);
  // fetch rules per site: [method, path regex, event, optional JSON status that must match, 1 = fire on the request]
  var RULES = {
    citedby: [["POST", /^\/api\/(snapshot|check)$/, "check_started", 0, 1], ["POST", /^\/api\/check$/, "check_finished"], ["GET", /^\/api\/snapshot\/[\w-]+$/, "check_finished", "done"],
              ["POST", /^\/api\/(account\/link|request)$/, "signup"], ["POST", /^\/api\/(order|checkout)$/, "checkout_started", 0, 1]],
    hexaciv: [["POST", /^\/api\/mock\/start$/, "mock_started"], ["POST", /^\/api\/mock\/\d+\/submit$/, "mock_finished"], ["POST", /^\/api\/checkout$/, "checkout_started"]],
    civiqpass: [["POST", /^\/api\/mock\/start$/, "mock_started"], ["POST", /^\/api\/mock\/\d+\/submit$/, "mock_finished"]]
  }[site];
  if (RULES && window.fetch) {
    var of = window.fetch, done = {};
    window.fetch = function (input, init) {
      var p = of.apply(this, arguments);
      try {
        var u = new URL(typeof input === "string" ? input : input.url, location.href), m = ((init && init.method) || (input && input.method) || "GET").toUpperCase();
        if (u.origin === location.origin) RULES.forEach(function (r) {
          if (r[0] !== m || !r[1].test(u.pathname)) return;
          if (r[4]) return send(r[2]);  // fires on the request, not on the answer
          p.then(function (res) {
            if (!res.ok) return;
            if (!r[3]) return send(r[2]);
            res.clone().json().then(function (j) { if (j && j.status === r[3] && !done[u.pathname]) { done[u.pathname] = 1; send(r[2]); } }).catch(function () {});
          }).catch(function () {});
        });
      } catch (e) {}
      return p;
    };
  }
})();
