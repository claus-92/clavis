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
