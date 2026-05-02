import json
import os
import sys
import traceback
from typing import Any, Dict, List, Optional

import requests

from .config import ResearchFlowConfig, load_config


class SlackNotifier:
    def __init__(self, config: Optional[ResearchFlowConfig] = None):
        self.config = config if config is not None else load_config()

    @staticmethod
    def _post_json(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        try:
            response = requests.post(
                url,
                data=json.dumps(payload),
                headers=headers or {"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            if response.text:
                try:
                    return response.json()
                except ValueError:
                    return {"ok": True, "text": response.text}
            return {"ok": True}
        except requests.exceptions.RequestException as e:
            sys.stderr.write(f"[SlackNotifier] Error sending Slack notification: {e}\n")
            if e.response is not None:
                sys.stderr.write(f"[SlackNotifier] Response Status Code: {e.response.status_code}\n")
                sys.stderr.write(f"[SlackNotifier] Response Text: {e.response.text}\n")
            return None

    def _api_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.slack_bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    def _call_slack_api(self, method: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        response_payload = self._post_json(
            f"https://slack.com/api/{method}",
            payload,
            headers=self._api_headers(),
        )
        if response_payload is None:
            return None
        if not response_payload.get("ok"):
            sys.stderr.write(
                f"[SlackNotifier] Slack API method {method} failed: "
                f"{response_payload.get('error', 'unknown_error')}\n"
            )
            return None
        return response_payload

    def _open_dm(self) -> Optional[str]:
        if not self.config.slack_user_id:
            sys.stderr.write("[SlackNotifier] DM destination requested, but no Slack user ID is configured.\n")
            return None

        response_payload = self._call_slack_api(
            "conversations.open",
            {"users": self.config.slack_user_id, "return_im": False},
        )
        if not response_payload:
            return None

        channel = response_payload.get("channel") or {}
        channel_id = channel.get("id")
        if not channel_id:
            sys.stderr.write("[SlackNotifier] Slack did not return a DM channel ID.\n")
            return None
        return channel_id

    def _resolve_delivery(self) -> Optional[str]:
        destination = self.config.slack_destination
        if destination == "off":
            return "off"
        if destination == "webhook":
            return "webhook"
        if destination == "channel":
            return "channel"
        if destination == "dm":
            return "dm"

        if self.config.slack_bot_token and self.config.slack_channel:
            return "channel"
        if self.config.slack_bot_token and self.config.slack_user_id:
            return "dm"
        if self.config.slack_webhook_url:
            return "webhook"
        return None

    def send_payload(self, payload: Dict[str, Any]) -> bool:
        delivery = self._resolve_delivery()
        if delivery == "off":
            sys.stdout.write("[SlackNotifier] Slack notification disabled by configuration.\n")
            return False
        if delivery is None:
            sys.stderr.write("[SlackNotifier] Slack destination not configured. Skipping notification.\n")
            return False
        if delivery == "webhook":
            return self._send_webhook_payload(payload)

        if not self.config.slack_bot_token:
            sys.stderr.write("[SlackNotifier] Slack bot token not configured. Skipping notification.\n")
            return False

        channel_id = self.config.slack_channel
        if delivery == "dm":
            channel_id = self._open_dm()
        if not channel_id:
            sys.stderr.write("[SlackNotifier] Slack channel/DM target could not be resolved.\n")
            return False

        api_payload = dict(payload)
        api_payload["channel"] = channel_id
        return self._call_slack_api("chat.postMessage", api_payload) is not None

    def _send_webhook_payload(self, payload: Dict[str, Any]) -> bool:
        if not self.config.slack_webhook_url:
            sys.stderr.write("[SlackNotifier] Slack webhook URL not configured. Skipping notification.\n")
            return False

        try:
            response = requests.post(
                self.config.slack_webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            sys.stderr.write(f"[SlackNotifier] Error sending Slack webhook notification: {e}\n")
            if e.response is not None:
                sys.stderr.write(f"[SlackNotifier] Response Status Code: {e.response.status_code}\n")
                sys.stderr.write(f"[SlackNotifier] Response Text: {e.response.text}\n")
            return False
        except Exception as e:
            sys.stderr.write(f"[SlackNotifier] Unexpected Slack webhook error: {e}\n")
            sys.stderr.write(traceback.format_exc())
            return False


class AlarmSlackSender:
    def __init__(self, config: Optional[ResearchFlowConfig] = None, webhook_url: Optional[str] = None):
        if config is None:
            config = load_config(slack_webhook_url=webhook_url) if webhook_url is not None else load_config()
        self.config = config
        self.notifier = SlackNotifier(config=config)

    @staticmethod
    def _format_slack_block_text(text: str, max_length: int = 2900, is_mrkdwn: bool = True) -> str:
        if not text:
            return "N/A" if is_mrkdwn else ""

        if len(text) > max_length:
            truncate_msg = "... [Content Truncated]"
            allowed_text_len = max_length - len(truncate_msg)
            if allowed_text_len < 0:
                return text[:max_length]
            text = text[:allowed_text_len] + truncate_msg
        return text

    def _format_parsed_arguments_block(self, args_dict: Optional[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        if not args_dict:
            return None

        argument_lines = []
        max_key_len = max(map(len, [str(k) for k in args_dict.keys()])) if args_dict else 0
        for key, value in args_dict.items():
            argument_lines.append(f"{str(key).ljust(max_key_len)} : {str(value)}")

        if not argument_lines:
            return None

        full_arguments_text = "\n".join(argument_lines)
        formatted_args_text_for_block = self._format_slack_block_text(
            f"```{full_arguments_text}```",
            max_length=2950,
            is_mrkdwn=True,
        )

        return [
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Parsed Arguments*"}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": formatted_args_text_for_block}]},
        ]

    def _format_error_output_block(self, error_output: Optional[str]) -> Optional[List[Dict[str, Any]]]:
        if not error_output or not error_output.strip():
            return None

        error_to_send = error_output.strip()
        formatted_error_text_for_block = self._format_slack_block_text(
            f"```{error_to_send}```",
            max_length=2950,
            is_mrkdwn=True,
        )

        return [
            {"type": "section", "text": {"type": "mrkdwn", "text": "*Error Output (stderr & warnings):*"}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": formatted_error_text_for_block}]},
        ]

    def _format_gpu_info_block(self, gpu_info_text: Optional[str]) -> Optional[List[Dict[str, Any]]]:
        if not gpu_info_text:
            return None

        formatted_gpu_text = self._format_slack_block_text(
            f"```{gpu_info_text}```",
            max_length=2950,
            is_mrkdwn=True,
        )
        return [
            {"type": "section", "text": {"type": "mrkdwn", "text": "*GPU Snapshot*"}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": formatted_gpu_text}]},
        ]

    def _build_alarm_payload(
        self,
        script_name: str,
        status: str,
        duration_str: str,
        exit_code: int,
        hostname: str,
        start_time_str: str,
        end_time_str: str,
        script_path_str: str,
        executed_command_str: str,
        parsed_args_dict: Optional[Dict[str, Any]] = None,
        error_output_str: Optional[str] = None,
        log_file_path_str: Optional[str] = None,
        gpu_info_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        color = "#36a64f" if status == "Success" else "#ff0000"
        status_emoji = "✅" if status == "Success" else "❌"
        status_text = f"{status_emoji} *{status}*"

        base_blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Script Report: {self._format_slack_block_text(script_name, max_length=140, is_mrkdwn=False)}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Status:*\n{status_text}"},
                    {"type": "mrkdwn", "text": f"*Duration:*\n{duration_str}"},
                    {"type": "mrkdwn", "text": f"*Exit Code:*\n`{exit_code}`"},
                    {"type": "mrkdwn", "text": f"*Host:*\n`{hostname}`"},
                    {"type": "mrkdwn", "text": f"*Start Time:*\n{start_time_str}"},
                    {"type": "mrkdwn", "text": f"*End Time:*\n{end_time_str}"},
                ],
            },
            {"type": "context", "elements": [{"type": "mrkdwn", "text": f"*Script Path:* `{script_path_str}`"}]},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": f"*Executed Command:* `{executed_command_str}`"}]},
        ]

        if log_file_path_str:
            base_blocks.append(
                {"type": "context", "elements": [{"type": "mrkdwn", "text": f"*Log:* `{log_file_path_str}`"}]}
            )

        final_blocks = list(base_blocks)

        for optional_blocks in (
            self._format_parsed_arguments_block(parsed_args_dict),
            self._format_gpu_info_block(gpu_info_text),
        ):
            if optional_blocks:
                if final_blocks[-1].get("type") != "divider":
                    final_blocks.append({"type": "divider"})
                final_blocks.extend(optional_blocks)

        if status == "Failure" and error_output_str:
            error_blocks = self._format_error_output_block(error_output_str)
            if error_blocks:
                if final_blocks[-1].get("type") != "divider":
                    final_blocks.append({"type": "divider"})
                final_blocks.extend(error_blocks)

        fallback_text = f"{status_emoji} {script_name} {status} ({duration_str})"
        if self.config.mention_user and self.config.slack_user_id:
            fallback_text = f"<@{self.config.slack_user_id}> {fallback_text}"
        if status == "Failure":
            fallback_text += f" | Exit Code: {exit_code}"
        if log_file_path_str:
            fallback_text += f" | Log: {os.path.basename(log_file_path_str)}"

        return {
            "text": fallback_text,
            "attachments": [
                {
                    "color": color,
                    "blocks": final_blocks,
                }
            ],
        }

    def send_alarm_notification(
        self,
        script_name: str,
        status: str,
        duration_str: str,
        exit_code: int,
        hostname: str,
        start_time_str: str,
        end_time_str: str,
        script_path_str: str,
        executed_command_str: str,
        parsed_args_dict: Optional[Dict[str, Any]] = None,
        error_output_str: Optional[str] = None,
        log_file_path_str: Optional[str] = None,
        gpu_info_text: Optional[str] = None,
    ) -> bool:
        payload = self._build_alarm_payload(
            script_name=script_name,
            status=status,
            duration_str=duration_str,
            exit_code=exit_code,
            hostname=hostname,
            start_time_str=start_time_str,
            end_time_str=end_time_str,
            script_path_str=script_path_str,
            executed_command_str=executed_command_str,
            parsed_args_dict=parsed_args_dict,
            error_output_str=error_output_str,
            log_file_path_str=log_file_path_str,
            gpu_info_text=gpu_info_text,
        )
        return self.notifier.send_payload(payload)
