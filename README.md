# researchflow

`researchflow` wraps a Python experiment with `alarm` and sends a Slack DM or channel message when the process finishes.

Korean README: [readme_ko.md](readme_ko.md)

## Quick Setup

For lab members, the Slack app and `.env` are already prepared. Install the package, set your Slack DM target, and send a test message:

```bash
pip install -e .
alarm --setup "Your Slack Display Name"
```

If no user matches, inspect the exact Slack names:

```bash
alarm --list-slack-users
```

## Quick Usage

Wrap any Python script with `alarm`. Arguments after the script path are passed to your script unchanged.

```bash
alarm script.py --your-arg value
```

Example test command:

```bash
alarm tests/fixtures/sample_experiment.py --epochs 1 --total-runtime-factor 0
```

Use `--log` to run in the background and save stdout/stderr:

```bash
alarm --log script.py --your-arg value
```

Use `--log --wait` when a shell script should wait for the real experiment process:

```bash
alarm --log --wait script.py --your-arg value
```

## Setup

```bash
git clone https://github.com/mjk0618/researchflow.git
cd researchflow
pip install -e .
```

Set your default DM target:

```bash
alarm --setup "Your Slack Display Name"
```

Check the saved config:

```bash
alarm --print-config
```

The user config is saved to:

```text
~/.config/researchflow/config.json
```

`--print-config` also prints the config paths it read and the active write path. `alarm --setup "name"` stores both the detected Slack user ID and the matched Slack display name for easier inspection later.

## Logging

`--log` writes stdout/stderr to a file and starts the script in the background.

```bash
alarm --log train.py --config configs/run.yaml
```

Default log location:

```text
<script_dir>/logs/{YYYYMMDD_HHMMSS_microseconds_KST}_{script_name}.log
```

Use a custom log directory for one run:

```bash
alarm --log --log-dir /path/to/researchflow_logs train.py
```

Save a default log directory:

```bash
alarm --set-log-dir /path/to/researchflow_logs
```

## Useful Commands

Run without Slack:

```bash
alarm --destination off script.py
```

Show resolved config with secrets masked:

```bash
alarm --print-config
```

Verify the current Slack target without sending an experiment message:

```bash
alarm --check-slack-target
```

Control GPU/process snapshot:

```bash
alarm --gpu-info script.py
alarm --no-gpu-info script.py
```

`alarm` uses `nvidia-smi` when available and can include GPU name, VRAM usage, utilization, temperature, active compute PIDs, process owner, and elapsed time.

Clean local test artifacts:

```bash
rm -rf test_artifacts
```

Run multiple alarm-wrapped sample jobs with shell-level concurrency control:

```bash
tests/scripts/alarm_parallel_example.sh 2 8
```

The first argument is the maximum number of logged jobs running at once. The second argument is the total number of runs. The script uses `alarm --log --wait`, so shell `wait` tracks the actual experiment lifetime while stdout/stderr are still saved to log files. Plain `alarm --log` still returns immediately after starting its monitor process.

## Additional Features

### Channel Target

Most lab members should use DM setup. Channel posting is mainly for shared lab/admin notifications.

```bash
alarm --team-id T07CSJGATDW --list-slack-channels
alarm --team-id T07CSJGATDW --channel C08RV70M4FM --check-slack-target
```

Send one run to a channel:

```bash
alarm \
  --destination channel \
  --channel C08RV70M4FM \
  --team-id T07CSJGATDW \
  script.py --your-arg value
```

For private channels, invite the bot first:

```text
/invite @researchflow
```

### Interactive Setup

```bash
alarm --team-id T07CSJGATDW --configure-slack
alarm --team-id T07CSJGATDW --list-slack-users
```

### Slack App Setup

For lab/private distribution, prepare `.env` before handing the package to users:

```bash
RESEARCHFLOW_SLACK_BOT_TOKEN="xoxb-..."
RESEARCHFLOW_SLACK_TEAM_ID="T07CSJGATDW"
```

The shared Slack app needs these bot scopes:

- `chat:write` to send messages
- `im:write` to open DM conversations
- `users:read` for `--setup` and user search
- `channels:read` for public channel listing
- `groups:read` for private channel listing

After changing scopes, reinstall the Slack app to the workspace.

Secrets such as `RESEARCHFLOW_SLACK_BOT_TOKEN` should stay in `.env` or server environment variables. Do not commit them to source code, README files, or package distributions.

## Experiment Metadata

To include parsed arguments in the Slack alarm, call `report_arguments` in your script:

```python
from researchflow.core.utils import report_arguments

args = parser.parse_args()
report_arguments(args)
```
