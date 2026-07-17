# Getting started

## Install for development

```bash
pipx install uv
uv sync --extra test
```

Install a local board plugin into the same environment when needed:

```bash
uv pip install -e ../clavis-samidare
```

## Start the daemon

Use a Unix socket for local-only operation:

```bash
uv run clavisd --uds /tmp/clavisd.sock
```

Use TCP when another process or host must access the API:

```bash
uv run clavisd --host 127.0.0.1 --port 8000
```

Clavis does not provide authentication. Network exposure is appropriate only
on a trusted network or behind an authenticated proxy.

## Common commands

```bash
uv run clavis status
uv run clavis boards types
uv run clavis boards list
uv run clavis boards create board_type=TYPE board_id=ID name=NAME
uv run clavis boards connect ID
uv run clavis boards power-on ID
uv run clavis boards start-acquisition ID
uv run clavis boards stop-acquisition ID
uv run clavis boards power-off ID
uv run clavis boards disconnect ID
```

Pass `--host http://HOST:PORT` for a TCP daemon. Every command supports
`--help`.

The optional terminal interface is started with `uv run clavis tui`.
