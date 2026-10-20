"""HTML fragments rendered by HTMX for each settings tab.

Each fragment is a self-contained block of HTML inserted into the main
``#tab-content`` container.  They call the FastAPI backend endpoints for
real data instead of duplicating logic in JavaScript.
"""

from __future__ import annotations

# Each tab id -> static HTML fragment path (relative to the static dir).
# Static fragments are served directly; dynamic ones below are generated
# as Python strings so they can embed server-side values if needed later.


def dashboard() -> str:
    """Dashboard: quick status + start/stop buttons + health card."""
    return """
<div class="max-w-6xl mx-auto space-y-6">
  <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
    <h2 class="text-xl font-bold text-gray-800 mb-4">Quick Actions</h2>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <button
        hx-post="/docker/start"
        hx-target="#docker-card"
        hx-swap="outerHTML"
        hx-indicator=".htmx-indicator"
        class="bg-green-600 hover:bg-green-700 text-white font-medium py-3 px-6 rounded-lg shadow transition-colors flex items-center justify-center gap-2"
      >
        <i class="fas fa-play"></i> Start Hermes
      </button>
      <button
        hx-post="/docker/restart"
        hx-target="#docker-card"
        hx-swap="outerHTML"
        class="bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-lg shadow transition-colors flex items-center justify-center gap-2"
      >
        <i class="fas fa-redo"></i> Restart
      </button>
      <button
        hx-post="/docker/stop"
        hx-target="#docker-card"
        hx-swap="outerHTML"
        class="bg-red-600 hover:bg-red-700 text-white font-medium py-3 px-6 rounded-lg shadow transition-colors flex items-center justify-center gap-2"
      >
        <i class="fas fa-stop"></i> Stop
      </button>
    </div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <div id="docker-card" class="lg:col-span-2 bg-white p-6 rounded-xl shadow-sm border border-gray-200">
      <h2 class="text-lg font-bold text-gray-800 mb-4 flex items-center">
        <i class="fas fa-docker text-blue-600 mr-2"></i>
        Docker Status
      </h2>
      <div class="space-y-3">
        <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
          <span class="text-gray-600">Docker Engine</span>
          <span class="w-2 h-2 rounded-full bg-yellow-400 animate-pulse"></span>
        </div>
        <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
          <span class="text-gray-600">Docker Compose</span>
          <span class="w-2 h-2 rounded-full bg-yellow-400 animate-pulse"></span>
        </div>
        <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
          <span class="text-gray-600">Container State</span>
          <span class="w-2 h-2 rounded-full bg-yellow-400 animate-pulse"></span>
        </div>
      </div>
      <div class="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
        <p class="text-sm text-blue-700">
          <i class="fas fa-info-circle mr-2"></i>
          Docker status will appear here after the backend is running.
          Click "Start Hermes" to begin.
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

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Docker Settings -->
      <div class="flex flex-col">
        <label class="text-sm font-medium text-gray-700 mb-1">Docker Image</label>
        <input id="docker_image" type="text" value="nousresearch/hermes-agent:latest" class="border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
      </div>
      <div class="flex flex-col">
        <label class="text-sm font-medium text-gray-700 mb-1">Host Port</label>
        <input id="host_port" type="number" value="8000" class="border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
      </div>
      <div class="flex flex-col">
        <label class="text-sm font-medium text-gray-700 mb-1">Container Port</label>
        <input id="container_port" type="number" value="8000" class="border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
      </div>
      <div class="flex flex-col">
        <label class="text-sm font-medium text-gray-700 mb-1">Memory Limit</label>
        <input id="memory_limit" type="text" value="4g" class="border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
      </div>
      <div class="flex flex-col">
        <label class="text-sm font-medium text-gray-700 mb-1">CPU Limit</label>
        <input id="cpus_limit" type="number" step="0.5" value="2" class="border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
      </div>
      <!-- Data Paths -->
      <div class="flex flex-col">
        <label class="text-sm font-medium text-gray-700 mb-1">Data Directory</label>
        <input id="data_dir" type="text" value="./data" class="border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
      </div>
      <div class="flex flex-col">
        <label class="text-sm font-medium text-gray-700 mb-1">Models Directory</label>
        <input id="models_dir" type="text" value="./models" class="border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
      </div>
      <!-- Hermes Agent Settings -->
      <div class="flex flex-col">
        <label class="text-sm font-medium text-gray-700 mb-1">Model Name</label>
        <input id="model_name" type="text" value="NousResearch/Hermes-3-Llama-3.1-8B" class="border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
      </div>
      <div class="flex flex-col">
        <label class="text-sm font-medium text-gray-700 mb-1">API Provider</label>
        <select id="api_provider" class="border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
          <option value="huggingface">HuggingFace</option>
          <option value="openai">OpenAI-compatible</option>
          <option value="ollama">Ollama</option>
        </select>
      </div>
      <div class="flex flex-col">
        <label class="text-sm font-medium text-gray-700 mb-1">Context Size</label>
        <input id="context_size" type="number" value="8192" class="border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
      </div>
      <div class="flex flex-col">
        <label class="text-sm font-medium text-gray-700 mb-1">Temperature</label>
        <input id="temperature" type="number" step="0.1" min="0" max="2" value="0.7" class="border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
      </div>
      <div class="flex flex-col">
        <label class="text-sm font-medium text-gray-700 mb-1">Top P</label>
        <input id="top_p" type="number" step="0.05" min="0" max="1" value="0.9" class="border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
      </div>
      <div class="flex flex-col">
        <label class="text-sm font-medium text-gray-700 mb-1">Max Tokens</label>
        <input id="max_tokens" type="number" value="2048" class="border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
      </div>
      <!-- API Keys -->
      <div class="md:col-span-2">
        <label class="block text-sm font-medium text-gray-700 mb-2">HuggingFace Token</label>
        <input id="hf_token" type="password" placeholder="hf_xxxxxxxxxxxxx (optional)" class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
        <p class="text-xs text-gray-500 mt-1">Required for private models or HF Inference API</p>
      </div>
      <div class="md:col-span-2">
        <label class="block text-sm font-medium text-gray-700 mb-2">OpenAI API Key</label>
        <input id="openai_api_key" type="password" placeholder="sk-xxxxxxxxxxxxx (optional)" class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
      </div>
      <div class="md:col-span-2">
        <label class="block text-sm font-medium text-gray-700 mb-2">OpenAI Base URL</label>
        <input id="openai_base_url" type="text" placeholder="https://api.openai.com/v1 (optional)" class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
        <p class="text-xs text-gray-500 mt-1">For OpenAI-compatible endpoints</p>
      </div>
      <div class="md:col-span-2">
        <label class="block text-sm font-medium text-gray-700 mb-2">Ollama Host</label>
        <input id="ollama_host" type="text" value="http://host.docker.internal:11434" class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
        <p class="text-xs text-gray-500 mt-1">Default for Ollama on Docker Desktop</p>
      </div>
      <!-- Channel Tokens -->
      <div class="md:col-span-2 border-t border-gray-200 pt-4">
        <h3 class="text-lg font-semibold text-gray-800 mb-3">Channel Integrations</h3>
        <p class="text-xs text-gray-500 mb-3">Get tokens from: Telegram @BotFather, Discord Developer Portal, Slack API Apps</p>
      </div>
      <div class="md:col-span-2">
        <label class="block text-sm font-medium text-gray-700 mb-2">Telegram Bot Token</label>
        <input id="telegram_bot_token" type="password" placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz" class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
      </div>
      <div class="md:col-span-2">
        <label class="block text-sm font-medium text-gray-700 mb-2">Discord Bot Token</label>
        <input id="discord_bot_token" type="password" placeholder="your_discord_bot_token_here" class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
      </div>
      <div class="md:col-span-2">
        <label class="block text-sm font-medium text-gray-700 mb-2">Slack Bot Token</label>
        <input id="slack_bot_token" type="password" placeholder="xoxb-your-slack-bot-token" class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
      </div>
      <div class="md:col-span-2">
        <label class="block text-sm font-medium text-gray-700 mb-2">Slack App Token</label>
        <input id="slack_app_token" type="password" placeholder="xapp-1-your-slack-app-token" class="w-full border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
      </div>
    </div>

    <div class="mt-6 pt-4 border-t border-gray-200">
      <label class="text-sm font-medium text-gray-700 mb-1">Passphrase (encrypt config)</label>
      <input id="passphrase" type="password" placeholder="Choose a passphrase" class="border border-gray-300 rounded-md p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none w-full max-w-xs">
      <p class="text-xs text-gray-500 mt-1">Used to encrypt the config file on disk.</p>
    </div>

    <div class="mt-6">
      <button
        id="btn-save-config"
        class="bg-green-600 hover:bg-green-700 text-white font-medium py-3 px-6 rounded-lg shadow transition-colors"
      >
        <i class="fas fa-save mr-2"></i> Save Encrypted Config
      </button>
      <button
        id="btn-test-config"
        class="bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-lg shadow transition-colors ml-2"
      >
        <i class="fas fa-flask mr-2"></i> Test Config
      </button>
      <div id="config-result" class="mt-4 h-6 text-sm font-medium"></div>
    </div>
  </div>
</div>
"""


