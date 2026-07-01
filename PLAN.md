# CLAVIS Plan

This file records the staged execution plan. Update checkboxes only when the user wants persistent progress tracking.

## Stage 1: Core Plugin Foundation

- [x] Define board plugin contracts in core.
- [x] Add a generic board factory that creates boards by looking up `board_type` in the plugin registry.
- [x] Load external board plugins from the `clavis.boards` entry point group.
- [x] Keep a built-in fake board plugin for local development and tests.
- [x] Add generic board configuration and board-type API models.
- [x] Add API/CLI support for listing board types and creating boards from generic config.

## Stage 2: Reusable Transport And Client Layer

- [x] Add a generic UDP datagram transport.
- [x] Add a fakernet register client in core.
- [x] Keep fakernet sequence/retry/register packet logic out of board classes.
- [ ] Add hardware-free packet-level tests for fakernet request/response validation.
- [ ] Add a local UDP test-server test for `UdpTransport`.

## Stage 3: SAMIDARE Plugin Package

- [x] Create `../clavis-samidare` as an installable plugin package.
- [x] Register `samidare` through the `clavis.boards` entry point group.
- [x] Move SAMIDARE board class/config/parameter definitions into `clavis-samidare`.
- [x] Verify local editable install with `uv pip install -e ../clavis-samidare`.
- [ ] Replace placeholder SAMIDARE behavior with real register mappings when available.

## Stage 4: Board Configuration Persistence

- [ ] Decide where daemon board configs should persist.
- [ ] Load configured boards on daemon startup.
- [ ] Add update/delete behavior for persistent board configs.
- [ ] Keep defaults safe and local; do not auto-connect to hardware on startup unless explicitly configured.

## Stage 5: UI-Ready API Shape

- [ ] Expand `GET /api/board-types` with enough schema metadata for a UI to build board creation forms.
- [ ] Clarify configured vs connected vs discovered board states.
- [ ] Add validation errors that are useful for UI display.
