import sys
import argparse
import json
from dataclasses import asdict
from pathlib import Path

from researchflow.core.config import get_config_sources, load_config, update_config_file, write_default_config
from researchflow.core.slack_setup import (
    check_slack_target,
    list_slack_channels,
    list_slack_users,
    run_interactive_slack_setup,
    setup_dm_by_name,
)
from .handler import execute_script_with_alarm

def _mask_secret(value):
    if not value:
        return value
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def main():
    parser = argparse.ArgumentParser(
        description="Executes a Python script and sends a Slack notification with the results.",
        prog="alarm"
    )
    parser.add_argument("script_to_run", nargs="?", help="The Python script to execute (e.g., path/to/your_script.py).")
    parser.add_argument("script_arguments", nargs=argparse.REMAINDER,
                        help="Arguments to be passed to the target script.")
    parser.add_argument(
        "--log",
        action="store_true",
        help="Enable logging of script stdout/stderr to a file under <script_dir>/logs or --log-dir. "
             "The script will be run in a way that mimics nohup behavior (detached, SIGHUP ignored on Unix)."
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="With --log, keep alarm in the foreground and wait for the target script. Useful for shell concurrency control.",
    )
    parser.add_argument("--config", help="Path to a ResearchFlow JSON config file.")
    parser.add_argument("--log-dir", help="Directory for --log output. Defaults to <script_dir>/logs.")
    parser.add_argument("--set-log-dir", metavar="PATH", help="Save a default log directory to ResearchFlow config and exit.")
    parser.add_argument(
        "--configure-slack",
        action="store_true",
        help="Interactively choose a Slack channel or DM target and save it to config.",
    )
    parser.add_argument("--list-slack-channels", action="store_true", help="List Slack channels visible to the configured bot token.")
    parser.add_argument("--list-slack-users", action="store_true", help="List Slack users visible to the configured bot token.")
    parser.add_argument("--check-slack-target", action="store_true", help="Inspect the configured or provided Slack channel/DM target without sending a message.")
    parser.add_argument("--setup", metavar="NAME", help="Set your Slack DM target by name, save it, then run the bundled sample experiment as a test.")
    parser.add_argument("--setup-dm", metavar="NAME", help=argparse.SUPPRESS)
    parser.add_argument("--quickstart-dm", metavar="NAME", help=argparse.SUPPRESS)
    parser.add_argument(
        "--init-config",
        nargs="?",
        const="",
        metavar="PATH",
        help="Create a default ResearchFlow config file. Defaults to ~/.config/researchflow/config.json.",
    )
    parser.add_argument("--print-config", action="store_true", help="Print the resolved notification config with secrets masked.")
    parser.add_argument(
        "--destination",
        choices=["auto", "channel", "dm", "webhook", "off"],
        help="Slack delivery mode. Defaults to config/env auto detection.",
    )
    parser.add_argument("--channel", help="Slack channel ID or name for this run, e.g. C0123456789.")
    parser.add_argument("--dm", metavar="USER_ID", help="Slack user ID to DM for this run, e.g. U0123456789.")
    parser.add_argument("--team-id", help="Slack workspace/team ID, useful for org-wide tokens, e.g. T0123456789.")
    parser.add_argument("--bot-token", help="Slack bot token for this run. Prefer .env or config for normal use.")
    parser.add_argument("--webhook-url", help="Legacy Slack incoming webhook URL for this run.")
    parser.add_argument("--gpu-info", dest="include_gpu", action="store_true", default=None, help="Include nvidia-smi GPU/process context.")
    parser.add_argument("--no-gpu-info", dest="include_gpu", action="store_false", help="Disable GPU/process context.")
    parser.add_argument("--mention-user", dest="mention_user", action="store_true", default=None, help="Mention the configured DM user in the Slack fallback text.")
    parser.add_argument("--no-mention-user", dest="mention_user", action="store_false", help="Disable Slack user mention for this run.")

    if len(sys.argv) <= 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
        
    args = parser.parse_args(sys.argv[1:])

    if args.init_config is not None:
        target_path = args.init_config or None
        try:
            written_path = write_default_config(target_path)
            sys.stdout.write(f"[AlarmCLI] Wrote default config: {written_path}\n")
            sys.exit(0)
        except FileExistsError as e:
            sys.stderr.write(f"[AlarmCLI] {e}\n")
            sys.exit(1)

    if args.set_log_dir:
        written_path = update_config_file({"log_dir": args.set_log_dir}, path=args.config)
        sys.stdout.write(f"[AlarmCLI] Saved log_dir={args.set_log_dir} to {written_path}\n")
        sys.exit(0)

    destination = args.destination
    if args.channel and args.dm:
        sys.stderr.write("[AlarmCLI] Use either --channel or --dm, not both.\n")
        sys.exit(1)
    if args.channel and destination is None:
        destination = "channel"
    if args.dm and destination is None:
        destination = "dm"

    if args.configure_slack:
        sys.exit(
            run_interactive_slack_setup(
                config_path=args.config,
                bot_token=args.bot_token,
                team_id=args.team_id,
                destination=destination,
            )
        )

    if args.setup_dm:
        sys.exit(
            setup_dm_by_name(
                name_query=args.setup_dm,
                config_path=args.config,
                bot_token=args.bot_token,
                team_id=args.team_id,
            )
        )

    setup_test_name = args.setup or args.quickstart_dm
    if setup_test_name:
        setup_result = setup_dm_by_name(
            name_query=setup_test_name,
            config_path=args.config,
            bot_token=args.bot_token,
            team_id=args.team_id,
        )
        if setup_result != 0:
            sys.exit(setup_result)

        sample_script_path = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "sample_experiment.py"
        notification_config = load_config(
            config_path=args.config,
            slack_bot_token=args.bot_token,
            slack_team_id=args.team_id,
            include_gpu=False,
            log_dir=args.log_dir,
        )
        return_code = execute_script_with_alarm(
            str(sample_script_path),
            ["--epochs", "1", "--total-runtime-factor", "0"],
            [str(sample_script_path), "--epochs", "1", "--total-runtime-factor", "0"],
            enable_logging=False,
            detach_logging=True,
            notification_config=notification_config,
        )
        sys.exit(return_code)

    if args.list_slack_channels:
        sys.exit(list_slack_channels(config_path=args.config, bot_token=args.bot_token, team_id=args.team_id))

    if args.list_slack_users:
        sys.exit(list_slack_users(config_path=args.config, bot_token=args.bot_token, team_id=args.team_id))

    if args.check_slack_target:
        sys.exit(
            check_slack_target(
                channel_id=args.channel,
                user_id=args.dm,
                config_path=args.config,
                bot_token=args.bot_token,
                team_id=args.team_id,
            )
        )

    notification_config = load_config(
        config_path=args.config,
        slack_destination=destination,
        slack_channel=args.channel,
        slack_user_id=args.dm,
        slack_bot_token=args.bot_token,
        slack_webhook_url=args.webhook_url,
        slack_team_id=args.team_id,
        log_dir=args.log_dir,
        include_gpu=args.include_gpu,
        mention_user=args.mention_user,
    )

    if args.print_config:
        config_dict = asdict(notification_config)
        config_dict["slack_bot_token"] = _mask_secret(config_dict.get("slack_bot_token"))
        config_dict["slack_webhook_url"] = _mask_secret(config_dict.get("slack_webhook_url"))
        config_dict["config_location"] = get_config_sources(args.config)
        sys.stdout.write(json.dumps(config_dict, indent=2))
        sys.stdout.write("\n")
        if not args.script_to_run:
            sys.exit(0)

    if not args.script_to_run:
        parser.print_help(sys.stderr)
        sys.exit(1)

    target_script_path = args.script_to_run
    target_script_args = args.script_arguments
    enable_logging = args.log
    detach_logging = not args.wait
    
    alarm_command_args_for_display = [target_script_path] + target_script_args

    return_code = execute_script_with_alarm(
        target_script_path,
        target_script_args,
        alarm_command_args_for_display,
        enable_logging=enable_logging,
        detach_logging=detach_logging,
        notification_config=notification_config,
    )
    sys.exit(return_code)

if __name__ == '__main__':
    main()
