import sys
import argparse
from .handler import execute_script_with_alarm

def main():
    parser = argparse.ArgumentParser(
        description="Executes a Python script and sends a Slack notification with the results.",
        prog="alarm"
    )
    parser.add_argument("script_to_run", help="The Python script to execute (e.g., path/to/your_script.py).")
    parser.add_argument("script_arguments", nargs=argparse.REMAINDER,
                        help="Arguments to be passed to the target script.")
    parser.add_argument(
        "--log",
        action="store_true",
        help="Enable logging of script stdout/stderr to a file in the current directory. "
             "The script will be run in a way that mimics nohup behavior (detached, SIGHUP ignored on Unix)."
    )

    if len(sys.argv) <= 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
        
    args = parser.parse_args(sys.argv[1:])

    target_script_path = args.script_to_run
    target_script_args = args.script_arguments
    enable_logging = args.log
    
    alarm_command_args_for_display = [target_script_path] + target_script_args

    return_code = execute_script_with_alarm(
        target_script_path,
        target_script_args,
        alarm_command_args_for_display,
        enable_logging=enable_logging
    )
    sys.exit(return_code)

if __name__ == '__main__':
    main()