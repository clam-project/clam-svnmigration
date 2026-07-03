from collections import OrderedDict
from dataclasses import dataclass
from typing import Self

REVISION_MARKER = b"Revision-number: "
NODE_MARKER = b"Node-path: "

def parse_fields(header: bytes) -> OrderedDict:
    fields = OrderedDict()
    for line in header.split(b"\n"):
        key, value = line.split(b": ", 1)
        fields[key] = value
    return fields

def parse_kv_properties(data: bytes) -> OrderedDict:
    properties = OrderedDict()
    pos = 0
    while True:
        k_pos = data.find(b"K ", pos)
        if k_pos == -1:
            break
        newline = data.find(b"\n", k_pos)
        k_len = int(data[k_pos+2:newline])
        key = data[newline+1:newline+1+k_len]
        v_pos = newline + 1 + k_len + 1
        v_newline = data.find(b"\n", v_pos)
        v_len = int(data[v_pos+2:v_newline])
        value = data[v_newline+1:v_newline+1+v_len]
        properties[key] = value
        pos = v_newline + 1 + v_len + 1
    return properties

def dump_fields(fields: OrderedDict) -> bytes:
    return b"\n".join(k + b": " + v for k, v in fields.items())

def dump_kv_properties(properties: OrderedDict) -> bytes:
    props = b""
    for k, v in properties.items():
        props += b"K " + str(len(k)).encode() + b"\n" + k + b"\n"
        props += b"V " + str(len(v)).encode() + b"\n" + v + b"\n"
    props += b"PROPS-END\n"
    return props

@dataclass
class SvnNode:
    fields: OrderedDict
    properties: OrderedDict | None
    content: bytes | None
    raw: bytes

    @classmethod
    def parse(cls, raw: bytes) -> Self:
        PROPS_END = b"PROPS-END\n"

        header, remaining = raw.split(b"\n\n", 1)
        fields = parse_fields(header)

        properties = None
        if PROPS_END in remaining:
            props_length = int(fields[b"Prop-content-length"].decode())
            properties_chunk, remaining = remaining.split(PROPS_END, 1)
            properties_chunk += PROPS_END
            assert len(properties_chunk) == props_length, (
                f"{props_length} {len(properties_chunk)}"
            )
            properties = parse_kv_properties(properties_chunk+PROPS_END)
        content = None
        content_length = fields.get(b'Text-content-length', None)
        content_length = content_length and int(content_length.decode())
        if content_length is not None:
            content = remaining[:-2]
            remaining = remaining[-2:]
            assert len(content) == content_length, (
                f"{content_length} vs {len(content)}"
            )
            assert remaining == b"\n\n", (
                f"remaining: <{remaining}>"
            )
        else:
            assert remaining == b"\n\n" or remaining == b"\n" or remaining == b"", (
                f"header: <{header}>\nremaining: <{remaining}>"
            )

        return cls(fields=fields, properties=properties, content=content, raw=remaining)

    def dump(self) -> bytes:
        props = b""
        if self.properties != None:
            props = dump_kv_properties(self.properties)
            self.fields[b"Prop-content-length"] = str(len(props)).encode()
        result = dump_fields(self.fields) + b"\n\n"
        result += props
        if self.content is not None:
            result += self.content
        return result + self.raw

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
        nodes = [SvnNode.parse(NODE_MARKER + part) for part in parts[1:]]

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
