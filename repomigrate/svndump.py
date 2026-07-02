from dataclasses import dataclass

@dataclass
class SvnDump:
    raw: bytes


def parse_svndump(data: bytes) -> bytes:
    return SvnDump(raw=data)

def dump_svndump(dump: SvnDump) -> bytes:
    return dump.raw



