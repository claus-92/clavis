# CLAVIS Agent Instructions

This repository is being prepared as a Python acquisition-board control daemon with plugin-based board support. Future agent sessions must treat [TASK.md](TASK.md) as the source of truth for the product goal, [PLAN.md](PLAN.md) as the staged execution plan, and [ARCHITECTURE.md](ARCHITECTURE.md) as the current design reference.

## Operating Mode

- Do not implement new features unless the user explicitly asks you to proceed.
- Before implementation, inspect the workspace and produce a short plan that names the files and directories you expect to create or edit.
- Implement the smallest safe diff that satisfies the current stage or request.
- Keep unrelated refactors, formatting churn, and optional UI/server work out of the active milestone unless explicitly requested.
- If the user asks for a review, use a PR-review stance and do not edit files unless asked.
- Preserve the separation between core package code and plugin package code.

## Project Shape

- Primary package: `clavis`.
- First external plugin package: sibling directory `../clavis-samidare`.
- Core package stack: Python, FastAPI, Typer, httpx, Pydantic, setuptools, uv.
- Core commands should be run from the `clavis` repository root unless the user asks to work in a plugin package.
- Local plugins may be installed with editable installs, for example `uv pip install -e ../clavis-samidare`.
- Do not require plugin packages to be published online.
- Do not move plugin-specific board implementations back into the core package unless explicitly requested.

## Architecture Boundaries

- `clavisd` owns application state and exposes the REST API.
- CLI and future UI code must talk to `clavisd` through the API, not through direct board objects.
- Core owns generic board registry, plugin discovery, factory dispatch, API, CLI, reusable clients, and reusable transports.
- Board plugins own board-specific config models, board classes, parameter definitions, register maps, and construction rules.
- Core must discover board plugins dynamically through the `clavis.boards` entry point group.
- Core factory logic must stay generic: look up a plugin by `board_type`, validate config with the plugin model, and call the plugin's `create_board` callback.
- Do not add `create_samidare_board` or other plugin-specific constructors to core.
- Do not make generic transports aware of fakernet or board register semantics.
- Do not make board classes speak raw UDP when a protocol/client abstraction is the correct boundary.

## Transport And Client Rules

- `UdpTransport` should move bytes only: open, close, send, receive, timeout/source filtering.
- `FakernetRegisterClient` should own fakernet packet encoding, response validation, register access, sequence numbers, retries, and reliable-channel behavior.
- Board implementations should depend on the narrowest client/protocol interface they need.
- If a board supports only one protocol/client, enforce that in the plugin config/factory, not by hard-coding plugin choices in core.
- Reliable fakernet channels are protocol behavior, not generic UDP behavior.

## Plugin Rules

- New board support should usually be added as a plugin package, not by modifying core.
- Plugin packages should expose a `clavis.boards` entry point returning a `BoardPlugin`.
- Plugin packages may be local and private; support editable installs as a first-class workflow.
- Plugin package tests should run independently when practical.
- Core tests should not depend on hardware or network boards.

## Hardware And Safety Rules

- Do not connect to real hardware, scan networks, or send UDP/fakernet packets to non-test addresses unless the user explicitly asks.
- Do not invent register maps or hardware behavior. Use placeholders only when clearly labeled as placeholders.
- Prefer fake clients/transports and local loopback tests for verification.
- Treat hardware addresses, credentials, tokens, API keys, and session material as sensitive.
- Never log, print, or persist secrets casually.
- Keep automatic daemon startup behavior safe; do not auto-connect to hardware unless explicitly configured and requested.

## Verification

- Prefer repo-native commands:
  - `uv run pytest`
  - `uv run pytest tests/test_name.py`
  - `uv pip install -e ../clavis-samidare` when testing the local SAMIDARE plugin
  - `../clavis/.venv/bin/python -m pytest` from a plugin package when reusing the core environment
- Run the narrowest relevant verification first, then broaden only when useful.
- If a command fails because local dependencies or tooling are missing, report the blocker and the exact command that failed.
- Do not claim the package works or tests pass unless the relevant command has actually passed.

## Prompting Pattern

Use this pattern for future implementation:

1. Read `TASK.md` and `PLAN.md`.
2. Inspect the current workspace and, if relevant, sibling plugin packages.
3. Confirm the next unchecked stage from `PLAN.md` or the user's explicitly requested task.
4. List expected file changes before editing.
5. Implement only that stage or request.
6. Run relevant verification.
7. Update `PLAN.md` status only if the user wants persistent progress tracking.
8. Summarize the diff and test results.
