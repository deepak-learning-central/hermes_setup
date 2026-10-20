"""HTML fragments rendered by HTMX for each settings tab.

Each fragment is a self-contained block of HTML inserted into the main
``#tab-content`` container.  They call the FastAPI backend endpoints for
real data instead of duplicating logic in JavaScript.
"""

from __future__ import annotations

# Each tab id -> static HTML fragment path (relative to the static dir).
# Static fragments are served directly; dynamic ones below are generated
# as Python strings so they can embed server-side values if needed later.


def _action_buttons() -> str:
    """Shared Start / Restart / Stop button group."""
    return """
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <button
        type="button"
        data-docker-action="start"
        class="docker-action bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-3 px-6 rounded-lg shadow transition-colors flex items-center justify-center gap-2"
      >
        <i class="fas fa-play"></i> Start Hermes
      </button>
      <button
        type="button"
        data-docker-action="restart"
        class="docker-action bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-3 px-6 rounded-lg shadow transition-colors flex items-center justify-center gap-2"
      >
        <i class="fas fa-redo"></i> Restart
      </button>
      <button
        type="button"
        data-docker-action="stop"
        class="docker-action bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-3 px-6 rounded-lg shadow transition-colors flex items-center justify-center gap-2"
      >
        <i class="fas fa-stop"></i> Stop
      </button>
    </div>
"""


def _job_panel() -> str:
    """Shared progress panel shown while a Docker operation runs."""
    return """
  <div id="job-panel" class="hidden mt-4 p-4 rounded-lg border border-blue-200 bg-blue-50">
    <div class="flex items-center gap-3">
      <i class="fas fa-circle-notch fa-spin text-blue-600"></i>
      <span id="job-title" class="text-sm font-medium text-blue-800">Working...</span>
      <span id="job-elapsed" class="text-xs text-blue-600 ml-auto">0s</span>
    </div>
    <pre id="job-output" class="mt-3 bg-gray-900 text-gray-300 rounded-md p-3 text-xs font-mono overflow-auto max-h-64 whitespace-pre-wrap"></pre>
  </div>
"""


def _status_card(card_id: str) -> str:
    """Shared Docker status card markup."""
    return f"""
    <div id="{card_id}" class="space-y-3">
      <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
        <span class="text-gray-600">Docker Engine</span>
        <span class="text-sm font-medium text-gray-500" data-status="docker">Checking...</span>
      </div>
      <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
        <span class="text-gray-600">Docker Compose</span>
        <span class="text-sm font-medium text-gray-500" data-status="compose">Checking...</span>
      </div>
      <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
        <span class="text-gray-600">Container State</span>
        <span class="text-sm font-medium text-gray-500" data-status="container">Checking...</span>
      </div>
    </div>
"""


def dashboard() -> str:
    """Dashboard: quick status + start/stop buttons + health card."""
    return f"""
<div class="max-w-6xl mx-auto space-y-6">
  <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
    <h2 class="text-xl font-bold text-gray-800 mb-4">Quick Actions</h2>
{_action_buttons()}
{_job_panel()}
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <div id="docker-card" class="lg:col-span-2 bg-white p-6 rounded-xl shadow-sm border border-gray-200">
      <h2 class="text-lg font-bold text-gray-800 mb-4 flex items-center">
        <i class="fas fa-docker text-blue-600 mr-2"></i>
        Docker Status
      </h2>
{_status_card("docker-status-card")}
      <div class="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
        <p class="text-sm text-blue-700">
          <i class="fas fa-info-circle mr-2"></i>
          Container state is refreshed automatically. Click "Start Hermes" to begin —
          progress appears below the buttons.
        </p>
      </div>
    </div>

    <div class="lg:col-span-1 bg-white p-6 rounded-xl shadow-sm border border-gray-200">
      <h2 class="text-lg font-bold text-gray-800 mb-4">Configuration</h2>
      <p class="text-sm text-gray-600 mb-4">
        All settings are saved to an encrypted file on this machine — never committed to git.
      </p>
      <a
        href="/tab/config"
        class="block bg-indigo-600 hover:bg-indigo-700 text-white text-center py-3 px-4 rounded-lg font-medium transition-colors"
      >
        Open Configuration &rarr;
      </a>
    </div>
  </div>
</div>
"""


