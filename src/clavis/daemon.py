import os
from pathlib import Path

import typer
import uvicorn

from clavis.runtime import DEFAULT_UDS

app = typer.Typer(help="Run the clavisd daemon/API.")


@app.callback(invoke_without_command=True)
def run(
    uds: str = typer.Option(DEFAULT_UDS, "--uds", envvar="CLAVIS_UDS", help="Unix domain socket path."),
) -> None:
    try:
        Path(uds).parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise typer.ClickException(f"Cannot create socket directory for {uds}: {exc}") from exc
    os.umask(0o007)
    uvicorn.run("clavis.api.app:app", uds=uds)
