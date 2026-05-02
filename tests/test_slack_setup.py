import tempfile
import unittest
from pathlib import Path
from unittest import mock

from researchflow.core.config import load_config
from researchflow.core.slack_setup import SlackApiError, _format_slack_api_error, setup_dm_by_name


class SlackSetupTests(unittest.TestCase):
    def test_missing_scope_message_explains_incoming_webhook_only_app(self):
        error = SlackApiError(
            method="conversations.list",
            error="missing_scope",
            needed="channels:read,groups:read",
            provided="incoming-webhook",
        )

        message = _format_slack_api_error(error, "channel")

        self.assertIn("incoming-webhook scope", message)
        self.assertIn("channels:read", message)
        self.assertIn("reinstall the Slack App", message)

    def test_setup_dm_by_name_saves_unique_user_match(self):
        user = {
            "id": "U123",
            "name": "mjkang",
            "profile": {
                "display_name": "mj kang",
                "real_name": "Minjae Kang",
                "email": "mjkang@example.com",
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            with mock.patch("researchflow.core.slack_setup.SlackSetupClient") as client_cls:
                client = client_cls.return_value
                client.auth_test.return_value = {"team": "ML3", "team_id": "T07CSJGATDW", "user_id": "UBOT"}
                client.list_users.return_value = [user]

                result = setup_dm_by_name(
                    "Minjae Kang",
                    config_path=str(config_path),
                    bot_token="xoxb-test",
                    team_id="T07CSJGATDW",
                    run_check=False,
                )

            config = load_config(config_path=str(config_path))

        self.assertEqual(result, 0)
        self.assertEqual(config.slack_destination, "dm")
        self.assertEqual(config.slack_user_id, "U123")


if __name__ == "__main__":
    unittest.main()
