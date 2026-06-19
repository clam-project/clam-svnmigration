import subprocess
import re
from pathlib import Path

import typer
from consolemsg import step, warn, success

app = typer.Typer(
    help="SVN to Git repository migration tool",
    invoke_without_command=True,
)


@app.callback()
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def load_dump(
    dump_file: Path = typer.Argument(..., help="Path to SVN dump file"),
    repo_dir: Path = typer.Option("./svn_repo_loaded", help="Local repository directory"),
):
    """Load an SVN dump into a local repository."""
    step("Creating local repository at {}", repo_dir)
    subprocess.run(["svnadmin", "create", str(repo_dir)], check=True)

    step("Loading dump from {}", dump_file)
    with open(dump_file, "rb") as f:
        subprocess.run(["svnadmin", "load", str(repo_dir)], stdin=f, check=True)

    step("Repository loaded at {}", repo_dir)


def capture(*args):
    return subprocess.run(
        *args, 
        capture_output=True,
        text=True,
        check=True,
    )

def svnls(repo_dir, path):
    return [
        file.strip().strip("/")
        for file in capture(
            ["svnlook", "tree", str(repo_dir), path, "-N", "--full-paths"],
        ).tdout.strip().split("\n")
        if len(file.strip()) > len(path) +1
    ]

def svn_copy_source(repo_dir, path):
    """Get copy source path, copyfrom revision, and creation revision."""
    result = capture(
        ["svnlook", "history", str(repo_dir), path]
    )
    lines = [
        l for l in result.stdout.strip().split("\n")
        if l.strip()
        and not l.startswith("REVISION")
        and not l.startswith("---")
    ]
    previous_revision = None
    for line in lines:
        parts = line.split()
        revision = int(parts[0])
        path_at_rev = parts[1].strip("/")
        if path_at_rev != path:
            assert previous_revision is not None
            return path_at_rev, revision, previous_revision
        previous_revision = revision
    return None, None, int(lines[-1].split()[0])

def top_level_history(repo_dir):
    result = capture(
        ["svn", "log", "-v", repo_dir.absolute().as_uri()]
    )

    commits = re.split(r'^-{5,}$', result.stdout, flags=re.MULTILINE)

    #for commit in commits:
    #    print(commit)
    top_pattern = re.compile(r'^\s+[A-Z]\s+(/(trunk|branches/[^/]+|tags/[^/]+)/[^/]+/?\s*)\s', re.MULTILINE)
    for commit in commits:
        if not top_pattern.search(commit):
            continue
        commit_lines = commit.strip("\n").split("\n")
        print("--" * 40)
        print("\n".join(commit_lines[0:3]))
        is_message = False
        for change in commit_lines[3:]:
            if is_message:
                print(change)
            elif not change.strip():
                is_message = True
                print(change)
            elif top_pattern.search(change):
                print(f"\033[31m{change}\033[0m")
            else:
                print(change)

@app.command()
def top_level_changes(
    repo_dir: Path = typer.Argument(..., help="Path to loaded SVN repository"),
):
    top_level_history(repo_dir)


@app.command()
def analyze_svn(
    repo_dir: Path = typer.Argument(..., help="Path to loaded SVN repository"),
):
    """Analyze an SVN repository and list branches and tags."""
    elements = svnls(repo_dir, "branches") + svnls(repo_dir, "tags") 
    for element in elements + ["trunk"]:
        creation_revs = set()
        step(f"{element}")
        for subdir in svnls(repo_dir, element):
            source_path, source_revision, creation_rev = svn_copy_source(repo_dir, subdir)
            creation_revs.add(creation_rev)
            success(f"  {creation_rev} - {subdir.split('/')[-1]} <- {source_path} @ {source_revision}")
        if len(creation_revs) > 1:
            warn(f"  Mixed creation revisions: {sorted(creation_revs)}")

if __name__ == "__main__":
    app()
