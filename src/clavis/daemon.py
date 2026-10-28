import os
from pathlib import Path

import typer
import uvicorn

from clavis.branding import version_text
from clavis.runtime import DEFAULT_UDS

app = typer.Typer(help="Run the clavisd daemon/API.")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(version_text("clavisd"))
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def run(
    uds: str = typer.Option(DEFAULT_UDS, "--uds", envvar="CLAVIS_UDS", help="Unix domain socket path."),
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the installed clavisd version and exit.",
    ),
) -> None:
    uds = str(Path(uds).expanduser())
    try:
        Path(uds).parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError as exc:
        raise typer.ClickException(f"Cannot create socket directory for {uds}: {exc}") from exc
    os.umask(0o007)
    uvicorn.run("clavis.api.app:app", uds=uds)
