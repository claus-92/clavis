# CLAVIS Architecture

`clavisd` owns application state and exposes the REST API. External callers, including the CLI and future UI, interact only with that API.

## Dependency Direction

```text
CLI / future UI
  -> REST API exposed by clavisd
  -> ClavisService
  -> BoardRegistry / BoardFactory / PluginRegistry
  -> AcquisitionBoard implementation
  -> protocol client
  -> transport
  -> hardware or simulator
```

## Core Package Responsibilities

The `clavis` package owns generic infrastructure:

- REST API and daemon process.
- CLI HTTP client.
- Board registry and generic board factory.
- Plugin discovery through Python entry points.
- Stable board/plugin interfaces.
- Reusable transports, such as UDP.
- Reusable protocol clients, such as fakernet, when they are not board-specific.
- Fake board/plugin support for tests and local development.

The core package must not hard-code third-party board implementations.

## Plugin Package Responsibilities

Board plugin packages own board-specific behavior:

- Board class implementation.
- Board config model.
- Board-specific factory callback registered through `BoardPlugin`.
- Register mapping and parameter semantics.
- Parameter definition files.
- Compatibility decisions, such as “SAMIDARE requires fakernet over UDP”.

Plugins register with core through `pyproject.toml` entry points:

```toml
[project.entry-points."clavis.boards"]
samidare = "clavis_samidare.plugin:plugin"
```

Core discovers the plugin dynamically and calls the plugin's generic `create_board` callback. Core must not import plugin-specific functions directly.

## Board Construction Flow

```text
BoardConfig
  -> BoardFactory.create(config)
  -> plugin = PluginRegistry.get(config.board_type)
  -> plugin_config = plugin.config_model.validate(config)
  -> plugin.create_board(plugin_config, ClientRegistry)
  -> AcquisitionBoard instance
```

Specialized construction, such as creating a `SamidareBoard`, belongs inside the plugin package.

## Transport And Protocol Boundaries

Keep layers separate:

- `UdpTransport` sends and receives bytes only.
- `FakernetRegisterClient` encodes/decodes fakernet packets, handles sequence numbers, retries, register reads/writes, and reliable-channel setup.
- Board classes express board operations and translate parameter updates into protocol-client calls.

Do not put register semantics into generic transports. Do not make board classes speak raw UDP if a protocol client is the real abstraction.

## Local Plugin Development

Plugins do not need to be published. Install local plugins into the same environment as `clavis`:

```bash
uv pip install -e ../clavis-samidare
```

After installation, restarting `clavisd` should make the plugin visible through `GET /api/board-types`.
