/* Hermes Setup web UI — frontend behaviour.
 *
 * Docker lifecycle operations run as background jobs on the server so the
 * browser gets an immediate response and can poll for live progress.  The
 * previous implementation posted to /docker/start and swapped the response
 * into the page, which produced no feedback at all while `docker compose up`
 * pulled and built the image.
 */

// ----------------------------------------------------------------
// Shared config field list — the ids rendered by the config tab.
// ----------------------------------------------------------------
var CONFIG_FIELDS = [
    'docker_image', 'api_port', 'dashboard_port', 'enable_dashboard',
    'api_server_key', 'memory_limit', 'cpus_limit', 'data_dir', 'models_dir',
    'model_name', 'api_provider', 'context_size', 'temperature', 'top_p',
    'max_tokens', 'hf_token', 'openai_api_key', 'openai_base_url',
    'ollama_host', 'telegram_bot_token', 'discord_bot_token',
    'slack_bot_token', 'slack_app_token'
];

function setResult(el, message, ok) {
    if (!el) return;
    el.textContent = message;
    el.className = 'mt-4 h-6 text-sm font-medium ' + (ok ? 'text-green-600' : 'text-red-600');
}

function collectConfig() {
    var config = {};
    CONFIG_FIELDS.forEach(function (f) {
        var el = document.getElementById(f);
        if (el && el.value !== '') config[f] = el.value;
    });
    return config;
}

function populateConfig(config) {
    CONFIG_FIELDS.forEach(function (f) {
        var el = document.getElementById(f);
        if (el && config[f] !== undefined && config[f] !== null) {
            el.value = config[f];
        }
    });
    // Pre-fill the save passphrase for convenience
    var passEl = document.getElementById('passphrase');
    var loadPassEl = document.getElementById('load-passphrase');
    if (passEl && loadPassEl) passEl.value = loadPassEl.value;
}

// ----------------------------------------------------------------
// Job runner
// ----------------------------------------------------------------
var jobTimer = null;

function setButtonsBusy(busy) {
    document.querySelectorAll('[data-docker-action]').forEach(function (b) {
        b.disabled = busy;
    });
}

function postJob(action) {
    var panel = document.getElementById('job-panel');
    var titleEl = document.getElementById('job-title');
    var outputEl = document.getElementById('job-output');
    var elapsedEl = document.getElementById('job-elapsed');
    if (!panel || !titleEl || !outputEl) return;

    panel.classList.remove('hidden');
    titleEl.textContent = 'Starting...';
    titleEl.className = 'text-sm font-medium text-blue-800';
    outputEl.textContent = '';
    if (elapsedEl) elapsedEl.textContent = '0s';
    setButtonsBusy(true);

    fetch('/docker/' + action, { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (!data || !data.job_id) {
                setButtonsBusy(false);
                titleEl.textContent = '✗ Failed to start operation';
                titleEl.className = 'text-sm font-medium text-red-700';
                return;
            }
            pollJob(data.job_id, action, titleEl, outputEl, elapsedEl);
        })
        .catch(function (e) {
            setButtonsBusy(false);
            titleEl.textContent = '✗ Request failed: ' + e.message;
            titleEl.className = 'text-sm font-medium text-red-700';
        });
}

function pollJob(jobId, action, titleEl, outputEl, elapsedEl) {
    var elapsed = 0;
    var clock = setInterval(function () {
        elapsed += 1;
        if (elapsedEl) elapsedEl.textContent = elapsed + 's';
    }, 1000);

    var label = action.charAt(0).toUpperCase() + action.slice(1);

    var finish = function (data) {
        clearInterval(clock);
        if (jobTimer) { clearInterval(jobTimer); jobTimer = null; }
        var ok = data.ok === true;
        titleEl.textContent = (ok ? '✓ ' : '✗ ') + label + (ok ? ' complete' : ' failed');
        titleEl.className = 'text-sm font-medium ' + (ok ? 'text-green-700' : 'text-red-700');
        var lines = data.output || [];
        outputEl.textContent = lines.join('\n');
        if (data.message) {
            outputEl.textContent += (outputEl.textContent ? '\n\n' : '') + data.message;
        }
        setButtonsBusy(false);
        refreshStatus();
        refreshContainerStatus();
    };

    var tick = function () {
        fetch('/jobs/' + jobId)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.status === 'succeeded' || data.status === 'failed') {
                    finish(data);
                    return;
                }
                titleEl.textContent = 'Running...';
                var lines = data.output || [];
                outputEl.textContent = lines.length ? lines.join('\n') : '(waiting for output...)';
            })
            .catch(function (e) {
                finish({ ok: false, message: e.message, output: [] });
            });
    };

    tick();
    jobTimer = setInterval(tick, 1200);
}

