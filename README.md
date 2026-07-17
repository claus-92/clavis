# Clavis

Clavis is a Python daemon and command-line client for controlling acquisition
boards through a REST API. Board support is supplied by independently
installable plugins discovered through Python entry points.

## Development setup

Clavis requires Python 3.10 or newer and Pydantic 2.

```bash
pipx install uv
uv sync --extra test
uv run pytest
```

Run the daemon and CLI locally:

```bash
uv run clavisd --uds /tmp/clavisd.sock
uv run clavis status
uv run clavis boards types
```

For TCP access:

```bash
uv run clavisd --host 127.0.0.1 --port 8000
uv run clavis --host http://127.0.0.1:8000 status
```

Docker users can build and start the daemon with:

```bash
docker compose up --build -d daemon
docker exec clavis clavis status
```

The daemon has no authentication layer. Bind it only to a trusted interface or
place it behind an appropriate authenticated service.

## Documentation

- [Getting started](docs/getting-started.md)
- [Docker](docs/docker.md)
- [Architecture](docs/architecture.md)
- [Board plugins](docs/plugins.md)
- [Configuration and parameters](docs/configuration.md)

The interactive API documentation is available at `/docs` on a running TCP
daemon.

## License

Clavis is licensed under the [Mozilla Public License 2.0](LICENSE). Modified
MPL-covered files must remain available under MPL-2.0; applications using the
library may use a different license while preserving applicable notices.
