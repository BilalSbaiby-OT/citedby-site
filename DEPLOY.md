# citedby.eu hosting (RES-385)
The site is now one stdlib Python container (server.py): static pages plus the free check API. nginx.conf is gone.
Env: OPTIN_SECRET (>=32 random bytes), BASE_URL=https://citedby.eu, RESEND_API_KEY, MAIL_FROM="CitedBy <hello@citedby.eu>", INTERNAL_IPS (comma list, not counted in events). Optional: CHECK_PER_IP_HOUR=10, CHECK_PER_HOST_HOUR=4, REQ_PER_IP_HOUR=5, DAILY_CAP=20.
Run: container port 8080, volume at /data (check.db), mem limit 128m, read-only rootfs allowed (writes only under /data), Traefik routes citedby.eu as before.
Rollback: redeploy the previous (nginx) image from commit 341b7e6; /check then 404s, the landing is unchanged. /data holds the opt-in rows: export before deleting.
Test: OPTIN_SECRET=... python3 test_check.py (26 checks: SSRF, slow-read deadline, confirm on POST, mail cap). Pages are generated: python3 tools/build_pages.py. Snapshots: python3 tools/build_snapshots.py <cells dir>.
Operator queue (mini-audit): python3 tools/queue.py next --db /data/check.db  -> prints today's batch (max DAILY_CAP, oldest confirmed first) and marks them released.
Metrics: sqlite3 /data/check.db "select day,lang,type,n from event_count order by day desc".
Mini-audit promise: "within 2 working days". Owner: Venture Builder, routine "CitedBy mini-audit queue" (id 430cf5fe-37b2-448f-b825-1928727a5a7a, weekdays 09:30 Madrid). Needs read access to /data/check.db for queue.py.
Health and deploy id (RES-772, STACK-STANDARD O1): GET /health -> {"status","db","time"}, 200 or 503 (fresh read-only SQLite read of /data/check.db). GET /deploy-id -> {"deploy_id": "<sha>"}. Build with: docker build --build-arg GIT_SHA=$(git rev-parse --short=12 HEAD) . (or set env DEPLOY_ID). Without the build arg the id reads "unknown": every deploy must pass it.
