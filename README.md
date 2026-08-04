<p align="center">
  <img src="https://raw.githubusercontent.com/claus-92/clavis/main/docs/logo.png" alt="Clavis logo" width="420">
  <br>
  <strong>Control Layer for Acquisition-board Validation and Interface Services</strong>
</p>

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
export CLAVIS_UDS=/tmp/clavisd.sock
uv run clavisd --uds /tmp/clavisd.sock
uv run clavis status
uv run clavis boards types
```

Docker users can build and start the daemon and its Caddy network proxy with:

```bash
docker compose up --build -d
docker exec clavis clavis status
```

`clavisd` always listens on a Unix socket. Caddy exposes the API on TCP when
network access is needed. The API has no authentication layer; expose the
proxy only on a trusted interface or add appropriate authentication.

## Documentation

The documentation is published at
[claus-92.github.io/clavis](https://claus-92.github.io/clavis/).

- [Getting started](docs/getting-started.md)
- [Docker](docs/docker.md)
- [Native service](docs/native-service.md)
- [Architecture](docs/architecture.md)
- [Board plugins](docs/plugins.md)
- [Configuration and parameters](docs/configuration.md)

The interactive API documentation is available at `/docs` through the Caddy
endpoint.

## License

Clavis is licensed under the [Apache License 2.0](LICENSE).

## Citing Clavis

If Clavis contributes to published work, cite the software using the metadata
in [`CITATION.cff`](CITATION.cff). GitHub also exposes this metadata through
the repository's **Cite this repository** action.
