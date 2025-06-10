import sys
import os
import traceback
import json
from pathlib import Path
from typing import List, Optional

from .agent import GeminiAgent, format_paper_data_for_slack, Review, MetaData
from researchflow.core.utils import get_gemini_api_key_from_env, get_slack_webhook_url_from_env
from researchflow.core.slack_sender import ReviewSlackSender

DUMMY_DATA_FILE_PATH = Path(__file__).parent / "review_data.json"

def process_paper_review(
    paper_url: str,
    language_code: str,
    user_interests: Optional[List[str]] = None
) -> bool:
    
    sys.stdout.write(f"[ReviewHandler] Initializing review for: {paper_url}\n")

    gemini_api_key = get_gemini_api_key_from_env()
    slack_webhook_url = get_slack_webhook_url_from_env()
    
    USE_DUMMY_OUTPUT = not bool(gemini_api_key)

    try:
        if USE_DUMMY_OUTPUT:
            sys.stdout.write(f"[ReviewHandler] API Key not found. Using DUMMY OUTPUT from {DUMMY_DATA_FILE_PATH}\n")
            if not DUMMY_DATA_FILE_PATH.exists():
                sys.stderr.write(f"[ReviewHandler] Error: Dummy data file not found at {DUMMY_DATA_FILE_PATH}\n")
                return False
            
            with open(DUMMY_DATA_FILE_PATH, 'r', encoding='utf-8') as f:
                final_data_for_slack = json.load(f)
        else:
            sys.stdout.write("[ReviewHandler] Using Gemini API to generate review...\n")
            agent = GeminiAgent(api_key=gemini_api_key, user_interests=user_interests)
            
            sys.stdout.write("[ReviewHandler] Extracting metadata...\n")
            metadata = agent.get_metadata(url=paper_url)
            
            sys.stdout.write("[ReviewHandler] Generating review...\n")
            review = agent.review_paper(url=paper_url)
            
            final_data_for_slack = format_paper_data_for_slack(metadata, review)
        
        if slack_webhook_url:
            sys.stdout.write("[ReviewHandler] Sending review to Slack...\n")
            sender = ReviewSlackSender(webhook_url=slack_webhook_url)
            send_success = sender.send_review_notification(
                paper_url_or_path=paper_url,
                review_data=final_data_for_slack
            )
            if send_success:
                sys.stdout.write("[ReviewHandler] Slack notification sent successfully.\n")
            else:
                sys.stderr.write("[ReviewHandler] Failed to send Slack notification.\n")
        else:
            sys.stdout.write("[ReviewHandler] Slack webhook URL not configured. Review details (JSON):\n")
            sys.stdout.write(json.dumps(final_data_for_slack, indent=2, ensure_ascii=False))
            
        return True

    except Exception as e:
        sys.stderr.write(f"[ReviewHandler] An unexpected error occurred: {e}\n")
        sys.stderr.write(traceback.format_exc())
        return False