"""A module imported by server.py that the Dockerfile does not COPY crash-loops the container (RES-1071, 17 Oct: analytics.py)."""
import os, re

HERE = os.path.dirname(os.path.abspath(__file__))


def test_every_local_import_is_copied():
    copied = set()
    for line in open(os.path.join(HERE, "Dockerfile")):
        if line.startswith("COPY ") and not line.split()[1].endswith("/"):
            copied.update(line.split()[1:-1])
    src = open(os.path.join(HERE, "server.py")).read()
    mods = {m.strip() for line in re.findall(r"^import (.+)$", src, re.M) for m in line.split(",")}
    local = {m + ".py" for m in mods if os.path.exists(os.path.join(HERE, m + ".py"))}
    assert local <= copied, sorted(local - copied)
