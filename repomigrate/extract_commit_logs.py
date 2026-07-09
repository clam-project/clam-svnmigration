import sys
from pathlib import Path
from collections import OrderedDict
from consolemsg import step, warn, success
import typer
from .svndump import parse_svndump, dump_svndump, SvnNode


def extract_commit_logs(
    input_dump_file: Path = typer.Argument(..., help="Path to the input SVN dump file"),
    output_dir: Path = typer.Argument("generated", help="Path to the output SVN dump file"),
):
    """Given an svn dump and a tsv with tagged removed.
    It dumps a set of files generated/log-NNNN.txt with the log message.
    The goal is to be able to recover those
    """
    empty_commits_tsv = Path("emptycommits.tsv")

    step(f"Reading {input_dump_file}")
    data = input_dump_file.read_bytes()
    dump = parse_svndump(data)


    for line in empty_commits_tsv.read_text().splitlines()[1:]:
        if not line: continue
        if line.startswith("#"): continue
        tagged, removed = line.split("\t")
        for rev_number in tagged, removed:
            rev_number = int(rev_number)
            rev = dump.revisions[rev_number]
            step(f"{rev_number}")
            success(f"{rev.properties}")
            (output_dir/f"log-{rev_number}.txt").write_bytes(rev.properties[b"svn:log"])



