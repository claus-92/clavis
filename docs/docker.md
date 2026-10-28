# Docker

Build the local core image and start the daemon and Caddy:

```bash
docker compose up --build -d
```

The Caddy endpoint is available on `http://127.0.0.1:8000`. The daemon has no
TCP listener. Its container includes the CLI, which contacts the daemon over
the shared Unix socket:

```bash
docker exec clavis clavis status
docker exec clavis clavis boards types
docker exec clavis clavis boards list
```

Change the host port with `CLAVIS_PORT`:

```bash
CLAVIS_PORT=8080 docker compose up -d
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
CLAVIS_DAEMON_IMAGE=clavis-samidare:local docker compose up --no-build -d
docker exec clavis clavis boards types
```

## Make the socket available on the host

By default, the socket is contained in a Docker named volume. To use a
host-installed CLI against the container, prepare a host runtime directory
and use the bind-mount override:

```bash
sudo groupadd --system clavis
sudo usermod -aG clavis "$USER"
sudo install -d -o "$USER" -g clavis -m 2770 "$HOME/.clavis"
export CLAVIS_RUNTIME_GID="$(getent group clavis | cut -d: -f3)"
docker compose -f compose.yaml -f compose.host-socket.yaml up --build -d
```

The override mounts `${HOME}/.clavis` at `/run/clavis` in both containers.
Log in again after changing group membership. The host CLI then uses its
default socket, `~/.clavis/clavisd.sock`:

```bash
clavis status
```

Use the same Compose file arguments when stopping this variant. The socket
directory persists in your home folder across reboots. Do not loosen your
home directory permissions to provide socket access to unrelated users.

The API does not provide authentication. Expose Caddy only on a trusted
network or configure an appropriate authentication layer there.
