# Board plugins

A board plugin is a separate Python package installed in the same environment
as Clavis. It registers a `BoardPlugin` entry point:

```toml
[project.entry-points."clavis.boards"]
example = "clavis_example.plugin:plugin"
```

The package supplies:

- A Pydantic 2 configuration model.
- An `AcquisitionBoard` implementation.
- A generic `create_board(config, clients)` factory.
- Parameter definitions for global, group, and channel controls.

Keep board-specific register maps and construction rules in the plugin. Reuse
core transports and protocol clients where their semantics match the hardware.

For a working package layout, use
[clavis-samidare](https://github.com/claus-92/clavis-samidare) as the reference.
The repository also contains a deliberately nonfunctional
[`examples/board-plugin`](../examples/board-plugin) template.
Install a local plugin with:

```bash
uv pip install -e ../clavis-example
```

Restart `clavisd` and verify registration with `clavis boards types`. Driver
methods must enforce live hardware-state and register-safety invariants; Clavis
provides generic request validation from the parameter definitions.
