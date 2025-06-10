import sys
import argparse
from researchflow.core.constants import DEFAULT_REVIEW_LANGUAGE
from .handler import process_paper_review

def main():
    parser = argparse.ArgumentParser(
        description="Reviews a research paper using a GenAI model and sends the results to Slack.",
        prog="review"
    )
    parser.add_argument(
        "paper_input",
        help="URL of the research paper (e.g., arXiv abstract page)."
    )
    parser.add_argument(
        "--lang",
        type=str,
        default=DEFAULT_REVIEW_LANGUAGE,
        help=f"Language for the review summary (e.g., 'en', 'ko'). Defaults to '{DEFAULT_REVIEW_LANGUAGE}'."
    )
    parser.add_argument(
        "--user-interests",
        "-u",
        nargs='+',
        help="List of user interests to consider in the review's 'interest_relevance' evaluation (e.g., --user-interests 'LLM Safety' 'Reinforcement Learning')."
    )

    if len(sys.argv) <= 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
        
    args = parser.parse_args(sys.argv[1:])

    success = process_paper_review(
        paper_url=args.paper_input,
        language_code=args.lang,
        user_interests=args.user_interests
    )

    if not success:
        sys.exit(1)
    sys.exit(0)