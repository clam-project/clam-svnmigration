import subprocess
from pathlib import Path

import typer
from consolemsg import step

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

@app.command()
def analyze_svn(
    repo_dir: Path = typer.Argument(..., help="Path to loaded SVN repository"),
):
    """Analyze an SVN repository and list branches and tags."""
    elements = svnls(repo_dir, "branches") + svnls(repo_dir, "tags")
    for element in elements:
        step(f"{element}")
        for subdir in svnls(repo_dir, element):
            print(f"  {subdir.split('/')[-1]}")

if __name__ == "__main__":
    app()
