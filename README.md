# Hermes Setup for Raspberry Pi

Run a setup page **on your Raspberry Pi**, open it from your laptop, enter your model credentials, and click **Set up Hermes**. The button downloads the official Hermes container, writes its model configuration, starts the assistant, checks the API and dashboard, and tests a short model response.

The Pi runs Hermes; a remote OpenAI-compatible provider runs the language model. You do not need to download an 8B model onto the Pi. You need a provider account, API key, exact model ID, and any required credit. The setup test uses a small number of paid provider tokens.

## 1. Prepare the Pi once

Use **64-bit Raspberry Pi OS (Bookworm or Trixie)** or another supported 64-bit Debian Linux. `uname -m` should print `aarch64`. The wizard also accepts x86_64 Linux. A Pi 4 or Pi 5 with 4 GB or more RAM is a reasonable starting target; this project has not been hardware-tested on a Pi. Have adequate free storage for the upstream container image and persistent state.

Enable SSH and connect to the Pi. Replace `YOUR_USER` and `PI_ADDRESS` below with your actual username and hostname/IP:

```bash
ssh YOUR_USER@PI_ADDRESS
```

On the Pi, install Git, curl, Docker Engine with the Compose plugin, and uv. If Docker is already installed, skip its installation. The following is the Docker convenience installer for a fresh personal Pi; review it before running. For an existing machine, use the [official Debian installation instructions](https://docs.docker.com/engine/install/debian/).

```bash
sudo apt update
sudo apt install -y git curl
curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
sudo sh /tmp/get-docker.sh
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
curl -LsSf https://astral.sh/uv/install.sh | sh
exit
```

Log back in so your Docker group membership and uv path take effect:

```bash
ssh YOUR_USER@PI_ADDRESS
docker info
docker compose version
uv --version
```

These commands must succeed **without sudo**. Docker group membership grants administrative control over the machine. Python dependencies are installed by the launcher using the committed lock file; uv can install the required Python version. See [uv installation](https://docs.astral.sh/uv/getting-started/installation/).

## 2. Put this updated project on the Pi

These changes must be copied to the Pi; cloning GitHub alone will not include local changes until you commit and push them.

To copy your current working project directly, run this from your laptop:

```bash
rsync -av --exclude='.git' --exclude='.venv' --exclude='.env*' \
  --exclude='.hermes-config.enc' --exclude='.hermes-runtime' \
  --exclude='backup_*' --exclude='data' --exclude='models' \
  --exclude='__pycache__' --exclude='.*cache' \
  /Users/deepaksama/Documents/Development/Repositories/hermes_setup/ \
  YOUR_USER@PI_ADDRESS:~/hermes_setup/
```

This intentionally leaves laptop credentials and local data behind. Enter the credentials you want to use on the Pi in the browser.

Alternatively, **after pushing the changes**, clone on the Pi:

```bash
git clone https://github.com/deepak-learning-central/hermes_setup.git
cd hermes_setup
```

## 3. Start the setup page with one command

On the Pi, inside the copied project:

```bash
cd ~/hermes_setup
bash start.sh
```

This command starts **only the setup web page** on the Pi. It does not install or start the Hermes container. Keep this terminal open until setup finishes. No separate `init`, `.env` editing or Docker commands are needed for Hermes deployment.

| Action | What it does |
|--------|--------------|
| `bash start.sh` | Installs the setup application's dependencies and starts its web server on port 8765. |
| **Set up Hermes** | Saves the form, pulls the Hermes image, applies configuration, starts the container and checks readiness. Use this for the first deployment and configuration changes. |
| **Start** under Manage your assistant | Starts the container using its existing generated Docker configuration. It does not save edits in the form or run the full setup checks. |
| **Stop** | Stops and removes the container using `docker compose down`, preserving its data volume and generated configuration. |
| **Restart** | Stops and recreates the container using its existing generated configuration, preserving its data volume. |

## 4. Open the page from your laptop

In a **second terminal on your laptop**, open this tunnel:

```bash
ssh -N -o ExitOnForwardFailure=yes \
  -L 8765:127.0.0.1:8765 \
  -L 9119:127.0.0.1:9119 \
  YOUR_USER@PI_ADDRESS
```

Keep it running, then open:

- **Setup:** [http://localhost:8765](http://localhost:8765)
- **Assistant after setup succeeds:** [http://localhost:9119](http://localhost:9119)

Both services bind to loopback on the Pi. The SSH tunnel makes them accessible privately on your laptop. Visiting `http://PI_ADDRESS:8765` directly is intentionally unsupported. No router port forwarding is required.

In the setup page:

1. Enter your provider’s OpenAI-compatible API URL, exact model ID and API key.
2. Optionally enable Telegram, Discord or Slack and enter its tokens and allowed-user IDs (see Messaging channels below).
3. Choose a configuration passphrase of at least 12 characters and keep it somewhere safe.
4. Optionally adjust the memory/CPU limits under Advanced settings (defaults: 2 GB / 2 CPUs).
5. Click **Set up Hermes**. Watch progress; the initial image download can take several minutes.
6. Once the model test passes, click **Open Hermes assistant** and start a conversation in the upstream dashboard.

You can stop the setup server with Ctrl+C afterwards. Hermes keeps running and restarts automatically after a Pi reboot. To use the assistant later, open the SSH tunnel and visit port 9119; the setup server is only needed for configuration or management.

## Access Hermes after installation

Open **[http://localhost:9119](http://localhost:9119)** on your laptop while the SSH tunnel above is running, or click **Open Hermes assistant** on the setup page. Port 8765 is the setup and management page; port 9119 is the Hermes assistant dashboard.

For everyday browser access, only the dashboard tunnel is needed:

```bash
ssh -N -o ExitOnForwardFailure=yes \
  -L 9119:127.0.0.1:9119 \
  YOUR_USER@PI_ADDRESS
```

Keep that terminal open while using the dashboard. Reconnect the tunnel after restarting your laptop or Pi. Messaging channels do not require your laptop, this tunnel or the setup web server to remain running; the Pi, Hermes container and its internet connection must be available.

## Automatic startup after a Pi reboot

The generated Compose configuration sets `restart: unless-stopped`. Once deployed and running successfully, Hermes starts again when Docker starts after a Pi reboot. Ensure Docker itself is enabled at boot by running this once **on the Pi**:

```bash
sudo systemctl enable --now docker
systemctl is-enabled docker
```

The second command should print `enabled`. After the next Pi reboot, reconnect with SSH and verify:

```bash
docker ps --filter name=hermes
docker inspect --format '{{.HostConfig.RestartPolicy.Name}}' hermes
```

The container should be running, and its restart policy should print `unless-stopped`. If needed, inspect its logs with `docker compose -f ~/hermes_setup/.hermes-runtime/compose.yml logs --tail 100`.

If you click **Stop** in the setup UI, the container is removed and will **not** come back after reboot. Click **Start** to recreate it before relying on automatic startup again. A container stopped manually with `docker stop hermes` also stays stopped across reboots under this policy. See [Docker restart policy documentation](https://docs.docker.com/engine/containers/start-containers-automatically/).

Neither `bash start.sh` nor the setup page needs to run at boot. Docker starts the existing Hermes container using its stored runtime configuration without requiring your configuration passphrase. The setup web server and laptop SSH tunnel do not start automatically.

## Messaging channels

The setup page includes optional **Telegram**, **Discord** and **Slack** configuration. Enable any combination before clicking **Set up Hermes**. Settings are encrypted with the rest of your configuration and passed to the Hermes gateway when it starts.

| Channel | Required values | One-time service setup |
|---------|-----------------|------------------------|
| Telegram | Bot token, allowed numeric user IDs | Create a bot with @BotFather using `/newbot`; after deployment open your bot and send `/start`. |
| Discord | Bot token, allowed numeric user IDs | Create a bot, enable Message Content Intent, and invite it to your server with messaging permissions. Developer Mode lets you copy user IDs. |
| Slack | Bot token (`xoxb-`), app token (`xapp-`), allowed Member IDs | Create/install an app, enable Socket Mode, and configure the required scopes and event subscriptions. |

Use comma-separated **user IDs**, not usernames or conversation/channel IDs. The wizard requires an explicit allowed-user list for each enabled channel. No channel is required to use the browser assistant.

Follow the upstream [Telegram guide](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram), [Discord guide](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord), or [Slack guide](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack) for service-specific permissions and finding your user ID. Bot creation and workspace installation still happen in the corresponding service.

To change channels later, unlock saved settings, edit the fields and run setup again. Disable a channel to clear its saved credentials on the next setup run. Setup checks the assistant API/model; it does not send test messages to messaging services. Verify each enabled channel yourself by messaging the bot from an allowed account; inspect **View logs** if it does not reply.

## How it works

```text
Laptop browser → SSH tunnel → Setup page on Pi :8765
                                ↓
                         Docker Compose on Pi
                                ↓
                       Hermes gateway + dashboard
                                ↓
                         Your model provider
```

The web page is an administration tool. Run it only when needed. Its JavaScript and styles are served locally, with no CDN dependencies. It validates settings before saving and refuses cross-origin browser requests.

Clicking **Set up Hermes** saves the form on the machine hosting the setup server—your Pi in the supported deployment. Typing into the form does not autosave, and clicking **Start** does not save form changes. The encrypted settings are saved before deployment begins, so they can remain saved even if a later deployment step fails.

| Location in the Pi project directory | Contents |
|--------------------------------------|----------|
| `.hermes-config.enc` | Model, channel and other setup settings encrypted using your passphrase. Unlock these in the UI to edit them later. |
| `.hermes-runtime/compose.yml` | Generated Docker runtime configuration used by the normal setup and management flow. |
| `.hermes-runtime/compose.prod.yml` | Generated production variant. |
| Docker named volume mounted at `/opt/data` | Hermes runtime configuration, conversations, memories and other persistent assistant state. |

The encrypted file and runtime directory are gitignored, and generated files have owner-only permissions. **The runtime Compose files contain plaintext API and channel credentials** because Docker needs them to restart unattended. Docker administrators can also inspect container environment values. Do not share these files or the Docker socket. The passphrase protects the saved configuration, not the running Docker container.

On Linux, host networking lets the upstream dashboard remain bound to `127.0.0.1` while remaining reachable through your SSH tunnel. The API also binds to loopback. Hermes state lives in the Compose project’s named `hermes-data` volume mounted at `/opt/data`. The wizard sets the upstream `model.default`, `model.provider` and `model.base_url` configuration and chooses the local terminal backend inside the container. Other existing Hermes configuration sections are preserved. The container uses the upstream entrypoint and supervisor.

Reference: [upstream Docker deployment](https://github.com/NousResearch/hermes-agent/blob/main/docker-compose.yml), [dashboard supervision](https://github.com/NousResearch/hermes-agent/blob/main/docker/s6-rc.d/dashboard/run).

## Management and recovery

- Start, Stop, Restart, View logs and Refresh status are available on the setup page.
- Stop and Restart preserve the state volume, including in production mode.
- Refreshing the browser reconnects to the current setup job in the same browser session.
- Reopen the setup page and unlock saved settings with your passphrase before changing them.
- If the image pull fails, check Pi internet access, storage and image architecture, then retry.
- If the model test fails, check the API URL, exact model ID, credentials and account balance. Correct the settings and run setup again. The container may already be running; no successful setup is claimed until the test passes.
- If the dashboard fails to start, use View logs. Ensure ports 8642 and 9119 are free on the Pi.
- If SSH reports a forwarding failure, another local process may already use ports 8765 or 9119. Stop that process or tunnel first.
- If you lose your passphrase, you can enter your settings again and rerun setup. Existing Hermes data remains in Docker; encrypted settings cannot be recovered without the passphrase.
- Do not run `docker compose down -v` or delete the volume unless you intend to delete assistant state.

For diagnostics on the Pi, use the generated Compose file, not the older files under `docker/`:

```bash
docker compose -f .hermes-runtime/compose.yml ps
docker compose -f .hermes-runtime/compose.yml logs --tail 100
```

The old CLI backup tools refer to host directories and **do not back up this Docker volume**. They are not exposed in the new setup page. To back up the actual state, stop Hermes, identify the named volume using `docker volume ls`, and archive that volume using Docker volume backup tooling. Preserve ownership and restart Hermes after backup. Do not assume that a host `data/` directory contains your assistant’s memories.

An older deployment using `docker/compose.yml` may use a different Compose project and volume. Do not run both against the same ports. Preserve its volume and migrate it explicitly before using the new wizard if it has data you need.

## Development and validation

```bash
uv sync
uv run pytest
uv run ruff check src tests
uv run mypy src
```

Unit/integration tests mock Docker and provider calls; they verify configuration validation, encrypted persistence, lifecycle behavior, Linux networking and deployment stage failures/success. A successful test suite is not a hardware deployment test. Actual ARM64 image download, dashboard startup and provider access must be verified on your target Pi using the setup button.

The original implementation plan describes earlier TUI and CI/CD ambitions. The supported end-user path is now this browser wizard; n8n, Obsidian, scheduled backups and zero-downtime deployment are not implemented by it.
