import sys
from pathlib import Path
from collections import OrderedDict
from consolemsg import step, warn, success
import typer
from .svndump import parse_svndump, dump_svndump, SvnNode
from os.path import commonprefix


def preprocess(
    input_dump_file: Path = typer.Argument(..., help="Path to the input SVN dump file"),
    output_dump_file: Path = typer.Argument(..., help="Path to the output SVN dump file"),
):
    """Preprocess SVN dump: fix GraphicsViewNetworkCanvas branch paths."""

    step(f"Reading {input_dump_file}")
    data = input_dump_file.read_bytes()
    dump = parse_svndump(data)

    step("Make GraphicsViewNetworkCanvas have directory")
    rev = dump.revisions[13369]
    rev.nodes[0].fields[b"Node-copyfrom-path"] = b"trunk"
    for rev in dump.revisions[13370:]:
        # Any reference to the branch should include NetworkEditor/
        for node in rev.nodes:
            node.fields[b"Node-path"] = node.fields[b"Node-path"].replace(
                b"branches/GraphicsViewNetworkCanvas/",
                b"branches/GraphicsViewNetworkCanvas/NetworkEditor/",
            )

    #step("Analyzing partial tags/branches")
    #for rev_num, rev in enumerate(dump.revisions):
    #    log = rev.header
    #    if b"This commit was manufactured" not in log:
    #        continue
    #    
    #    success(rev_num)
    #    partial_tag_analysis(rev, rev_num)
        
    step("Completting tags and branches")
    for line in Path('tags-and-branches.tsv').read_bytes().splitlines():
        rev_number, label, rev_number_src, label_src, *projects = line.split(b'\t')
        if rev_number.startswith(b"#"): continue
        rev = dump.revisions[int(rev_number.decode())]
        #print(rev.nodes[0])
        rev.nodes = [
            SvnNode(
                fields=OrderedDict([
                    (b'Node-path', label),
                    (b'Node-kind', b'dir'),
                    (b'Node-action', b'add'),
                    (b'Node-copyfrom-rev', rev_number_src),
                    (b'Node-copyfrom-path', label_src),
                ]),
                properties=None,
                content=None,
                raw=b'\n',
            )
        ]


    step(f"Writing {output_dump_file}")
    output_dump_file.write_bytes(dump.dump())
        
        





def partial_tag_analysis(rev, rev_num):
    """Turns a partial branch or tag into a full tree branch or tag"""
    if rev.nodes[0].fields[b"Node-path"].startswith(b"branches/unlabeled"):
        warn("Ignoring Unlabeled")
        return
    copy_revs = [
        int(copy_rev.decode())
        for copy_rev in [
            node.fields.get(b'Node-copyfrom-rev', None)
            for node in rev.nodes 
        ]
        if copy_rev is not None
    ]
    source_rev_num = max(copy_revs)
    #for node in rev.nodes:
    #    success(f"  {node.fields}, {node.properties}")
    targets = [
        path
        for path in [
            node.fields.get(b'Node-path', None)
            for node in rev.nodes 
        ]
        if path is not None
    ]
    target = commonprefix(targets)
    sources = [
        path
        for path in [
            node.fields.get(b'Node-copyfrom-path', None)
            for node in rev.nodes 
            if node.fields.get(b'Node-copyfrom-rev', None) == str(source_rev_num).encode()
        ]
        if path is not None
        #and not path.startswith(b"branches/GNU")
        #and not path.startswith(b"branches/INITIAL")
        #and not path.startswith(b"branches/imosquera")
    ]
    source = commonprefix(sources) or b""
    print(f"{rev_num}\t{target.decode()}\t{source_rev_num}\t{source.decode() or '??'}")
    assert target, f"Mixed targets {targets}"
    if not source:
        warn(f"Mixed origins")
        print(f"{sources and b'\n'.join(sources).decode()}")
        return

    





