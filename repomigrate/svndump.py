from dataclasses import dataclass
from typing import Self

REVISION_MARKER = b"Revision-number: "
NODE_MARKER = b"Node-path: "

@dataclass
class SvnNode:
    raw: bytes

    def dump(self) -> bytes:
        return self.raw

@dataclass
class SvnRevision:
    number: int
    header: bytes
    nodes: list[SvnNode]

    @classmethod
    def parse(cls, raw: bytes) -> Self:
        newline = raw.find(b"\n")
        rev_num = int(raw[len(REVISION_MARKER):newline])

        parts = raw.split(NODE_MARKER)
        header = parts[0]
        nodes = [SvnNode(raw=NODE_MARKER + part) for part in parts[1:]]

        return cls(number=rev_num, header=header, nodes=nodes)

    def dump(self) -> bytes:
        return self.header + b"".join(node.dump() for node in self.nodes)

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
        return self.header + b"".join(rev.dump() for rev in self.revisions)


def parse_svndump(data: bytes) -> SvnDump:
    return SvnDump.parse(data)

def dump_svndump(dump: SvnDump) -> bytes:
    return dump.dump()
