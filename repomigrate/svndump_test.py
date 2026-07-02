from .svndump import dump_svndump, parse_svndump

def test_roundtrip_raw():
    with open("clam.svn", "rb") as f:
        original = f.read()
    dump = parse_svndump(original)
    assert dump_svndump(dump) == original
    assert len(dump.revisions) == 15457


