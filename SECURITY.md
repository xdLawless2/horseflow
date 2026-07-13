# Security policy

## Network boundary

Horseflow intentionally has no authentication or TLS termination. The API can
receive microphone audio and consume GPU resources, so it must not be exposed
directly to the public internet.

Bind the Compose port to one of:

- `127.0.0.1`
- A private LAN address protected by a firewall
- A private overlay-network address such as Tailscale

Use a reverse proxy with authentication and TLS if access outside a trusted
private network is required.

## Client privileges

The Linux client reads physical keyboard devices, creates a virtual input
device, records the selected microphone, writes to the clipboard, and injects
a paste shortcut.

The macOS client requires Accessibility, Input Monitoring, and Microphone
permissions for the equivalent behavior.

Review the client source and install scripts before granting these privileges.

## Audio retention

Clients create temporary WAV files and remove them after upload or cancellation.
The server uses a temporary WAV file and removes it after transcription. The
server does not persist transcripts.

Container, reverse-proxy, systemd, or application logs may still contain
metadata. Configure those systems according to your retention requirements.

## Reporting

Do not open a public issue containing an undisclosed vulnerability, audio,
transcripts, credentials, private addresses, or other sensitive data. Contact
the repository maintainer privately before public disclosure.
