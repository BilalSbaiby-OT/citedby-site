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
    assert b"@" not in analytics.TAG and b"?" not in analytics.TAG.replace(b"riq-a.js?v=1", b"")
