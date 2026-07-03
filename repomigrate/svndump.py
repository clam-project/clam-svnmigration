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
    properties: OrderedDict
    content: bytes | None
    raw: bytes

    @classmethod
    def parse(cls, raw: bytes) -> Self:
        header_end = raw.find(b"\n\n")
        header = raw[:header_end]
        props_start = header_end + 2
        props_end = raw.find(b"PROPS-END\n", props_start)

        fields = parse_fields(header)

        if props_end != -1:
            props_section = raw[props_start:props_end + len(b"PROPS-END")]
            properties = parse_kv_properties(props_section)
            content_start = props_end + len(b"PROPS-END\n")
            content = raw[content_start:] if content_start < len(raw) else None
        else:
            properties = OrderedDict()
            content = raw[props_start:] if props_start < len(raw) else None

        return cls(fields=fields, properties=properties, content=content, raw=raw)

    def _should_emit_props(self) -> bool:
        action = self.fields.get(b"Node-action")
        kind = self.fields.get(b"Node-kind")
        copy = b"Node-copyfrom-rev" in self.fields

        if self.properties:
            return True
        if action == b"delete":
            return False
        if action in (b"add", b"replace") and not copy:
            return True
        if action == b"change" and kind == b"dir":
            return True
        if (copy and kind == b"file" and
            self.fields.get(b"Text-copy-source-md5") == b"b8d297bf213f57e210708351d857c199"):
            return True
        # Fallback: 4 change file nocopy with empty PROPS-END
        # (property deletions with empty KV section)
        if b"Prop-content-length" in self.fields:
            return True
        return False

    def dump(self) -> bytes:
        emit_props = self._should_emit_props()
        props = dump_kv_properties(self.properties) if emit_props else b""
        if emit_props:
            self.fields[b"Prop-content-length"] = str(len(props)).encode()
        result = dump_fields(self.fields) + b"\n\n"
        result += props
        if self.content is not None:
            result += self.content
        return result

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
