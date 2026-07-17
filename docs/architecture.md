# Architecture

`clavisd` owns board instances and application state. The CLI and TUI use the
same REST API as other clients; they do not access board objects directly.

```text
CLI / TUI / external client
  -> FastAPI REST API
  -> ClavisService
  -> board and plugin registries
  -> AcquisitionBoard plugin implementation
  -> protocol client
  -> transport
  -> hardware or simulator
```

## API listener and client transport

The REST API is HTTP in both supported modes. A `clavisd` process exposes one
Uvicorn listener, selected when the process starts:

- `clavisd --host HOST --port PORT` listens on TCP. With no daemon options,
  `HOST` is `127.0.0.1` and `PORT` is `8000`.
- `clavisd --uds PATH` serves HTTP through the Unix-domain socket at `PATH`.
  When `--uds` is set, Uvicorn uses that socket instead of the TCP listener.

The CLI and TUI select their client transport independently:

- If `--host URL` or the `CLAVIS_HOST` environment variable is present, the
  client sends normal HTTP requests to that TCP URL. An explicit `--host`
  takes precedence over `CLAVIS_HOST`.
- Otherwise, the client sends HTTP through a Unix-domain socket. Its default
  path is `/tmp/clavisd.sock`, and `--uds PATH` selects another path.

Consequently, the bare commands do not select matching defaults:

```text
clavisd           -> TCP 127.0.0.1:8000
clavis status     -> Unix socket /tmp/clavisd.sock
```

For local socket operation, start both sides with the same socket path:

```bash
clavisd --uds /tmp/clavisd.sock
clavis status
```

For TCP operation, point the client at the daemon explicitly:

```bash
clavisd --host 127.0.0.1 --port 8000
clavis --host http://127.0.0.1:8000 status
```

The Compose service uses TCP only. The daemon binds `0.0.0.0:8000` inside the
container and Docker publishes that port on the host. `CLAVIS_HOST` is set to
`http://127.0.0.1:8000` inside the container, which is why this command reaches
the daemon without additional connection options:

```bash
docker exec clavis clavis status
```

The Unix socket is not created or mounted by the current Compose configuration.

Core Clavis implements the API, service, plugin discovery, board factory,
generic clients and transports. A board plugin implements its configuration
model, board behavior, register semantics, and parameter definitions.

Plugins register a `BoardPlugin` through the `clavis.boards` entry-point group.
The factory validates common configuration, selects the plugin by `board_type`,
validates with the plugin model, and calls its `create_board` function.

`UdpTransport` only moves datagrams. Protocol behavior such as fakernet packet
encoding, response validation, retries, and reliable-channel handling belongs
to `FakernetRegisterClient`. Board drivers express hardware operations through
the narrow client interface they require.

Board configuration is currently held in daemon memory. Restarting the daemon
does not restore boards automatically.
