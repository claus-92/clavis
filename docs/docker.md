# Docker

Build the local core image and start the daemon:

```bash
docker compose up --build -d daemon
```

The API is available on `http://127.0.0.1:8000`. The running container includes
the CLI and is configured to contact its own daemon:

```bash
docker exec clavis clavis status
docker exec clavis clavis boards types
docker exec clavis clavis boards list
```

Change the host port with `CLAVIS_PORT`:

```bash
CLAVIS_PORT=8080 docker compose up -d daemon
```

Stop and remove the local container with `docker compose down`.

## Local plugin images

Board plugins can derive from the core image. Build the core image first, then
build the plugin repository:

```bash
docker build -t clavis:local .
docker build --build-arg CLAVIS_BASE_IMAGE=clavis:local -t clavis-samidare:local ../clavis-samidare
```

Select the plugin-equipped image for Compose:

```bash
CLAVIS_DAEMON_IMAGE=clavis-samidare:local docker compose up --no-build -d daemon
docker exec clavis clavis boards types
```

The daemon does not provide authentication. Expose it only on a trusted
network or behind an authenticated service.
