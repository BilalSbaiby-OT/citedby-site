"""SSRF-safe HTTP fetcher for the CitedBy check. Standard library only.

Rules: http/https only, ports 80/443 only, no userinfo, every resolved address must be globally routable,
the socket connects to the address we validated (no second DNS lookup, so no rebinding), every redirect hop is
re-validated, bodies and wall-clock time are capped.
"""
import http.client, ipaddress, os, socket, ssl, threading, time
from urllib.parse import urlsplit, urljoin

UA = "CitedByCheck/1.0 (+https://citedby.eu/check)"
MAX_BODY = 1_500_000
MAX_REDIRECTS = 4
CTX = ssl.create_default_context()
CTX.post_handshake_auth = True  # same ClientHello as http.client's HTTPSConnection; Shopify answers 429 to the bare one from OpenSSL 3.5 (prod)


class Blocked(Exception):
    """The URL is not allowed (scheme, port, userinfo, private or unresolvable address)."""


EMBEDDED_V4 = [ipaddress.ip_network(n) for n in ("64:ff9b::/96", "64:ff9b:1::/48", "::/96", "2002::/16", "2001::/32")]  # IPv6 forms that carry an IPv4 address


def addr_ok(ip):
    a = ipaddress.ip_address(ip)
    if getattr(a, "ipv4_mapped", None):
        a = a.ipv4_mapped
    if a.version == 6 and any(a in n for n in EMBEDDED_V4):
        return False
    return a.is_global and not a.is_multicast


def resolve_public(host, port):
    """Return one validated address for host; raise Blocked if any address is non-public."""
    try:
        ipaddress.ip_address(host.strip("[]"))
        infos = [(None, None, None, None, (host.strip("[]"), port))]
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except socket.gaierror:
            raise Blocked("dns")
    ips = [i[4][0] for i in infos]
    if not ips or not all(addr_ok(ip) for ip in ips):
        raise Blocked("private_address")
    return ips[0]


def parse(url):
    if len(url) > 2048:
        raise Blocked("url_too_long")
    u = urlsplit(url)
    if u.scheme not in ("http", "https"):
        raise Blocked("scheme")
    if u.username or u.password:
        raise Blocked("userinfo")
    if not u.hostname:
        raise Blocked("host")
    port = u.port or (443 if u.scheme == "https" else 80)
    if port not in (80, 443):
        raise Blocked("port")
    return u, port


class _Conn(http.client.HTTPConnection):
    def __init__(self, host, ip, port, timeout, tls):
        super().__init__(host, port, timeout=timeout)
        self._ip, self._tls = ip, tls
        self.dead = False  # set by the deadline timer; connect() honours it if the timer fired mid-connect

    def connect(self):
        self.sock = socket.create_connection((self._ip, self.port), self.timeout)
        self.raw = socket.socket(fileno=os.dup(self.sock.fileno()))  # own fd for the deadline timer: http.client closes self.sock on 'Connection: close' responses, shutdown() on a dup still cuts the connection
        if self.dead:  # the timer fired while we were connecting and found no socket to cut
            self.raw.shutdown(socket.SHUT_RDWR)
        if self._tls:
            self.sock = CTX.wrap_socket(self.sock, server_hostname=self.host)


def fetch(url, deadline=None, max_body=MAX_BODY, accept_lang="en"):
    """GET url following validated redirects. Returns dict(status, url, body, error). Never raises on network errors.
    Raises Blocked only for the first URL; a blocked redirect hop returns error='blocked:<why>'."""
    deadline = deadline or time.time() + 10
    cur = url
    for hop in range(MAX_REDIRECTS + 1):
        try:
            u, port = parse(cur)
            ip = resolve_public(u.hostname, port)
        except Blocked as e:
            if hop == 0:
                raise
            return {"status": 0, "url": cur, "body": "", "error": "blocked:" + str(e)}
        left = deadline - time.time()
        if left <= 0:
            return {"status": 0, "url": cur, "body": "", "error": "timeout"}
        c = _Conn(u.hostname, ip, port, min(left, 8), u.scheme == "https")
        c.raw = None
        def cut():  # hard deadline in every phase (connect, TLS, status line, headers, body): shutting the TCP socket unblocks any recv
            c.dead = True
            try:
                c.raw.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
        timer = threading.Timer(max(0, deadline - time.time()), cut)
        timer.daemon = True
        timer.start()
        try:
            path = (u.path or "/") + ("?" + u.query if u.query else "")
            c.request("GET", path, headers={"Host": u.netloc.rsplit("@", 1)[-1], "User-Agent": UA, "Accept-Language": accept_lang,
                                            "Accept": "text/html,text/plain,application/json;q=0.9,*/*;q=0.5", "Connection": "close"})
            r = c.getresponse()
            if r.status in (301, 302, 303, 307, 308) and r.getheader("Location"):
                cur = urljoin(cur, r.getheader("Location"))
                c.close()
                continue
            chunks, got = [], 0
            while got < max_body:  # the deadline holds while the body is read, so a trickling server cannot pin a slot
                left = deadline - time.time()
                if left <= 0:
                    c.close()
                    return {"status": 0, "url": cur, "body": "", "error": "timeout"}
                part = r.read1(min(65536, max_body - got))
                if not part:
                    break
                chunks.append(part)
                got += len(part)
            if time.time() >= deadline:  # the timer cut the connection mid-body: a partial page is not a result
                return {"status": 0, "url": cur, "body": "", "error": "timeout"}
            c.close()
            return {"status": r.status, "url": cur, "body": b"".join(chunks).decode("utf-8", "replace"), "error": ""}
        except (TimeoutError, socket.timeout):
            return {"status": 0, "url": cur, "body": "", "error": "timeout"}
        except Exception as e:  # network errors are data, not crashes
            return {"status": 0, "url": cur, "body": "", "error": "timeout" if time.time() >= deadline - 0.05 else type(e).__name__}
        finally:
            timer.cancel()
            c.close()
            if c.raw:
                c.raw.close()
    return {"status": 0, "url": cur, "body": "", "error": "too_many_redirects"}
