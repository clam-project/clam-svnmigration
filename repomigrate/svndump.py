from dataclasses import dataclass

MARKER = b"Revision-number: "

@dataclass
class SvnRevision:
    number: int
    raw: bytes

@dataclass
class SvnDump:
    header: bytes
    revisions: list[SvnRevision]


def parse_svndump(data: bytes) -> SvnDump:
    positions = []
    start = 0
    while True:
        pos = data.find(MARKER, start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + 1

    header = data[:positions[0]]
    revisions = []
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(data)
        rev_raw = data[pos:end]
        newline = rev_raw.find(b"\n")
        rev_num = int(rev_raw[len(MARKER):newline])
        revisions.append(SvnRevision(number=rev_num, raw=rev_raw))

    return SvnDump(header=header, revisions=revisions)

def dump_svndump(dump: SvnDump) -> bytes:
    return dump.header + b"".join(rev.raw for rev in dump.revisions)
