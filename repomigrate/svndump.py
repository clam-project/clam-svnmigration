from collections import OrderedDict
from dataclasses import dataclass
from typing import Self
import hashlib

def md5(data: bytes) -> bytes:
    return hashlib.md5(data).hexdigest().encode()

def sha1(data: bytes) -> bytes:
    return hashlib.sha1(data).hexdigest().encode()

REVISION_MARKER = b"Revision-number: "
NODE_MARKER = b"Node-path: "

def binaryLength(content):
    if content is None: return None
    return str(len(content)).encode()

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

def dump_kv_properties(properties: OrderedDict | None) -> bytes:
    if properties is None: return None
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
        if content_length is not None:

            content = remaining[:-2]
            remaining = remaining[-2:]

            assert binaryLength(content) == content_length, (
                f"{content_length.decode()} vs {len(content.decode())}"
            )

            stored_md5 = fields.get(b"Text-content-md5")
            if stored_md5 is not None:
                assert md5(content) == stored_md5, (
                    f"md5: {md5(content).decode()} != {stored_md5.decode()}"
                )

            stored_sha1 = fields.get(b"Text-content-sha1")
            if stored_sha1 is not None:
                assert sha1(content) == stored_sha1, (
                    f"sha1: {sha1(content).decode()} != {stored_sha1.decode()}"
                )

            assert remaining == b"\n\n", (
                f"remaining: <{remaining}>"
            )
        else:
            # TODO: We should be able to predict which trailing goes
            assert remaining in (b"\n\n", b"\n", b""), (
                f"header: <{header}>\nremaining: <{remaining}>"
            )
        stored_full_length = fields.get(b"Content-length", None)
        computed_full_length = None
        if content is not None or properties is not None:
            computed_full_length = binaryLength(
                (content or b"") +
                (properties_chunk if properties is not None else b"")
            )
        assert stored_full_length == computed_full_length, (
            f"full length {stored_full_length} vs {computed_full_length}"
        )

        return cls(fields=fields, properties=properties, content=content, raw=remaining)

    def dump(self) -> bytes:
        props = dump_kv_properties(self.properties) or b""
        content = self.content or b""

        if self.properties != None:
            self.fields[b"Prop-content-length"] = binaryLength(props)

        if self.content != None:
            self.fields[b"Text-content-length"] = binaryLength(content)

        if self.content != None or self.properties != None:
            self.fields[b"Content-length"] = binaryLength(content + props)

        result = dump_fields(self.fields) + b"\n\n"
        result += props
        result += content

        # TODO: We shoudl be able to predict which trailing goes
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
