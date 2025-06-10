import requests
import json
import os
import sys
import traceback
from typing import Optional, List, Dict, Any
from datetime import datetime
from urllib.parse import urlparse

from .utils import get_slack_webhook_url_from_env, format_script_duration


class BaseSlackSender:
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url if webhook_url is not None else get_slack_webhook_url_from_env()

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

    def _send_payload(self, payload: dict) -> bool:
        if not self.webhook_url:
            sys.stderr.write("[SlackSender] Slack webhook URL not configured. Skipping notification.\n")
            return False

        try:
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            sys.stderr.write(f"[SlackSender] Error sending Slack notification: {e}\n")
            if e.response is not None:
                sys.stderr.write(f"[SlackSender] Response Status Code: {e.response.status_code}\n")
                sys.stderr.write(f"[SlackSender] Response Text: {e.response.text}\n")
            return False
        except Exception as e:
            sys.stderr.write(f"[SlackSender] An unexpected error occurred while sending Slack notification: {e}\n")
            sys.stderr.write(traceback.format_exc())
            return False


class AlarmSlackSender(BaseSlackSender):
    def _format_parsed_arguments_block(self, args_dict: Optional[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        if not args_dict:
            return None
        
        str_keys = [str(k) for k in args_dict.keys()]
        str_values = [str(v) for v in args_dict.values()]

        if not str_keys or not str_values : return None

        max_key_len = 0
        if str_keys:
            max_key_len = max(map(len, str_keys))
        
        argument_lines = []
        for key, value in args_dict.items():
            key_padded = str(key).ljust(max_key_len)
            argument_lines.append(f"{key_padded} : {str(value)}")

        if not argument_lines:
            return None

        full_arguments_text = "\n".join(argument_lines)
        
        formatted_args_text_for_block = self._format_slack_block_text(f"```{full_arguments_text}```", max_length=2950, is_mrkdwn=True)

        header_block = { 
            "type": "section",
            "text": {
                "type": "mrkdwn", 
                "text": "*Parsed Arguments*"
            },
        }
        content_block = {
            "type": "context",
            "elements": [
                {
                "type": "mrkdwn",
                "text": formatted_args_text_for_block
                }
            ]
        }
        return [header_block, content_block]

    def _format_error_output_block(self, error_output: Optional[str]) -> Optional[List[Dict[str, Any]]]:
        if not error_output or not error_output.strip():
            return None
        
        error_to_send = error_output.strip()
        header_text = "*Error Output (stderr & warnings):*"
        
        formatted_error_text_for_block = self._format_slack_block_text(f"```{error_to_send}```", max_length=2950, is_mrkdwn=True)

        header_block = { 
            "type": "section",
            "text": {
                "type": "mrkdwn", 
                "text": header_text
            },
        }
        content_block = {
            "type": "context",
            "elements": [
                {
                "type": "mrkdwn",
                "text": formatted_error_text_for_block
                }
            ]
        }
        return [header_block, content_block]

    def _build_alarm_payload(self,
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
                             log_file_path_str: Optional[str] = None
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
                    "emoji": True
                }
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
                ]
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"*Script Path:* `{script_path_str}`"}
                ]
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"*Executed Command:* `{executed_command_str}`"}
                ]
            }
        ]
        
        if log_file_path_str:
            base_blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"*Log File:* `{log_file_path_str}`"}
                    ]
                }
            )


        final_blocks = list(base_blocks)

        parsed_args_added = False
        parsed_args_blocks = self._format_parsed_arguments_block(parsed_args_dict)
        if parsed_args_blocks:
            if final_blocks[-1].get("type") not in ["divider", "header"]:
                 final_blocks.append({"type": "divider"})
            final_blocks.extend(parsed_args_blocks)
            parsed_args_added = True

        if status == "Failure" and error_output_str:
            error_blocks = self._format_error_output_block(error_output_str)
            if error_blocks:
                if not parsed_args_added and final_blocks[-1].get("type") not in ["divider", "header"]:
                    final_blocks.append({"type": "divider"})
                elif parsed_args_added and final_blocks[-1].get("type") != "divider":
                     final_blocks.append({"type": "divider"})
                final_blocks.extend(error_blocks)
        
        fallback_text = f"{status_emoji} {script_name} {status} ({duration_str})"
        if status == "Failure":
            fallback_text += f" | Exit Code: {exit_code}"
        if log_file_path_str:
            fallback_text += f" | Log: {os.path.basename(log_file_path_str)}"


        main_payload = {
            "text": fallback_text,
            "attachments": [
                {
                    "color": color,
                    "blocks": final_blocks
                }
            ]
        }
        return main_payload

    def send_alarm_notification(self,
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
                                log_file_path_str: Optional[str] = None 
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
            log_file_path_str=log_file_path_str
        )
        return self._send_payload(payload)
    

