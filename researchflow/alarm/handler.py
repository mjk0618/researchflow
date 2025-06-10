import sys
import subprocess
from datetime import datetime
import os
import json
import re
import threading
import io
import time
import traceback
import socket
from typing import List, Optional, Any, Dict

from researchflow.core.utils import (
    get_kst_timestamp_string,
    format_script_duration,
    get_slack_webhook_url_from_env
)
from researchflow.core.slack_sender import AlarmSlackSender
from .constants import PARSED_ARGS_START_MARKER, PARSED_ARGS_END_MARKER


def _stream_and_buffer_output(pipe: Optional[io.TextIOWrapper], stream: io.TextIOBase, buffer_list: list):
    if pipe is None:
        return
    try:
        for line in pipe:
            stream.write(line)
            stream.flush()
            buffer_list.append(line)
    except ValueError:
        pass
    except Exception as e:
        sys.stderr.write(f"\n[AlarmHandler] Error streaming output: {e}\n")

def _read_log_file_content(log_file_path: str) -> str:
    try:
        with open(log_file_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception as e:
        sys.stderr.write(f"\n[AlarmHandler] Error reading log file {log_file_path}: {e}\n")
        return ""

def _get_last_n_lines_from_file(file_path: str, n_lines: int = 50) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        return "".join(lines[-n_lines:])
    except Exception:
        return f"Could not read last lines from log file: {file_path}"


def execute_script_with_alarm(
        target_script_path: str,
        target_script_args: List[str],
        alarm_command_args_for_display: List[str],
        enable_logging: bool = False
    ) -> int:

    if enable_logging and os.environ.get("_ALARM_INTERNAL_MONITOR") is None:
        script_base_name = os.path.splitext(os.path.basename(target_script_path))[0]
        timestamp_for_log = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file_name = f"{script_base_name}_{timestamp_for_log}.log"
        log_file_full_path = os.path.join(os.getcwd(), log_file_name)

        new_env = os.environ.copy()
        new_env["_ALARM_INTERNAL_MONITOR"] = "1"
        
        command_to_rerun = [sys.executable] + sys.argv
        
        popen_kwargs: Dict[str, Any] = {"env": new_env}

        if os.name == 'posix':
            popen_kwargs['start_new_session'] = True
        elif os.name == 'nt':
            DETACHED_PROCESS = 0x00000008
            popen_kwargs['creationflags'] = DETACHED_PROCESS
        
        popen_kwargs['stdout'] = subprocess.DEVNULL
        popen_kwargs['stderr'] = subprocess.DEVNULL
        popen_kwargs['stdin'] = subprocess.DEVNULL

        process = subprocess.Popen(command_to_rerun, **popen_kwargs)
        
        sys.stdout.write(f"[AlarmHandler] Process started in background (PID: {process.pid}).\n")
        sys.stdout.write(f"[AlarmHandler] Logging stdout/stderr to: {log_file_full_path}\n")
        
        return 0
    
    webhook_url = get_slack_webhook_url_from_env()
    if not webhook_url:
        sys.stderr.write("[AlarmHandler] Warning: SLACK_WEBHOOK_URL environment variable not set. Slack notification will be disabled.\n")

    try:
        target_script_full_path = os.path.abspath(target_script_path)
        if not os.path.isfile(target_script_full_path):
            sys.stderr.write(f"[AlarmHandler] Error: Target script is not a file or does not exist: {target_script_full_path}\n")
            return 1
    except Exception as e:
        sys.stderr.write(f"[AlarmHandler] Error resolving script path '{target_script_path}': {e}\n")
        return 1

    command = [sys.executable, target_script_full_path] + target_script_args
    
    start_time = datetime.now()
    process: Optional[subprocess.Popen] = None
    return_code = 1 
    status = "Failure"
    parsed_args_dict: Optional[Dict[str, Any]] = None
    error_message_for_slack: Optional[str] = None
    log_file_full_path: Optional[str] = None
    
    executed_command_display = f"alarm {' '.join(alarm_command_args_for_display)}"
    if enable_logging:
        executed_command_display = f"alarm --log {' '.join(alarm_command_args_for_display)}"


    popen_kwargs: Dict[str, Any] = {
        "text": True,
        "encoding": 'utf-8',
        "errors": 'replace',
        "bufsize": 1
    }
    
    log_file_handle: Optional[io.TextIOWrapper] = None

    if enable_logging:
        script_base_name = os.path.splitext(os.path.basename(target_script_full_path))[0]
        timestamp_for_log = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file_name = f"{script_base_name}_{timestamp_for_log}.log"
        log_file_full_path = os.path.join(os.getcwd(), log_file_name)
        
        sys.stdout.write(f"[AlarmHandler] Logging stdout/stderr to: {log_file_full_path}\n")
        try:
            log_file_handle = open(log_file_full_path, 'w', encoding='utf-8', errors='replace')
            popen_kwargs["stdout"] = log_file_handle
            popen_kwargs["stderr"] = subprocess.STDOUT
            if os.name == 'posix':
                popen_kwargs["preexec_fn"] = os.setsid
        except Exception as e:
            sys.stderr.write(f"[AlarmHandler] Error opening log file {log_file_full_path}: {e}. Logging disabled.\n")
            enable_logging = False
            if log_file_handle: log_file_handle.close()
            log_file_full_path = None


    if not enable_logging: 
        popen_kwargs["stdout"] = subprocess.PIPE
        popen_kwargs["stderr"] = subprocess.PIPE

    stdout_buffer: List[str] = []
    stderr_buffer: List[str] = []

    try:
        process = subprocess.Popen(command, **popen_kwargs)

        stdout_thread: Optional[threading.Thread] = None
        stderr_thread: Optional[threading.Thread] = None

        if not enable_logging and process.stdout and process.stderr:
            stdout_thread = threading.Thread(
                target=_stream_and_buffer_output,
                args=(process.stdout, sys.stdout, stdout_buffer),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=_stream_and_buffer_output,
                args=(process.stderr, sys.stderr, stderr_buffer),
                daemon=True
            )
            stdout_thread.start()
            stderr_thread.start()

        return_code = process.wait()
        end_time = datetime.now()

        if stdout_thread: stdout_thread.join(timeout=2.0)
        if stderr_thread: stderr_thread.join(timeout=2.0)
        
        output_content_for_parsing: str
        if enable_logging and log_file_full_path:
            if log_file_handle: log_file_handle.close() 
            output_content_for_parsing = _read_log_file_content(log_file_full_path)
        else:
            output_content_for_parsing = "".join(stdout_buffer)
            error_message_for_slack = "".join(stderr_buffer).strip()

        match = re.search(
            f"{re.escape(PARSED_ARGS_START_MARKER)}(.*?){re.escape(PARSED_ARGS_END_MARKER)}",
            output_content_for_parsing,
            re.DOTALL
        )

        if match:
            json_string = match.group(1).strip()
            try:
                parsed_args_dict = json.loads(json_string)
            except json.JSONDecodeError as json_err:
                warning_msg = f"\n[AlarmHandler Warning] Could not decode JSON arguments from script output: {json_err}\nCaptured JSON string: ```{json_string}```\n"
                sys.stderr.write(warning_msg)
                if enable_logging:
                    pass
                elif error_message_for_slack is not None:
                        error_message_for_slack += warning_msg
                else:
                        error_message_for_slack = warning_msg

            except Exception as e:
                warning_msg = f"\n[AlarmHandler Warning] Error processing parsed arguments: {e}\n"
                sys.stderr.write(warning_msg)
                if enable_logging:
                    pass
                elif error_message_for_slack is not None:
                    error_message_for_slack += warning_msg
                else:
                    error_message_for_slack = warning_msg


        if return_code == 0:
            status = "Success"
        else:
            status = "Failure"
            if enable_logging and log_file_full_path and status == "Failure":
                error_message_for_slack = f"Script failed. Check log for details: {log_file_full_path}\n--- Last 50 lines ---\n{_get_last_n_lines_from_file(log_file_full_path)}"
            elif not error_message_for_slack and status == "Failure":
                    error_message_for_slack = f"Script failed with exit code {return_code} and no specific stderr output."
            
    except FileNotFoundError:
        end_time = datetime.now()
        status = "Failure"
        error_message_for_slack = f"[AlarmHandler] Error: Script not found or couldn't execute - {target_script_full_path}"
        return_code = 1 
    except Exception as e:
        end_time = datetime.now()
        status = "Failure"
        error_message_for_slack = f"[AlarmHandler] Error running script: {e}\nTraceback:\n{traceback.format_exc()}"
        if process and process.returncode is not None:
            return_code = process.returncode
        else:
            return_code = 1
    finally:
        if 'end_time' not in locals():
            end_time = datetime.now()
        if process:
            if process.stdout and not enable_logging: process.stdout.close()
            if process.stderr and not enable_logging: process.stderr.close()
            if process.poll() is None:
                sys.stderr.write("[AlarmHandler] Terminating script due to error in alarm tool.\n")
                process.terminate()
                time.sleep(0.5)
                if process.poll() is None:
                    process.kill()
        if log_file_handle and not log_file_handle.closed:
            log_file_handle.close()


    if webhook_url:
        sys.stdout.write("\n[AlarmHandler] Sending Slack notification...\n")
        
        hostname = ""
        try:
            hostname = os.uname().nodename
        except AttributeError: 
            try:
                hostname = socket.gethostname()
            except Exception:
                hostname = "N/A"
        
        sender = AlarmSlackSender(webhook_url=webhook_url)
        sender.send_alarm_notification(
            script_name=os.path.basename(target_script_full_path),
            status=status,
            duration_str=format_script_duration(start_time, end_time),
            exit_code=return_code if return_code is not None else 1,
            hostname=hostname,
            start_time_str=get_kst_timestamp_string(start_time),
            end_time_str=get_kst_timestamp_string(end_time),
            script_path_str=target_script_full_path,
            executed_command_str=executed_command_display,
            parsed_args_dict=parsed_args_dict,
            error_output_str=error_message_for_slack,
            log_file_path_str=log_file_full_path if enable_logging else None 
        )
    else:
        sys.stdout.write("\n[AlarmHandler] Skipping Slack notification (SLACK_WEBHOOK_URL not set).\n")

    return return_code if return_code is not None else 1