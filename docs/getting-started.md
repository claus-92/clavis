# Getting started

## Install for development

```bash
pipx install uv
uv sync --extra test
```

Install a local board plugin into the same environment when needed:

```bash
uv pip install -e ../clavis-samidare
```

## Start the daemon

The daemon and local clients default to `~/.clavis/clavisd.sock`. The daemon
creates `~/.clavis` if needed; no root permissions are required:

```bash
uv run clavisd
uv run clavis status
```

Use `--uds PATH` or `CLAVIS_UDS` to override the socket for both commands.
The system-service example explicitly uses `/run/clavis/clavisd.sock` instead.

`clavisd` does not listen on TCP. Use Caddy or another Unix-socket-capable
reverse proxy when network access is required. Clavis does not provide
authentication, so expose that proxy only on a trusted network or configure
authentication at the proxy.

## Common commands

```bash
uv run clavis status
uv run clavis boards types
uv run clavis boards list
uv run clavis boards create board_type=TYPE board_id=ID name=NAME
uv run clavis boards connect ID
uv run clavis boards power-on ID
uv run clavis boards arm-acquisition ID
uv run clavis boards start-acquisition ID
uv run clavis boards stop-acquisition ID
uv run clavis boards power-off ID
uv run clavis boards disconnect ID
```

Arming prepares acquisition and waits for a start request. For a SAMIDARE board
configured with the local start source, `start-acquisition` sends the Fakernet
start strobe after arming. With GPIO0 selected, the external rising edge starts
the run instead.

Pass `--host http://HOST:PORT` to use a remote Caddy endpoint. Every command
supports `--help`.

## Terminal interface

Start the keyboard-driven terminal interface with:

```bash
uv run clavis tui
```

The dashboard shows the connection, power, and acquisition state of every
configured board. Its footer lists the available keyboard shortcuts.

![Clavis TUI board dashboard](images/TUI_Dashboard.png)

Use the arrow keys to move between boards. Press <kbd>Space</kbd> to mark or
unmark the current board (`[x]`), and <kbd>Ctrl+A</kbd> to select all boards
(press again to deselect all). The selection counter shows how many boards
are marked; selections survive automatic refreshes.

Act on the marked boards directly from the dashboard:
<kbd>c</kbd> connect, <kbd>x</kbd> disconnect, <kbd>o</kbd> power on,
<kbd>f</kbd> power off, <kbd>a</kbd> arm acquisition, <kbd>s</kbd> start
acquisition, and <kbd>t</kbd> disarm. With no marked boards, these commands
target the current row. Operations run concurrently across the target boards;
the dashboard shows progress and a completion summary with individual errors.
Wait for completion before issuing another operation. Selections remain marked
so successive commands can target the same group.

Concurrent start requests are not a hardware-synchronized trigger; use a shared
external start source when precise synchronization is required.
For SAMIDARE local start, use Arm then
Start; if GPIO0 is selected, the external rising edge starts the run. Press
<kbd>Enter</kbd> or <kbd>d</kbd> to open the current row's detail view, where
actions and parameter edits apply only to that board.

![Clavis TUI board detail and parameters](images/TUI_Board_Detail.png)