class ReviewSlackSender(BaseSlackSender):
    def _build_review_payload(self, paper_url: str, review_data: Dict[str, Any]) -> Dict[str, Any]:
        original_title = review_data.get("Title", "Paper Review") 
        
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "📄 Daily Paper Review", "emoji": True}},
            
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Title:* <{paper_url}|{self._format_slack_block_text(original_title, max_length=200, is_mrkdwn=True)}>"}},
            # {"type": "section", "text": {"type": "mrkdwn", "text": f"*Source:* <{paper_url}|Link to Paper>"}},
            # {"type": "divider"}
        ]
        
        if "Authors" in review_data and review_data["Authors"]:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Authors:* {',   '.join(review_data['Authors'])}"
                }
            })

        published_categories_fields = []
        if "Date" in review_data and review_data["Date"]:
            published_categories_fields.append({"type": "mrkdwn", "text": f"*Published:*\n{review_data['Date']}"})
        if "categories" in review_data and review_data["categories"]:
            published_categories_fields.append({"type": "mrkdwn", "text": f"*Categories:*\n{', '.join(review_data['categories'])}"})

        if published_categories_fields:
            blocks.append({"type": "section", "fields": published_categories_fields})

       
        if "evaluation" in review_data:
            eval_data = review_data["evaluation"]
            

            justification = eval_data.get("justification")
            if justification:
                blocks.append({
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": self._format_slack_block_text(justification)}
                    ]
                })
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Evaluation:*"
                }
            })

            eval_score_elements = []
            if 'completeness' in eval_data: eval_score_elements.append({"type": "mrkdwn", "text": f"완성도: *{eval_data['completeness']}*"})
            if 'originality' in eval_data: eval_score_elements.append({"type": "mrkdwn", "text": f"독창성: *{eval_data['originality']}*"})
            if 'clarity' in eval_data: eval_score_elements.append({"type": "mrkdwn", "text": f"명료성: *{eval_data['clarity']}*"})
            if 'impact' in eval_data: eval_score_elements.append({"type": "mrkdwn", "text": f"기대효과: *{eval_data['impact']}*"})
            if 'interest_relevance' in eval_data: eval_score_elements.append({"type": "mrkdwn", "text": f"관심도: *{eval_data['interest_relevance']}*"})

            if eval_score_elements:
                blocks.append({
                    "type": "context",
                    "elements": eval_score_elements
                })
        
        text_sections_to_check = ["summary", "contribution_and_method", "limitations_and_further_study", "related_works", "recommended_papers"]
        
        if any(key in review_data for key in text_sections_to_check):
            if blocks and blocks[-1]["type"] != "divider": 
                 blocks.append({"type": "divider"})

        text_sections_config = {
            "summary": "📑 *Summary*",
            "contribution_and_method": "✨ *Contribution & Method*",
            "limitations_and_further_study": "🤔 *Limitations & Further Study*",
            "insights": "💡 *Insights*",
            "related_works": "📚 *Related Works*",
            "recommended_papers": "📌 *Recommended Papers*"
        }

        for key, heading in text_sections_config.items():
            content = review_data.get(key)
            if not content:
                continue
            
            body = ""
            if isinstance(content, list):
                body = "\n".join([f"• {item}" for item in content])
            elif isinstance(content, str):
                body = content
            
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"{heading}\n{self._format_slack_block_text(body)}"} })

        fallback_text = "" #f"Daily Paper Review: {original_title}"
        review_color = "#4287f5" 

        return {
            "text": fallback_text,
            "attachments": [
                {
                    "color": review_color,
                    "blocks": blocks
                }
            ]
        }

    def send_review_notification(self, paper_url_or_path: str, review_data: Dict[str, Any]) -> bool:
        payload = self._build_review_payload(
            paper_url=paper_url_or_path,
            review_data=review_data
        )
        return self._send_payload(payload)