"""Bootstrap executed inside the Hermes image; credentials stay out of argv/logs."""

CHANNEL_ENV_KEYS = (
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_ALLOWED_USERS",
    "DISCORD_BOT_TOKEN",
    "DISCORD_ALLOWED_USERS",
    "SLACK_BOT_TOKEN",
    "SLACK_APP_TOKEN",
    "SLACK_ALLOWED_USERS",
)

# Keep this script self-contained: the setup package is not installed in the
# upstream container. Read secrets from its environment, never command arguments.
BOOTSTRAP_SCRIPT = r"""
import json
import os
import pathlib
import re
import sys
import tempfile
import hermes_yaml as yaml

home = pathlib.Path(os.environ.get("HERMES_HOME", "/opt/data"))
runtime = json.loads(sys.argv[1])
keys = json.loads(sys.argv[2])
config_path = home / "config.yaml"
config = yaml.safe_load(config_path.read_text()) if config_path.exists() else {}
config = config or {}
config.update(runtime)

def private_replace(path, content):
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".setup-")
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)

env_path = home / ".env"
lines = env_path.read_text().splitlines() if env_path.exists() else []
# Replace only wizard-owned channel settings; preserve provider keys and other
# profile settings. Empty values deliberately clear previously saved channels.
lines = [line for line in lines
         if not ((match := re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", line))
                 and match.group(1) in keys)]
for key in keys:
    lines.append(key + "=" + json.dumps(os.environ.get(key, "")))
private_replace(env_path, "\n".join(lines) + "\n")
private_replace(config_path, yaml.safe_dump(config))
print("Saved channel credentials in the persistent default profile (values hidden).")
"""
