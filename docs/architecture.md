# Architecture

`clavisd` owns board instances and application state. The CLI and TUI use the
same REST API as other clients; they do not access board objects directly.

```text
local CLI / TUI -> Unix socket ┐
                               ├-> FastAPI REST API
external client -> Caddy ------┘
  -> ClavisService
  -> board and plugin registries
  -> AcquisitionBoard plugin implementation
  -> protocol client
  -> transport
  -> hardware or simulator
```

## API boundary

`clavisd` serves HTTP only through a Unix-domain socket. The default is
`~/.clavis/clavisd.sock`, resolved against the current user's home directory;
`--uds` or `CLAVIS_UDS` can select a different path. The daemon creates the
parent directory when permissions allow it, with private permissions for a
new directory. The system-service example explicitly selects `/run/clavis/clavisd.sock`
and lets the service manager prepare `/run/clavis`.

The CLI and TUI use the same socket by default, so an administrator can still
use them locally over SSH when the network proxy is stopped or unavailable:

```bash
clavis status
```

For remote use, Caddy accepts TCP HTTP requests and forwards them to the Unix
socket. Caddy is an independent process: it owns network binding, TLS, access
controls, and any future authentication policy. More than one proxy may read
the same socket if separate network endpoints are required.

The CLI retains `--host URL` and `CLAVIS_HOST` for acting as a remote client.
When neither is set, it uses `--uds PATH`, `CLAVIS_UDS`, or the default socket,
in that order.

## Container topology

The Compose setup has two containers and one shared runtime volume:

```text
TCP :8000 -> Caddy container -> /run/clavis/clavisd.sock
                                  ^
                                  |
                             daemon container
                             (clavisd and clavis)
```

The daemon container has no published port. Both containers mount the
`clavis-runtime` named volume at `/run/clavis`; the CLI inside the daemon
container therefore reaches `clavisd` using its explicit `CLAVIS_UDS` setting:

```bash
docker exec clavis clavis status
```

The optional host-socket Compose override replaces the named volume with a
bind mount of host `${HOME}/.clavis` at container `/run/clavis`. This lets a
host-installed CLI use its default socket while preserving the two-container
proxy boundary. Socket directory
ownership and group membership must permit the daemon, Caddy, and the host
user to access it.

## Core and plugin boundaries

Core Clavis implements the API, service, plugin discovery, board factory,
generic clients and transports. A board plugin implements its configuration
model, board behavior, register semantics, and parameter definitions.

Plugins register a `BoardPlugin` through the `clavis.boards` entry-point group.
The factory validates common configuration, selects the plugin by `board_type`,
validates with the plugin model, and calls its `create_board(config)` function.
The plugin constructs its required client and transport, either from reusable
core implementations or from plugin-owned implementations.

`UdpTransport` only moves datagrams. Protocol behavior such as fakernet packet
encoding, response validation, retries, and reliable-channel handling belongs
to `FakernetRegisterClient`. Board drivers express hardware operations through
the narrow client interface they require.

Board configuration is currently held in daemon memory. Restarting the daemon
does not restore boards automatically.

`BoardStatus.status_fresh` distinguishes a current hardware observation from a
cached value. Plugins that can query live hardware should refresh status while
connected and retain the last observation with `status_fresh=false` when the
control connection is unavailable.
