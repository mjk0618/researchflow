import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Union, Dict, Any

from dotenv import load_dotenv

from .constants import SLACK_WEBHOOK_ENV_KEY, GEMINI_API_KEY_ENV_KEY
from researchflow.alarm.constants import PARSED_ARGS_START_MARKER, PARSED_ARGS_END_MARKER

_dotenv_loaded_globally = False

def ensure_dotenv_is_loaded():
    global _dotenv_loaded_globally
    if _dotenv_loaded_globally:
        return

    current_working_directory_env = Path.cwd() / ".env"
    package_root_env = Path(__file__).resolve().parent.parent.parent / ".env"

    if current_working_directory_env.exists():
        load_dotenv(dotenv_path=current_working_directory_env, override=True)
    elif package_root_env.exists():
        load_dotenv(dotenv_path=package_root_env, override=True)

    _dotenv_loaded_globally = True

def get_slack_webhook_url_from_env():
    ensure_dotenv_is_loaded()
    return os.environ.get(SLACK_WEBHOOK_ENV_KEY)

def get_gemini_api_key_from_env():
    ensure_dotenv_is_loaded()
    return os.environ.get(GEMINI_API_KEY_ENV_KEY)


def get_kst_timestamp_string(target_datetime: datetime = None, datetime_format_str: str = '%Y-%m-%d %H:%M:%S KST'):
    korea_standard_time = timezone(timedelta(hours=9))

    datetime_in_kst: datetime
    if target_datetime is None:
        datetime_in_kst = datetime.now(tz=korea_standard_time)
    else:
        if target_datetime.tzinfo is None:
            aware_local_datetime = target_datetime.astimezone()
            datetime_in_kst = aware_local_datetime.astimezone(korea_standard_time)
        else:
            datetime_in_kst = target_datetime.astimezone(korea_standard_time)
            
    return datetime_in_kst.strftime(datetime_format_str)

def format_script_duration(start_datetime: datetime, end_datetime: datetime) -> str:
    if not isinstance(start_datetime, datetime) or \
       not isinstance(end_datetime, datetime) or \
       end_datetime < start_datetime:
        return "N/A"
    
    duration_in_seconds = (end_datetime - start_datetime).total_seconds()
    if duration_in_seconds < 0:
        return "N/A"

    total_seconds_integer = int(duration_in_seconds)

    hours, remainder_seconds = divmod(total_seconds_integer, 3600)
    minutes, seconds = divmod(remainder_seconds, 60)
    
    duration_components = []
    if hours > 0:
        duration_components.append(f"{hours}h")
    if minutes > 0:
        duration_components.append(f"{minutes}m")
    
    if total_seconds_integer == 0 or seconds > 0 or not duration_components:
        duration_components.append(f"{seconds}s")
        
    return " ".join(duration_components) if duration_components else "0s"

def report_arguments(args: Union[argparse.Namespace, Dict[str, Any]]):
    """
    Reports script arguments to be captured by the researchflow alarm tool.
    Call this function in your script with the parsed arguments object.
    """
    args_dict = vars(args) if isinstance(args, argparse.Namespace) else args
    
    try:
        json_output = json.dumps(args_dict, indent=2)
        sys.stdout.write(f"\n{PARSED_ARGS_START_MARKER}\n")
        sys.stdout.write(json_output)
        sys.stdout.write(f"\n{PARSED_ARGS_END_MARKER}\n\n")
        sys.stdout.flush()
    except TypeError as e:
        sys.stderr.write(f"[researchflow.report_arguments] Error: Could not serialize arguments to JSON: {e}\n")