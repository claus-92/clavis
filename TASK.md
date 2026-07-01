# CLAVIS Task

CLAVIS is an acquisition-board control daemon and CLI. The immediate goal is to keep the core package generic while allowing board-specific support to be added through installable plugins.

## Product Goal

- Provide a Python daemon, `clavisd`, that owns board state and exposes a REST API for board discovery, configuration, connection, status, and parameter updates.
- Provide a CLI, `clavis`, that talks only to the daemon API.
- Support multiple acquisition boards in one daemon process.
- Allow board developers to add board implementations as local or published Python plugin packages without modifying the core `clavis` package.
- Keep reusable transports and protocol clients in core when they are board-agnostic.
- Keep board-specific logic, register maps, parameter definitions, and construction rules in board plugin packages.

## Current Direction

- Core package: `clavis`.
- First external board plugin package: sibling directory `../clavis-samidare`.
- Core should discover board plugins through Python entry points under `clavis.boards`.
- SAMIDARE should live in `clavis-samidare`, not in the core package.
- Fakernet protocol support and UDP byte transport are reusable core infrastructure.

## Non-Goals For The Current Milestone

- Do not build a Web UI unless explicitly requested.
- Do not invent hardware register mappings that are not known yet.
- Do not make board plugins depend on private core internals.
- Do not require plugins to be published online; local editable installs must work.
