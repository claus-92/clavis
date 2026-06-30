from typing import Optional

import typer
import uvicorn

app = typer.Typer(help="Run the clavisd daemon/API.")


@app.callback(invoke_without_command=True)
def run(
    host: str = typer.Option("127.0.0.1", help="TCP host to bind."),
    port: int = typer.Option(8000, help="TCP port to bind."),
    uds: Optional[str] = typer.Option(None, help="Unix domain socket path."),
) -> None:
    uvicorn.run("clavis.api.app:app", host=host, port=port, uds=uds)
