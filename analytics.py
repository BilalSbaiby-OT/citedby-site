"""RES-1071: cookieless PostHog (EU). The public/riq-a.js client sets no cookies and uses no storage; the project key is public by design.
POSTHOG_KEY="" switches the tag off (rollback without a redeploy of code)."""
import os, threading, urllib.request

KEY = os.environ.get("POSTHOG_KEY", "phc_r2uexPGqx2dCYjsFKnevTB8rf8Ez9B6twoMXcfFceHzD")
TAG = ('<script src="/riq-a.js?v=3" data-key="%s" data-site="citedby" data-endpoint="/riq-e" defer></script>' % KEY).encode()


def inject(body):
    """Add the tag before </head> of an HTML page; pages without a head, or with the tag already, pass through."""
    if not KEY or TAG in body or b"</head>" not in body:
        return body
    return body.replace(b"</head>", TAG + b"</head>", 1)


UPSTREAM = "https://eu.i.posthog.com/i/v0/e/"


def relay(raw, ip, ua):
    """Forward one capture body to PostHog in the background (the page never waits). The client IP goes in X-Forwarded-For for PostHog's daily cookieless hash; nothing is stored here."""
    def go():
        try:
            req = urllib.request.Request(UPSTREAM, raw, {"Content-Type": "text/plain", "X-Forwarded-For": ip, "User-Agent": ua or "riq-relay"}, method="POST")
            urllib.request.urlopen(req, timeout=5).read()
        except Exception:
            pass
    if KEY and 0 < len(raw) <= 8192:
        threading.Thread(target=go, daemon=True).start()
