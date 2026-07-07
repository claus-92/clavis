# clavis

Minimal Python boilerplate for acquisition-board control through a daemon/API.

## Install

Install `uv` once, for example with `pipx`:

```bash
pipx install uv
```

Create the local development environment and install the project in editable mode:

```bash
uv sync --extra test
```

## Run Daemon

```bash
# Run daemon over TCP
uv run clavisd --host 127.0.0.1 --port 8000

# Run daemon over Unix socket
uv run clavisd --uds /tmp/clavisd.sock
```

Equivalent raw Uvicorn commands:

```bash
uv run uvicorn clavis.api.app:app --host 127.0.0.1 --port 8000
uv run uvicorn clavis.api.app:app --uds /tmp/clavisd.sock
```

## CLI

```bash
# CLI through local Unix socket
uv run clavis status
uv run clavis boards list

# Interactive TUI (live board status dashboard)
uv run clavis tui

# CLI against remote daemon
uv run clavis --host http://127.0.0.1:8000 status
uv run clavis --host https://server.example.com boards list
```

All commands support `--help`, e.g.:

```bash
uv run clavis boards set-global --help
```

Shell completion (double-tab) can be installed with:

```bash
uv run clavis --install-completion
```

## Tests

```bash
uv run pytest
```

## Architecture

`clavisd` owns all application state and exposes the REST API. External callers, including the future Web GUI and the `clavis` CLI, interact only with that API.

Dependency direction:

```text
external Web GUI -> REST API exposed by clavisd -> service/core -> AcquisitionBoard -> Transport
clavis CLI -> HTTP client -> REST API exposed by clavisd -> service/core -> AcquisitionBoard -> Transport
```

Parameter definitions live in JSON files under `parameter_definitions/`. The API exposes them so a future Web GUI can build dynamic controls from `generalParameters`, `groupParameters`, and `channelParameters`.

The current implementation uses fake transports and fake boards only. `boards/samidare.py` is a placeholder for a future SAMIDARE-specific board implementation backed by a real transport.