def config() -> str:
    """Configuration tab: editable fields for all HermesConfig values."""
    return """
<div class="max-w-4xl mx-auto space-y-6">
  <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
    <h2 class="text-xl font-bold text-gray-800 mb-4">Hermes Configuration</h2>
    <p class="text-sm text-gray-600 mb-6">
      Set the values below and click <strong>Save Encrypted</strong>.
      You will be prompted for a passphrase used to encrypt the config file.
    </p>

    <!-- Config load section -->
    <div id="load-section" class="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200" style="display: none;">
      <h3 class="text-sm font-semibold text-gray-800 mb-1">Load Existing Config</h3>
      <p class="text-xs text-gray-500 mb-3">
        An encrypted config already exists on this machine. Enter its passphrase to load
        the saved values into this form.
      </p>
      <div class="flex flex-col sm:flex-row gap-3 items-end">
        <div class="flex-1">
          <label for="load-passphrase" class="block text-sm font-medium text-gray-700 mb-1">Passphrase</label>
          <input id="load-passphrase" type="password" autocomplete="off" placeholder="Enter passphrase"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
        </div>
        <button id="btn-load-config" type="button"
                class="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-5 rounded-lg transition-colors whitespace-nowrap">
          <i class="fas fa-folder-open mr-2"></i> Load Config
        </button>
      </div>
      <div id="config-load-result" class="mt-3 text-sm font-medium"></div>
    </div>

    <!-- Docker &amp; Network -->
    <fieldset class="border-t border-gray-200 pt-5">
      <legend class="text-sm font-semibold uppercase tracking-wide text-gray-500 px-2">Docker &amp; Network</legend>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
        <div>
          <label for="docker_image" class="block text-sm font-medium text-gray-700 mb-1">Docker Image</label>
          <input id="docker_image" type="text" value="nousresearch/hermes-agent:latest"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
          <p class="text-xs text-gray-500 mt-1">Use <code>:stable</code> for production deployments</p>
        </div>
        <div>
          <label for="api_port" class="block text-sm font-medium text-gray-700 mb-1">API Server Port</label>
          <input id="api_port" type="number" value="8642"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
          <p class="text-xs text-gray-500 mt-1">OpenAI-compatible API served by the agent</p>
        </div>
        <div>
          <label for="dashboard_port" class="block text-sm font-medium text-gray-700 mb-1">Dashboard Port</label>
          <input id="dashboard_port" type="number" value="9119"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
        </div>
        <div>
          <label for="enable_dashboard" class="block text-sm font-medium text-gray-700 mb-1">Enable Web Dashboard</label>
          <select id="enable_dashboard"
                  class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </div>
        <div>
          <label for="memory_limit" class="block text-sm font-medium text-gray-700 mb-1">Memory Limit</label>
          <input id="memory_limit" type="text" value="4g"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
        </div>
        <div>
          <label for="cpus_limit" class="block text-sm font-medium text-gray-700 mb-1">CPU Limit</label>
          <input id="cpus_limit" type="number" step="0.5" value="2"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
        </div>
        <div class="md:col-span-2">
          <label for="api_server_key" class="block text-sm font-medium text-gray-700 mb-1">API Server Key</label>
          <input id="api_server_key" type="password" autocomplete="off" placeholder="At least 16 characters"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
          <p class="text-xs text-gray-500 mt-1">
            Required for the OpenAI-compatible API. The agent refuses to expose the API without one.
            Generate with <code>openssl rand -hex 32</code>.
          </p>
        </div>
      </div>
    </fieldset>

    <!-- Storage -->
    <fieldset class="border-t border-gray-200 pt-5">
      <legend class="text-sm font-semibold uppercase tracking-wide text-gray-500 px-2">Persistent Storage</legend>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
        <div>
          <label for="data_dir" class="block text-sm font-medium text-gray-700 mb-1">Data Directory</label>
          <input id="data_dir" type="text" value="./data"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
          <p class="text-xs text-gray-500 mt-1">Host path backing the agent's /opt/data volume</p>
        </div>
        <div>
          <label for="models_dir" class="block text-sm font-medium text-gray-700 mb-1">Models Directory</label>
          <input id="models_dir" type="text" value="./models"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
          <p class="text-xs text-gray-500 mt-1">Cached model files</p>
        </div>
      </div>
    </fieldset>

    <!-- Agent Settings -->
    <fieldset class="border-t border-gray-200 pt-5">
      <legend class="text-sm font-semibold uppercase tracking-wide text-gray-500 px-2">Agent Settings</legend>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
        <div>
          <label for="model_name" class="block text-sm font-medium text-gray-700 mb-1">Model Name</label>
          <input id="model_name" type="text" value="NousResearch/Hermes-3-Llama-3.1-8B"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
        </div>
        <div>
          <label for="api_provider" class="block text-sm font-medium text-gray-700 mb-1">API Provider</label>
          <select id="api_provider"
                  class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
            <option value="huggingface">HuggingFace</option>
            <option value="openai">OpenAI-compatible</option>
            <option value="ollama">Ollama</option>
          </select>
        </div>
        <div>
          <label for="context_size" class="block text-sm font-medium text-gray-700 mb-1">Context Size</label>
          <input id="context_size" type="number" value="8192"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
        </div>
        <div>
          <label for="max_tokens" class="block text-sm font-medium text-gray-700 mb-1">Max Tokens</label>
          <input id="max_tokens" type="number" value="2048"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
        </div>
        <div>
          <label for="temperature" class="block text-sm font-medium text-gray-700 mb-1">Temperature</label>
          <input id="temperature" type="number" step="0.1" min="0" max="2" value="0.7"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
        </div>
        <div>
          <label for="top_p" class="block text-sm font-medium text-gray-700 mb-1">Top P</label>
          <input id="top_p" type="number" step="0.05" min="0" max="1" value="0.9"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
        </div>
      </div>
    </fieldset>

    <!-- Provider Credentials -->
    <fieldset class="border-t border-gray-200 pt-5">
      <legend class="text-sm font-semibold uppercase tracking-wide text-gray-500 px-2">Provider Credentials</legend>
      <div class="space-y-4 mt-2">
        <div>
          <label for="hf_token" class="block text-sm font-medium text-gray-700 mb-1">HuggingFace Token</label>
          <input id="hf_token" type="password" autocomplete="off" placeholder="hf_xxxxxxxxxxxxx (optional)"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
          <p class="text-xs text-gray-500 mt-1">Required for private models or the HF Inference API</p>
        </div>
        <div>
          <label for="openai_api_key" class="block text-sm font-medium text-gray-700 mb-1">OpenAI API Key</label>
          <input id="openai_api_key" type="password" autocomplete="off" placeholder="sk-xxxxxxxxxxxxx (optional)"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
        </div>
        <div>
          <label for="openai_base_url" class="block text-sm font-medium text-gray-700 mb-1">OpenAI Base URL</label>
          <input id="openai_base_url" type="text" placeholder="https://api.openai.com/v1 (optional)"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
          <p class="text-xs text-gray-500 mt-1">For OpenAI-compatible endpoints</p>
        </div>
        <div>
          <label for="ollama_host" class="block text-sm font-medium text-gray-700 mb-1">Ollama Host</label>
          <input id="ollama_host" type="text" value="http://host.docker.internal:11434"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
          <p class="text-xs text-gray-500 mt-1">Default for Ollama on Docker Desktop</p>
        </div>
      </div>
    </fieldset>

    <!-- Channel Tokens -->
    <fieldset class="border-t border-gray-200 pt-5">
      <legend class="text-sm font-semibold uppercase tracking-wide text-gray-500 px-2">Channel Integrations</legend>
      <p class="text-xs text-gray-500 mt-2 mb-4">
        Get tokens from Telegram @BotFather, the Discord Developer Portal, or Slack API Apps.
      </p>
      <div class="space-y-4">
        <div>
          <label for="telegram_bot_token" class="block text-sm font-medium text-gray-700 mb-1">Telegram Bot Token</label>
          <input id="telegram_bot_token" type="password" autocomplete="off" placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
        </div>
        <div>
          <label for="discord_bot_token" class="block text-sm font-medium text-gray-700 mb-1">Discord Bot Token</label>
          <input id="discord_bot_token" type="password" autocomplete="off" placeholder="your_discord_bot_token_here"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
        </div>
        <div>
          <label for="slack_bot_token" class="block text-sm font-medium text-gray-700 mb-1">Slack Bot Token</label>
          <input id="slack_bot_token" type="password" autocomplete="off" placeholder="xoxb-your-slack-bot-token"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
        </div>
        <div>
          <label for="slack_app_token" class="block text-sm font-medium text-gray-700 mb-1">Slack App Token</label>
          <input id="slack_app_token" type="password" autocomplete="off" placeholder="xapp-1-your-slack-app-token"
                 class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
        </div>
      </div>
    </fieldset>

    <!-- Save -->
    <div class="mt-6 pt-5 border-t border-gray-200">
      <div class="max-w-sm">
        <label for="passphrase" class="block text-sm font-medium text-gray-700 mb-1">Passphrase (encrypt config)</label>
        <input id="passphrase" type="password" autocomplete="off" placeholder="Choose a passphrase"
               class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
        <p class="text-xs text-gray-500 mt-1">Encrypts the config file on disk. You will need it to load it again.</p>
      </div>

      <div class="mt-5 flex flex-wrap items-center gap-3">
        <button id="btn-save-config" type="button"
                class="bg-green-600 hover:bg-green-700 text-white font-medium py-2.5 px-6 rounded-lg shadow transition-colors">
          <i class="fas fa-save mr-2"></i> Save Encrypted Config
        </button>
        <button id="btn-test-config" type="button"
                class="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 px-6 rounded-lg shadow transition-colors">
          <i class="fas fa-flask mr-2"></i> Test Config
        </button>
      </div>
      <div id="config-result" class="mt-3 text-sm font-medium"></div>
    </div>
  </div>
</div>
"""


