# Cross-machine setup with Tailscale

This setup runs Whisper, Ollama, and the API on one GPU-equipped Linux server.
Linux and macOS clients record locally and send audio to that server through
the encrypted tailnet.

Tailscale Serve is the supported path. The Horseflow container remains bound
to localhost while Tailscale provides a stable tailnet-only HTTPS endpoint.
This also satisfies macOS App Transport Security without weakening the client.

## 1. Join every machine to one tailnet

Install Tailscale on:

- The Linux GPU server
- Every Linux dictation client
- Every macOS dictation client

Sign in to the same tailnet and confirm the machines can see one another:

```bash
tailscale status
```

In the Tailscale admin console under **DNS**:

1. Enable MagicDNS.
2. Enable HTTPS Certificates.

Tailscale HTTPS certificates publish machine and tailnet DNS names to public
Certificate Transparency logs. They do not make the service public.

Clone Horseflow on the server and each client machine:

```bash
git clone https://github.com/xdLawless2/horseflow.git
cd horseflow
```

## 2. Start Horseflow on the server

Keep the API bound to loopback in `deploy/.env`:

```dotenv
HORSEFLOW_BIND_ADDRESS=127.0.0.1
```

Start and verify Horseflow:

```bash
cd deploy
docker compose up -d ollama
docker compose exec ollama ollama pull qwen3:8b
docker compose up -d --build api
curl http://127.0.0.1:8100/health
```

## 3. Publish it inside the tailnet

On the server:

```bash
tailscale serve --bg 8100
tailscale serve status
```

The command prints an endpoint resembling:

```text
https://horseflow-server.example-tailnet.ts.net
```

Serve terminates HTTPS on the Tailscale interface and proxies requests to
`http://127.0.0.1:8100`. It persists across reboots. It is available only to
devices permitted by the tailnet policy.

Do not use `tailscale funnel`; Funnel would publish the service to the internet.

## 4. Test from each client machine

Use the exact URL reported by `tailscale serve status`:

```bash
curl https://horseflow-server.example-tailnet.ts.net/health
```

Do not continue until this returns the configured ASR and LLM model names.

## 5. Configure a Linux client

```bash
mkdir -p ~/.config/horseflow
cp clients/linux/client.env.example ~/.config/horseflow/client.env
```

Set the endpoint in `~/.config/horseflow/client.env`:

```dotenv
HORSEFLOW_API_URL=https://horseflow-server.example-tailnet.ts.net/dictate
HORSEFLOW_MIC=alsa_input.usb-your_microphone-00.mono-fallback
```

Then install:

```bash
clients/linux/install.sh
```

## 6. Configure a macOS client

Run the installer with the same HTTPS endpoint:

```bash
clients/macos/install.sh \
  https://horseflow-server.example-tailnet.ts.net/dictate
```

Grant Horseflow Accessibility, Input Monitoring, and Microphone access when
macOS prompts.

## Operations

Inspect the private proxy:

```bash
tailscale serve status
```

Remove it:

```bash
tailscale serve reset
```

If a client cannot connect, verify `tailscale status`, test `/health`, inspect
the tailnet access policy, and check the server with:

```bash
docker compose -f deploy/compose.yaml ps
docker compose -f deploy/compose.yaml logs -f api ollama
```
