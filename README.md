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

## Docker Compose

Build the image and start the daemon container:

```bash
docker compose up --build -d daemon
```

The API is then available externally at `http://127.0.0.1:8000`. The running
container is named `clavis` and includes both executables, so run CLI commands
inside it without specifying `--host`:

```bash
docker exec clavis clavis status
docker exec clavis clavis boards types
docker exec clavis clavis boards list
```

Use `CLAVIS_PORT` to change the published daemon port:

```bash
CLAVIS_PORT=8080 docker compose up -d daemon
```

The image contains the core package. Board plugins such as `clavis-samidare`
remain separate packages and are installed in derived daemon images. The CLI
inside the container communicates with the daemon through its TCP API. Stop
the stack with:

```bash
docker compose down
```

### Publish the core image

Choose a registry and replace the example name below with your Docker Hub
(`docker.io`) or GitHub Container Registry (`ghcr.io`) namespace:

```bash
docker login ghcr.io
docker build -t ghcr.io/OWNER/clavis:0.1.0 .
docker push ghcr.io/OWNER/clavis:0.1.0
```

For Docker Hub, use a name such as `docker.io/USERNAME/clavis:0.1.0` and run
`docker login docker.io`. Registry credentials or access tokens should be
entered at the login prompt, not stored in `compose.yaml`.

On a release host, select the published core image and skip local builds:

```bash
export CLAVIS_DAEMON_IMAGE=ghcr.io/OWNER/clavis:0.1.0
docker compose pull
docker compose up --no-build -d daemon
docker exec clavis clavis status
```

### Use board plugins

A board-plugin image derives from the published core image and installs the
plugin into the daemon's Python environment. For example,
`clavis-samidare/Dockerfile` builds the SAMIDARE variant. After publishing that
image, use it for the container:

```bash
export CLAVIS_DAEMON_IMAGE=ghcr.io/OWNER/clavis-samidare:0.1.0
docker compose pull
docker compose up --no-build -d daemon
docker exec clavis clavis boards types
```

For an unpublished development plugin, create a small Dockerfile in that
plugin repository:

```dockerfile
ARG CLAVIS_BASE_IMAGE=ghcr.io/OWNER/clavis:0.1.0
FROM ${CLAVIS_BASE_IMAGE}

COPY . /opt/my-board-plugin
RUN python -m pip install --no-cache-dir /opt/my-board-plugin
```

Build it locally, then pass its tag to Compose:

```bash
docker build -t clavis-my-board:dev path/to/my-board-plugin
CLAVIS_DAEMON_IMAGE=clavis-my-board:dev docker compose up --no-build -d daemon
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

`clavisd` validates parameter updates from these definitions before calling a
board driver. Definitions support `type` (`boolean`, `integer`, `number`, or
`string`), `defaultValue`, `options`, and optional inclusive `minimum` and
`maximum` bounds for numeric types. Validation is strict: values are not
coerced between strings, numbers, and booleans. Drivers may keep additional
board-state and hardware-safety validation.

The current implementation uses fake transports and fake boards only. `boards/samidare.py` is a placeholder for a future SAMIDARE-specific board implementation backed by a real transport.
