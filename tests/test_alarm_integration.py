import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from researchflow.alarm.handler import _resolve_log_file_path


class AlarmIntegrationTests(unittest.TestCase):
    def test_alarm_wraps_sample_experiment_without_slack(self):
        repo_root = Path(__file__).resolve().parents[1]
        sample_script = repo_root / "tests" / "fixtures" / "sample_experiment.py"

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = Path(tmpdir) / "artifacts"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "researchflow.alarm.cli",
                    "--destination",
                    "off",
                    "--no-gpu-info",
                    str(sample_script),
                    "--epochs",
                    "1",
                    "--total-runtime-factor",
                    "0",
                    "--checkpoint-save-dir",
                    str(checkpoint_dir),
                ],
                cwd=repo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("ResearchFlow Sample Experiment Finished successfully", completed.stdout)
        self.assertIn("Skipping Slack notification", completed.stdout)

    def test_default_log_path_uses_script_logs_dir_and_kst_timestamp(self):
        script_path = "/tmp/project/train.py"
        with mock.patch("researchflow.alarm.handler._get_kst_log_timestamp", return_value="20260502_123456_KST"):
            log_path = _resolve_log_file_path(script_path)

        self.assertEqual(log_path, "/tmp/project/logs/20260502_123456_KST_train.log")

    def test_custom_log_path_uses_configured_dir(self):
        script_path = "/tmp/project/train.py"
        with mock.patch("researchflow.alarm.handler._get_kst_log_timestamp", return_value="20260502_123456_KST"):
            log_path = _resolve_log_file_path(script_path, "/tmp/researchflow_logs")

        self.assertEqual(log_path, "/tmp/researchflow_logs/20260502_123456_KST_train.log")


if __name__ == "__main__":
    unittest.main()
