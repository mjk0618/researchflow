import unittest
from unittest import mock

from researchflow.core.gpu import collect_gpu_info, format_gpu_info_for_text


class GpuInfoTests(unittest.TestCase):
    def test_collects_gpu_and_process_info(self):
        outputs = {
            (
                "nvidia-smi",
                "--query-gpu=index,name,uuid,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits",
            ): "0, NVIDIA A100, GPU-abc, 40960, 1024, 39936, 12, 41",
            (
                "nvidia-smi",
                "--query-compute-apps=gpu_uuid,pid,process_name,used_memory",
                "--format=csv,noheader,nounits",
            ): "GPU-abc, 1234, python, 900",
            ("ps", "-p", "1234", "-o", "user=", "-o", "pid=", "-o", "ppid=", "-o", "etime=", "-o", "cmd="): (
                "alice 1234 100 01:02:03 python train.py"
            ),
        }

        def fake_run(command):
            return outputs[tuple(command)]

        with mock.patch("researchflow.core.gpu.shutil.which", return_value="/usr/bin/nvidia-smi"):
            with mock.patch("researchflow.core.gpu._run_command", side_effect=fake_run):
                gpu_infos = collect_gpu_info()

        self.assertEqual(len(gpu_infos), 1)
        self.assertEqual(gpu_infos[0].name, "NVIDIA A100")
        self.assertEqual(gpu_infos[0].processes[0].process.user, "alice")

        text = format_gpu_info_for_text(gpu_infos)
        self.assertIn("GPU 0 | NVIDIA A100", text)
        self.assertIn("pid 1234 | user alice", text)


if __name__ == "__main__":
    unittest.main()
