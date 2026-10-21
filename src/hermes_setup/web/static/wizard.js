'use strict';
const $ = id => document.getElementById(id);
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Check your configuration values.');
  return data;
}
function notice(message) { $('notice').textContent = message; }
function busy(value) { document.querySelectorAll('button').forEach(button => button.disabled = value); }
async function status() {
  const d = await api('/docker/status');
  $('connection').textContent = d.available && d.compose_available ? 'Pi · Docker ready' : 'Docker needs attention';
  if (!d.available || !d.compose_available) notice('Install Docker Engine and Compose on the Pi and give your user Docker access. See README.md.');
  const h = await api('/agent/health');
  $('agent-status').textContent = h.ok ? 'API ready' : 'Not ready';
}
async function poll(id) {
  sessionStorage.setItem('hermes-job', id);
  $('progress').hidden = false;
  busy(true);
  try {
    const job = await api('/jobs/' + id);
    $('output').textContent = (job.output || []).join('\n');
    $('job-title').textContent = job.action + ' · ' + job.status;
    if (job.status === 'failed' || job.status === 'succeeded') {
      sessionStorage.removeItem('hermes-job');
      busy(false);
      if (job.action === 'Set up Hermes') $('ready').hidden = !job.ok;
      if (!job.ok) notice(job.message + '. Review the progress output for recovery steps.');
      status().catch(error => notice(error.message));
    } else setTimeout(() => poll(id), 1500);
  } catch(error) { busy(false); notice(error.message + ' Refresh to reconnect to the operation.'); }
}
const CHANNELS = ['telegram', 'discord', 'slack'];
function channelFields(channel) {
  return [channel + '_bot_token', channel + '_allowed_users'].concat(channel === 'slack' ? ['slack_app_token'] : []);
}
function syncChannel(channel) {
  const enabled = $(channel + '-enabled').checked;
  $(channel + '-fields').hidden = !enabled;
  channelFields(channel).forEach(name => {
    const field = $('setup-form').elements.namedItem(name);
    field.disabled = !enabled;
    field.required = enabled;
  });
}
CHANNELS.forEach(channel => $(channel + '-enabled').addEventListener('change', () => syncChannel(channel)));
$('setup-form').addEventListener('submit', async event => {
  event.preventDefault(); notice(''); busy(true); $('ready').hidden = true;
  const config = Object.fromEntries(new FormData(event.target));
  CHANNELS.forEach(channel => {
    if (!$(channel + '-enabled').checked) channelFields(channel).forEach(name => config[name] = '');
  });
  Object.assign(config, {api_provider:'openai', enable_dashboard:true, dashboard_port:9119});
  try { const job = await api('/setup', {passphrase:$('passphrase').value, config}); await poll(job.job_id); }
  catch(error) { busy(false); notice(error.message); }
});
$('load').onclick = async () => {
  try {
    const data = await api('/config/load', {passphrase:$('unlock-pass').value});
    CHANNELS.forEach(channel => {
      channelFields(channel).forEach(name => $('setup-form').elements.namedItem(name).value = '');
      $(channel + '-enabled').checked = Boolean(data.config[channel + '_bot_token']);
      syncChannel(channel);
    });
    for (const [key,value] of Object.entries(data.config)) {
      const field = $('setup-form').elements.namedItem(key);
      if (field && value != null) field.value = value;
    }
    $('passphrase').value = $('unlock-pass').value;
    $('unlock').hidden = true; notice('Saved settings loaded.');
  } catch(error) { notice(error.message); }
};
document.querySelectorAll('[data-action]').forEach(button => button.onclick = async () => {
  try { busy(true); const job = await api('/docker/' + button.dataset.action, {}); await poll(job.job_id); }
  catch(error) { busy(false); notice(error.message); }
});
$('logs').onclick = async () => {
  try { const data = await api('/docker/logs'); $('progress').hidden = false; $('job-title').textContent='Container logs'; $('output').textContent=data.logs || 'No logs yet.'; }
  catch(error) { notice(error.message); }
};
$('refresh').onclick = () => status().catch(error => notice(error.message));
api('/config/status').then(data => { $('unlock').hidden = !data.exists; if (data.exists) notice('Unlock your saved settings before running setup again.'); }).catch(error => notice(error.message));
status().catch(error => notice(error.message));
const previous = sessionStorage.getItem('hermes-job');
if (previous) poll(previous);
