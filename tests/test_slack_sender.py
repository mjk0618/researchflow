import unittest
from unittest import mock

from researchflow.core.config import ResearchFlowConfig
from researchflow.core.slack_sender import AlarmSlackSender, SlackNotifier


class _FakeResponse:
    def __init__(self, payload=None, text="ok", status_code=200):
        self._payload = payload
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class SlackNotifierTests(unittest.TestCase):
    def test_sends_channel_message_with_bot_token(self):
        config = ResearchFlowConfig(
            slack_destination="channel",
            slack_bot_token="xoxb-test",
            slack_channel="C123",
        )

        with mock.patch("researchflow.core.slack_sender.requests.post") as post:
            post.return_value = _FakeResponse({"ok": True, "channel": "C123"})
            sent = SlackNotifier(config).send_payload({"text": "done"})

        self.assertTrue(sent)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.args[0], "https://slack.com/api/chat.postMessage")
        self.assertIn('"channel": "C123"', post.call_args.kwargs["data"])
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer xoxb-test")

    def test_opens_dm_then_posts_message(self):
        config = ResearchFlowConfig(
            slack_destination="dm",
            slack_bot_token="xoxb-test",
            slack_user_id="U123",
        )

        with mock.patch("researchflow.core.slack_sender.requests.post") as post:
            post.side_effect = [
                _FakeResponse({"ok": True, "channel": {"id": "D123"}}),
                _FakeResponse({"ok": True, "channel": "D123"}),
            ]
            sent = SlackNotifier(config).send_payload({"text": "done"})

        self.assertTrue(sent)
        self.assertEqual(post.call_count, 2)
        self.assertEqual(post.call_args_list[0].args[0], "https://slack.com/api/conversations.open")
        self.assertEqual(post.call_args_list[1].args[0], "https://slack.com/api/chat.postMessage")
        self.assertIn('"channel": "D123"', post.call_args_list[1].kwargs["data"])

    def test_alarm_payload_includes_gpu_snapshot(self):
        config = ResearchFlowConfig(slack_destination="off")
        sender = AlarmSlackSender(config=config)
        payload = sender._build_alarm_payload(
            script_name="train.py",
            status="Success",
            duration_str="1m",
            exit_code=0,
            hostname="host",
            start_time_str="start",
            end_time_str="end",
            script_path_str="/tmp/train.py",
            executed_command_str="alarm train.py",
            gpu_info_text="GPU 0 | Test GPU | 100/1000 MiB",
        )

        payload_text = str(payload)
        self.assertIn("GPU Snapshot", payload_text)
        self.assertIn("Test GPU", payload_text)


if __name__ == "__main__":
    unittest.main()
