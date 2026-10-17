import analytics

PAGE = b"<html><head><title>x</title></head><body></body></html>"


def test_inject_adds_tag_once_before_head_end():
    out = analytics.inject(PAGE)
    assert out.count(b'src="/riq-a.js') == 1 and out.index(b"riq-a.js") < out.index(b"</head>")
    assert analytics.inject(out) == out


def test_inject_leaves_fragments_alone_and_off_switch_works(monkeypatch):
    assert analytics.inject(b"<p>no head</p>") == b"<p>no head</p>"
    monkeypatch.setattr(analytics, "KEY", "")
    assert analytics.inject(PAGE) == PAGE


def test_no_query_or_email_in_tag():
    assert b"@" not in analytics.TAG and b"?" not in analytics.TAG.replace(b"riq-a.js?v=3", b"")


def test_relay_ignores_empty_and_oversize_bodies(monkeypatch):
    calls = []
    monkeypatch.setattr(analytics.threading, "Thread", lambda **k: type("T", (), {"start": lambda s: calls.append(1)})())
    analytics.relay(b"", "1.2.3.4", "ua")
    analytics.relay(b"x" * 9000, "1.2.3.4", "ua")
    assert calls == []
    analytics.relay(b'{"event":"x"}', "1.2.3.4", "ua")
    assert calls == [1]
