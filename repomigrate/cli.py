import subprocess
import re
import tarfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import typer
import requests
from bs4 import BeautifulSoup
from consolemsg import step, warn, success, error

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
        ).stdout.strip().split("\n")
        if len(file.strip()) > len(path) +1
    ]

def revision_tree(repo_dir, path, revision):
    """Return list of files under path at given revision."""
    result = capture(
        ["svnlook", "tree", str(repo_dir),
         "--revision", str(revision), path, "--full-paths"]
    )
    return [
        line.removeprefix(path + "/")
        for line in result.stdout.strip().split("\n")
        if line and line != path + "/"
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
                pass
                #print(change)

@app.command()
def top_level_changes(
    repo_dir: Path = typer.Argument(..., help="Path to loaded SVN repository"),
):
    """Lists changes on the top level directories"""
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


@app.command()
def merge_script(
    repo_dir: Path = typer.Argument(..., help="Path to loaded SVN repository"),
):
    """Generate reposurgeon merge commands from copy-to-trunk operations."""
    REV_RE = re.compile(r'^r(\d+)')
    MERGE_COPY_RE = re.compile(
        r'^\s+A\s+/trunk/\S+\s+\(from\s+/branches/([^/]+):(\d+)\)',
        re.MULTILINE
    )

    result = capture(
        ["svn", "log", "-v", repo_dir.absolute().as_uri()]
    )
    commits = re.split(r'^-{5,}$', result.stdout, flags=re.MULTILINE)
    for commit in commits:
        rev_match = REV_RE.search(commit)
        if not rev_match:
            continue
        commit_rev = rev_match.group(1)
        copies = defaultdict(int)
        for m in MERGE_COPY_RE.finditer(commit):
            branch = m.group(1)
            source_rev = int(m.group(2))
            copies[branch] = max(copies[branch], source_rev)
        if not copies:
            continue
        if len(copies) > 1:
            warn(f"r{commit_rev}: multiple branches in same commit: {list(copies.keys())}")
        for branch, source_rev in copies.items():
            print(f"merge {commit_rev} : {source_rev}")

@dataclass
class SvnCommit:
    rev: str
    author: str
    date: str
    changes: list[str]
    message: str


def parse_svn_log(log_file: Path):
    """Parse a verbose SVN log file, yielding SvnCommit objects."""
    with open(log_file) as f:
        content = f.read()
    commits = re.split(r'^-{5,}$', content, flags=re.MULTILINE)
    for block in commits[::-1]:
        block = block.strip()
        if not block: continue
        if 'branches/unlabeled-' not in block: continue
        head, *message = block.split("\n\n", 1)
        message = message[0] if message else ""
        headlines = head.split("\n")
        revision, author, date, lines = headlines[0].split(" | ")
        changes = [s.strip() for s in headlines[2:]]

        yield SvnCommit(
            rev=revision,
            author=author,
            date=date,
            changes=changes,
            message=message,
        )


@app.command()
def unlabeled_history(
    log_file: Path = typer.Option("full_svn_log.txt", help="Path to full verbose SVN log file"),
    repo_dir: Path = typer.Option("./svn_repo_loaded", help="SVN repo dir"),
    tsv: bool = typer.Option(False, "--tsv", help="Output plain TSV format"),
):
    """List every commit touching branches/unlabeled-*."""
    LOG_MANUFACTURED_RE = re.compile(r'A (/branches/\S+) \(from (/[^:]+):(\d+)\)')
    for commit in parse_svn_log(log_file):
        isManufactured = "This commit was manufactured by cvs2svn to create branch" in commit.message
        if isManufactured:
            if tsv: continue
            copy_changes = [c for c in commit.changes if c[0] != "D"]
            if len(copy_changes) != 1: error("Manufactured commit with multiple sources!")
            sources = " ".join([
                match.group(1)[len("/branches/unlabeled-"):]
                for match in [
                    LOG_MANUFACTURED_RE.search(c)
                    for c in copy_changes
                ]
                if match
            ])
            print(f"\033[34;1m{commit.rev} | {commit.author} | Manufactured from {sources}\033[0m")
            for change in copy_changes:
                m = LOG_MANUFACTURED_RE.search(change)
                if not m:
                    error(f"Non Remove change not matching pattern: {change}")
                    continue
                branch_path = m.group(1)
                rev_num = commit.rev.lstrip("r")
                for f in revision_tree(repo_dir, branch_path, rev_num):
                    if f.endswith("/"): continue
                    print(f"\033[32mC  {f}\033[0m")
            continue
        message = commit.message.splitlines()[0]
        if not tsv:
            print(f"\033[34;1m{commit.rev} | {commit.author} | {message}\033[0m")
        colors = dict(
            M = 3,
            A = 2,
            D = 1,
            R = 5,
        )
        for change in commit.changes:
            change_type = change[0]
            rest = change[2:]
            cvsbranch, *file = rest[len("/branches-unlabeled-"):].split("/",1)
            file = file[0] if file else "???"
            if tsv:
                print(f"{commit.rev}\t{change_type}\t{file}\t{cvsbranch}\t{commit.author}\t{message}")
            else:
                print(f"\033[{30 + colors[change_type]}m{change_type} {rest}\033[0m")
            


def continued_download(url: str, dest_dir: Path) -> Path:
    """Download a file with wget -c style continuation using .part files."""
    filename = dest_dir / url.rsplit("/", 1)[-1]
    part_file = dest_dir / (filename.name + ".part")

    if filename.exists():
        step("Using cached {}", filename)
        return filename

    step("Downloading {}", filename.name)
    existing_size = part_file.stat().st_size if part_file.exists() else 0

    headers = {"Range": f"bytes={existing_size}-"} if existing_size else {}
    resp = requests.get(url, headers=headers, stream=True)

    if resp.status_code == 206:
        mode = "ab"
    elif resp.status_code == 200:
        mode = "wb"
    else:
        resp.raise_for_status()

    with open(part_file, mode) as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    part_file.rename(filename)
    return filename


TARBALL_DIR = Path("tarballs")

DEFAULT_URLS = [
    "https://clam-project.org/download/src/",
    "https://clam-project.org/download/src/old/",
]


@app.command()
def tarball_revisions(
    urls: list[str] = typer.Argument(default=None, help="URLs listing tarballs (default: CLAM download pages)"),
):
    """Parse tarball pages, extract SVN_REVISION, output rev<TAB>stem TSV."""
    if not urls:
        urls = DEFAULT_URLS
    TARBALL_DIR.mkdir(exist_ok=True)

    tarball_urls = []
    for page_url in urls:
        step("Fetching {}", page_url)
        resp = requests.get(page_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.endswith(".tar.gz") and "/" not in href:
                full_url = page_url.rstrip("/") + "/" + href
                tarball_urls.append((full_url, href.removesuffix(".tar.gz")))

    step("Found {} tarballs", len(tarball_urls))

    for url, stem in tarball_urls:
        try:
            filename = continued_download(url, TARBALL_DIR)
        except Exception as e:
            warn("Failed to download {}: {}", url, e)
            print(f"0\t{stem}")
            continue

        try:
            with tarfile.open(filename, "r:gz") as tf:
                members = [m.name for m in tf.getmembers()]
                rev_member = next(
                    (m for m in members if m.endswith("SVN_REVISION")),
                    None,
                )
                if rev_member:
                    rev = tf.extractfile(rev_member).read().decode().strip()
                else:
                    warn("No SVN_REVISION in {}", filename)
                    rev = "0"
        except Exception as e:
            warn("Failed to read {}: {}", filename, e)
            rev = "0"

        print(f"{rev}\t{stem}")


if __name__ == "__main__":
    app()