// ----------------------------------------------------------------
// Docker status card
// ----------------------------------------------------------------
function updateStatus(key, text, colorClass) {
    document.querySelectorAll('[data-status="' + key + '"]').forEach(function (el) {
        el.textContent = text;
        el.className = 'text-sm font-medium ' + (colorClass || 'text-gray-500');
    });
}

function refreshStatus() {
    fetch('/docker/status')
        .then(function (r) { return r.json(); })
        .then(function (d) {
            updateStatus('docker', d.available ? 'Available' : 'Down',
                d.available ? 'text-green-600' : 'text-red-600');
            updateStatus('compose', d.compose_available ? 'Available' : 'Down',
                d.compose_available ? 'text-green-600' : 'text-red-600');
        })
        .catch(function () { /* leave previous state */ });
}

function refreshContainerStatus() {
    fetch('/docker/status-full')
        .then(function (r) { return r.json(); })
        .then(function (d) {
            updateStatus('container', d.running ? 'Running' : 'Stopped',
                d.running ? 'text-green-600' : 'text-gray-500');
            var viewer = document.getElementById('logs-viewer');
            if (viewer && d.logs) viewer.textContent = d.logs.slice(-4000);
        })
        .catch(function () { /* leave previous state */ });
}

// ----------------------------------------------------------------
// Config save / load
// ----------------------------------------------------------------
function saveConfig() {
    var saveBtn = document.getElementById('btn-save-config');
    var result = document.getElementById('config-result');
    var passphraseEl = document.getElementById('passphrase');
    var passphrase = passphraseEl ? passphraseEl.value : '';
    if (!passphrase) {
        setResult(result, 'Please enter a passphrase', false);
        return;
    }
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Saving...';
    fetch('/config/save', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({passphrase: passphrase, config: collectConfig()})
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
        if (data.ok) setResult(result, 'Config saved to ' + data.path, true);
        else setResult(result, 'Save failed: ' + (data.detail || 'unknown error'), false);
    })
    .catch(function (e) { setResult(result, 'Save failed: ' + e.message, false); })
    .finally(function () {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="fas fa-save mr-2"></i> Save Encrypted Config';
    });
}

function loadConfig(silent) {
    var loadBtn = document.getElementById('btn-load-config');
    var result = document.getElementById('config-result');
    var passphraseEl = document.getElementById('load-passphrase');
    var passphrase = passphraseEl ? passphraseEl.value : '';
    if (!passphrase) {
        if (!silent) setResult(result, 'Please enter passphrase to load', false);
        return;
    }
    if (loadBtn) {
        loadBtn.disabled = true;
        loadBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Loading...';
    }
    fetch('/config/load', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({passphrase: passphrase})
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
        if (data.ok && data.config) {
            populateConfig(data.config);
            setResult(result, 'Config loaded successfully', true);
            var section = document.getElementById('load-section');
            if (section) section.style.display = 'none';
        } else {
            if (!silent) {
                setResult(result, 'Load failed: ' + (data.detail || 'wrong passphrase?'), false);
            }
        }
    })
    .catch(function (e) {
        if (!silent) setResult(result, 'Load failed: ' + e.message, false);
    })
    .finally(function () {
        if (loadBtn) {
            loadBtn.disabled = false;
            loadBtn.innerHTML = '<i class="fas fa-folder-open mr-2"></i> Load Config';
        }
    });
}

