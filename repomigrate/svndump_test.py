from .svndump import dump_svndump, parse_svndump

def test_roundtrip_raw():
    with open("clam.svn", "rb") as f:
        original = f.read()
    dump = parse_svndump(original)
    assert dump_svndump(dump) == original
    assert len(dump.revisions) == 15457
    assert dump.revisions[-1].number == 15457 -1
    assert len(dump.revisions[-1].nodes) == 1
    assert len(dump.revisions[0].nodes) == 0
    assert dump.revisions[-1].nodes[0].content.startswith(
        b'/*\n * Copyright (c) 2001-2004 MUSIC TECHNOLOGY'
    )
    assert dump.revisions[-1].nodes[0].content.endswith(
        b';\n\treturn true;\n}\n\n\n\n'
    )

