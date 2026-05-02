import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from researchflow.core.config import get_config_sources, load_config, write_default_config


class ConfigTests(unittest.TestCase):
    def test_loads_file_env_and_cli_overrides(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "slack_destination": "channel",
                        "slack_channel": "CFILE",
                        "include_gpu": False,
                    }
                ),
                encoding="utf-8",
            )

            env = {
                "RESEARCHFLOW_SLACK_CHANNEL": "CENV",
                "RESEARCHFLOW_SLACK_BOT_TOKEN": "xoxb-env",
            }
            with mock.patch.dict(os.environ, env, clear=True):
                with mock.patch("researchflow.core.config.ensure_dotenv_is_loaded"):
                    with mock.patch("researchflow.core.utils.ensure_dotenv_is_loaded"):
                        config = load_config(
                            config_path=str(config_path),
                            slack_channel="CCLI",
                            include_gpu=True,
                            log_dir="/tmp/logs",
                        )

        self.assertEqual(config.slack_destination, "channel")
        self.assertEqual(config.slack_channel, "CCLI")
        self.assertEqual(config.slack_bot_token, "xoxb-env")
        self.assertTrue(config.include_gpu)
        self.assertEqual(config.log_dir, "/tmp/logs")

    def test_write_default_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "researchflow.json"
            written_path = write_default_config(str(config_path))
            data = json.loads(written_path.read_text(encoding="utf-8"))

        self.assertEqual(data["slack_destination"], "auto")
        self.assertIn("slack_channel", data)

    def test_config_sources_reports_active_write_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            sources = get_config_sources(str(config_path))

        self.assertEqual(sources["active_write_path"], str(config_path))
        self.assertEqual(sources["read_sources"][0]["path"], str(config_path))

    def test_config_sources_respects_env_config_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "env_config.json"
            with mock.patch.dict(os.environ, {"RESEARCHFLOW_CONFIG": str(config_path)}, clear=True):
                with mock.patch("researchflow.core.config.ensure_dotenv_is_loaded"):
                    sources = get_config_sources()

        self.assertEqual(sources["active_write_path"], str(config_path))
        self.assertEqual(sources["read_sources"][0]["path"], str(config_path))


if __name__ == "__main__":
    unittest.main()
