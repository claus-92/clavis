# Native service

A native installation normally runs `clavisd` under systemd and lets systemd
create `/run/clavis` with controlled ownership. The example unit in
[`examples/clavisd.service`](examples/clavisd.service) assumes a `clavis`
system user and group and that `clavisd` is installed at `/usr/bin/clavisd`.
Adjust those values for the local installation.

```bash
sudo install -m 0644 docs/examples/clavisd.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now clavisd
```

Users who need the local CLI must be members of the `clavis` group. They can
then run `clavis status` without a connection option.

## Network access

The example [`Caddyfile`](examples/Caddyfile) publishes port 8000 and proxies
requests to `/run/clavis/clavisd.sock`. The Caddy process must also have
supplementary membership in the `clavis` group. For a packaged Caddy systemd
unit, add an override:

```ini
[Service]
SupplementaryGroups=clavis
```

Reload systemd and restart Caddy after installing the Caddyfile and override.
Package paths and service names vary by distribution.

Stopping Caddy does not stop `clavisd`; local CLI access over the socket
continues to work. Clavis itself does not authenticate API requests, so bind
Caddy only to a trusted network or configure authentication and TLS there.