def docker_control() -> str:
    """Docker control tab: start/stop/status and log viewer."""
    return """
<div class="max-w-6xl mx-auto space-y-6">
  <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
    <h2 class="text-xl font-bold text-gray-800 mb-4">Docker Control</h2>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <button
        hx-post="/docker/start"
        hx-target="#docker-status-card"
        hx-swap="outerHTML"
        class="bg-green-600 hover:bg-green-700 text-white font-medium py-3 px-6 rounded-lg shadow transition-colors"
      >
        <i class="fas fa-play mr-2"></i> Start Agent
      </button>
      <button
        hx-post="/docker/restart"
        hx-target="#docker-status-card"
        hx-swap="outerHTML"
        class="bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-lg shadow transition-colors"
      >
        <i class="fas fa-redo mr-2"></i> Restart
      </button>
      <button
        hx-post="/docker/stop"
        hx-target="#docker-status-card"
        hx-swap="outerHTML"
        class="bg-red-600 hover:bg-red-700 text-white font-medium py-3 px-6 rounded-lg shadow transition-colors"
      >
        <i class="fas fa-stop mr-2"></i> Stop
      </button>
    </div>

    <div id="docker-status-card" class="space-y-3">
      <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
        <span class="text-gray-600">Docker Engine</span>
        <span class="text-sm font-medium text-yellow-600">Checking...</span>
      </div>
      <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
        <span class="text-gray-600">Docker Compose</span>
        <span class="text-sm font-medium text-yellow-600">Checking...</span>
      </div>
      <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
        <span class="text-gray-600">Container State</span>
        <span class="text-sm font-medium text-yellow-600">Checking...</span>
      </div>
    </div>
  </div>

  <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
    <h2 class="text-lg font-bold text-gray-800 mb-4">Container Logs</h2>
    <div class="bg-gray-900 rounded-md p-4 overflow-auto h-96 font-mono text-xs text-gray-300" id="logs-viewer">
      Click "Refresh Logs" to view container output.
    </div>
    <div class="mt-4 flex gap-2">
      <button
        hx-get="/docker/status-full"
        hx-target="#logs-viewer"
        hx-swap="outerHTML"
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
