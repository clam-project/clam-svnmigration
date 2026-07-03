import sys
from pathlib import Path
from consolemsg import step
import typer
from .svndump import parse_svndump, dump_svndump


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

    step(f"Writing {output_dump_file}")
    output_dump_file.write_bytes(dump.dump())

