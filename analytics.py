"""RES-1071: cookieless PostHog (EU). The public/riq-a.js client sets no cookies and uses no storage; the project key is public by design.
POSTHOG_KEY="" switches the tag off (rollback without a redeploy of code)."""
import os

KEY = os.environ.get("POSTHOG_KEY", "phc_r2uexPGqx2dCYjsFKnevTB8rf8Ez9B6twoMXcfFceHzD")
TAG = ('<script src="/riq-a.js?v=1" data-key="%s" data-site="citedby" defer></script>' % KEY).encode()


def inject(body):
    """Add the tag before </head> of an HTML page; pages without a head, or with the tag already, pass through."""
    if not KEY or TAG in body or b"</head>" not in body:
        return body
    return body.replace(b"</head>", TAG + b"</head>", 1)