def docker_control() -> str:
    """Docker control tab: start/stop/status and log viewer."""
    return f"""
<div class="max-w-6xl mx-auto space-y-6">
  <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
    <h2 class="text-xl font-bold text-gray-800 mb-4">Docker Control</h2>

{_action_buttons()}
{_job_panel()}

    <div class="mt-6">
{_status_card("docker-status-card")}
    </div>
  </div>

  <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
    <h2 class="text-lg font-bold text-gray-800 mb-4">Container Logs</h2>
    <div class="bg-gray-900 rounded-md p-4 overflow-auto h-96 font-mono text-xs text-gray-300 whitespace-pre-wrap" id="logs-viewer">
      Click "Refresh Logs" to view container output.
    </div>
    <div class="mt-4 flex gap-2">
      <button
        type="button"
        id="btn-refresh-logs"
        class="bg-gray-600 hover:bg-gray-700 text-white text-sm font-medium py-2 px-4 rounded-lg"
      >
        Refresh Logs
      </button>
    </div>
  </div>
</div>
"""


def state_management() -> str:
    """State management: backup, restore, state report."""
    return """
<div class="max-w-4xl mx-auto space-y-6">
  <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
    <h2 class="text-xl font-bold text-gray-800 mb-4">State Management</h2>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
      <button
        hx-post="/state/backup?reason=manual"
        hx-target="#state-result"
        hx-swap="beforeend"
        class="bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-lg shadow transition-colors"
      >
        <i class="fas fa-save mr-2"></i> Create Backup
      </button>
      <button
        hx-post="/state/restore"
        hx-target="#state-result"
        hx-swap="beforeend"
        class="bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 px-6 rounded-lg shadow transition-colors"
      >
        <i class="fas fa-undo mr-2"></i> Restore Backup
      </button>
    </div>
    <div id="state-result" class="h-6 text-sm font-medium"></div>
  </div>

  <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
    <h2 class="text-lg font-bold text-gray-800 mb-4">State Report</h2>
    <button
      hx-get="/state/report"
      hx-target="#report-content"
      hx-swap="innerHTML"
      class="bg-gray-600 hover:bg-gray-700 text-white text-sm font-medium py-2 px-4 rounded-lg mb-4"
    >
      Refresh Report
    </button>
    <pre id="report-content" class="bg-gray-50 p-4 rounded-lg text-sm font-mono overflow-auto border border-gray-200">
Click "Refresh Report" to view persistent state paths and status.
    </pre>
  </div>
</div>
"""


