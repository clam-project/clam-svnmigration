from dataclasses import dataclass
from typing import Self

REVISION_MARKER = b"Revision-number: "

@dataclass
class SvnRevision:
    number: int
    raw: bytes

    @classmethod
    def parse(cls, raw: bytes) -> Self:
        newline = raw.find(b"\n")
        rev_num = int(raw[len(REVISION_MARKER):newline])
        return cls(number=rev_num, raw=raw)

@dataclass
class SvnDump:
    header: bytes
    revisions: list[SvnRevision]

    @classmethod
    def parse(cls, data: bytes) -> Self:
        parts = data.split(REVISION_MARKER)
        header = parts[0]
        revisions = [
            SvnRevision.parse(REVISION_MARKER + part)
            for part in parts[1:]
        ]
        return cls(header=header, revisions=revisions)

    def dump(self) -> bytes:
        return self.header + b"".join(rev.raw for rev in self.revisions)


def parse_svndump(data: bytes) -> SvnDump:
    return SvnDump.parse(data)

def dump_svndump(dump: SvnDump) -> bytes:
    return dump.dump()