// ----------------------------------------------------------------
// Tab lifecycle — HTMX swaps fragments in, so bind after every swap.
// ----------------------------------------------------------------
function bindTab() {
    document.querySelectorAll('[data-docker-action]').forEach(function (btn) {
        if (btn.dataset.bound === '1') return;
        btn.dataset.bound = '1';
        btn.addEventListener('click', function () {
            postJob(btn.dataset.dockerAction);
        });
    });

    var refreshBtn = document.getElementById('btn-refresh-logs');
    if (refreshBtn && refreshBtn.dataset.bound !== '1') {
        refreshBtn.dataset.bound = '1';
        refreshBtn.addEventListener('click', refreshContainerStatus);
    }

    var saveBtn = document.getElementById('btn-save-config');
    if (saveBtn && saveBtn.dataset.bound !== '1') {
        saveBtn.dataset.bound = '1';
        saveBtn.addEventListener('click', saveConfig);
    }

    var loadBtn = document.getElementById('btn-load-config');
    if (loadBtn && loadBtn.dataset.bound !== '1') {
        loadBtn.dataset.bound = '1';
        loadBtn.addEventListener('click', loadConfig);
    }

    // Load the saved config as soon as the user enters a passphrase, so the
    // form does not show stale defaults when there is one to restore.
    // The input is rebuilt on each HTMX tab swap, so binding it here is
    // safe — each new element gets its own single handler.
    var passphraseEl = document.getElementById('load-passphrase');
    if (passphraseEl) {
        passphraseEl.addEventListener('change', function () {
            loadConfig(true);
        });
        passphraseEl.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                loadConfig(false);
            }
        });
        // If we already know the passphrase from earlier in this session,
        // restore the config straight away.
        if (passphraseEl.value) loadConfig(true);
    }

    refreshStatus();
    refreshContainerStatus();

    // Reveal the "load existing config" block if a config file exists, and
    // restore the already-loaded config when the session knows the passphrase.
    var loadSection = document.getElementById('load-section');
    if (loadSection) {
        fetch('/config/status')
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (!d.ok) return;
                if (d.alreadyLoaded) {
                    // Already opened in this session — no need to ask again.
                    loadSection.style.display = 'none';
                    restoreLoadedConfig();
                } else if (d.exists) {
                    loadSection.style.display = 'block';
                }
            })
            .catch(function () { /* ignore */ });
    }
}

// Restores the config the server already has in memory (the passphrase was
// entered earlier in this session), so the form shows the real values
// instead of the defaults.
function restoreLoadedConfig() {
    fetch('/config/current')
        .then(function (r) { return r.json(); })
        .then(function (d) {
            if (d.ok && d.config) populateConfig(d.config);
        })
        .catch(function () { /* ignore */ });
}

// ----------------------------------------------------------------
// Connection status
// ----------------------------------------------------------------
function setConnectionStatus(connected) {
    var el = document.getElementById('connection-status');
    if (!el) return;
    el.innerHTML = '<i class="fas fa-circle mr-1"></i> ' + (connected ? 'Connected' : 'Disconnected');
    el.className = 'animate-pulse inline-flex items-center px-2 py-1 rounded-full text-xs ' +
        (connected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800');
}

// ----------------------------------------------------------------
// Boot
// ----------------------------------------------------------------
document.addEventListener('DOMContentLoaded', function () {
    htmx.ajax('GET', '/tab/dashboard', {
        target: document.getElementById('tab-content'),
        swap: 'innerHTML'
    });
    var dashBtn = document.querySelector('[hx-get="/tab/dashboard"]');
    if (dashBtn) dashBtn.classList.add('bg-blue-50', 'text-blue-700', 'font-medium');
});

document.addEventListener('htmx:afterSwap', function () {
    document.querySelectorAll('.tab-btn').forEach(function (btn) {
        btn.classList.remove('bg-blue-50', 'text-blue-700', 'font-medium');
    });
    var path = window.location.pathname;
    if (path.indexOf('/tab/') === 0) {
        var tabName = path.substring(5);
        var btn = document.querySelector('[hx-get="/tab/' + tabName + '"]');
        if (btn) btn.classList.add('bg-blue-50', 'text-blue-700', 'font-medium');
    }

    bindTab();
    setConnectionStatus(true);
});

setInterval(function () {
    fetch('/health', {method: 'HEAD'})
        .then(function () { setConnectionStatus(true); })
        .catch(function () { setConnectionStatus(false); });
}, 5000);