def system_info() -> str:
    """System info diagnostics."""
    return """
<div class="max-w-4xl mx-auto space-y-6">
  <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
    <h2 class="text-xl font-bold text-gray-800 mb-4">System Information</h2>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="p-3 bg-gray-50 rounded-lg">
        <p class="text-xs text-gray-500 uppercase font-semibold mb-1">Platform</p>
        <p class="text-sm text-gray-800" id="sys-platform">Loading...</p>
      </div>
      <div class="p-3 bg-gray-50 rounded-lg">
        <p class="text-xs text-gray-500 uppercase font-semibold mb-1">Architecture</p>
        <p class="text-sm text-gray-800" id="sys-arch">Loading...</p>
      </div>
      <div class="p-3 bg-gray-50 rounded-lg">
        <p class="text-xs text-gray-500 uppercase font-semibold mb-1">Python Version</p>
        <p class="text-sm text-gray-800" id="sys-python">Loading...</p>
      </div>
      <div class="p-3 bg-gray-50 rounded-lg">
        <p class="text-xs text-gray-500 uppercase font-semibold mb-1">Hostname</p>
        <p class="text-sm text-gray-800" id="sys-hostname">Loading...</p>
      </div>
    </div>
  </div>
</div>
"""


TAB_REGISTRY = {
    "dashboard": dashboard,
    "config": config,
    "docker": docker_control,
    "state": state_management,
    "system": system_info,
}


def render_tab(tab_name: str) -> str:
    """Return HTML for the requested tab, or a 404-style message."""
    renderer = TAB_REGISTRY.get(tab_name)
    if renderer is None:
        return "<p class='text-gray-500'>Unknown tab.</p>"
    return renderer()
