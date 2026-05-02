import csv
import shutil
import subprocess
import sys
from dataclasses import dataclass
from io import StringIO
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ProcessInfo:
    pid: str
    user: str = "N/A"
    ppid: str = "N/A"
    elapsed: str = "N/A"
    command: str = "N/A"


@dataclass(frozen=True)
class GpuProcessInfo:
    gpu_uuid: str
    pid: str
    process_name: str
    used_memory_mib: str
    process: ProcessInfo


@dataclass(frozen=True)
class GpuInfo:
    index: str
    name: str
    uuid: str
    memory_total_mib: str
    memory_used_mib: str
    memory_free_mib: str
    utilization_gpu_percent: str
    temperature_gpu_c: str
    processes: List[GpuProcessInfo]


def _run_command(command: List[str]) -> Optional[str]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _parse_csv_rows(output: str) -> List[List[str]]:
    if not output:
        return []
    reader = csv.reader(StringIO(output))
    return [[cell.strip() for cell in row] for row in reader if row]


def _get_ps_info(pid: str) -> ProcessInfo:
    output = _run_command(["ps", "-p", pid, "-o", "user=", "-o", "pid=", "-o", "ppid=", "-o", "etime=", "-o", "cmd="])
    if not output:
        return ProcessInfo(pid=pid)

    parts = output.strip().split(None, 4)
    if len(parts) < 5:
        return ProcessInfo(pid=pid)

    user, parsed_pid, ppid, elapsed, command = parts
    return ProcessInfo(
        pid=parsed_pid,
        user=user,
        ppid=ppid,
        elapsed=elapsed,
        command=command,
    )


def collect_gpu_info() -> List[GpuInfo]:
    if shutil.which("nvidia-smi") is None:
        return []

    gpu_output = _run_command([
        "nvidia-smi",
        "--query-gpu=index,name,uuid,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu",
        "--format=csv,noheader,nounits",
    ])
    if gpu_output is None:
        return []

    gpu_rows = _parse_csv_rows(gpu_output)
    process_output = _run_command([
        "nvidia-smi",
        "--query-compute-apps=gpu_uuid,pid,process_name,used_memory",
        "--format=csv,noheader,nounits",
    ])
    process_rows = _parse_csv_rows(process_output or "")

    processes_by_gpu: Dict[str, List[GpuProcessInfo]] = {}
    for row in process_rows:
        if len(row) < 4:
            continue
        gpu_uuid, pid, process_name, used_memory_mib = row[:4]
        ps_info = _get_ps_info(pid)
        processes_by_gpu.setdefault(gpu_uuid, []).append(
            GpuProcessInfo(
                gpu_uuid=gpu_uuid,
                pid=pid,
                process_name=process_name,
                used_memory_mib=used_memory_mib,
                process=ps_info,
            )
        )

    gpu_infos: List[GpuInfo] = []
    for row in gpu_rows:
        if len(row) < 8:
            sys.stderr.write(f"[GpuInfo] Ignoring unexpected nvidia-smi row: {row}\n")
            continue

        index, name, uuid, total, used, free, utilization, temperature = row[:8]
        gpu_infos.append(
            GpuInfo(
                index=index,
                name=name,
                uuid=uuid,
                memory_total_mib=total,
                memory_used_mib=used,
                memory_free_mib=free,
                utilization_gpu_percent=utilization,
                temperature_gpu_c=temperature,
                processes=processes_by_gpu.get(uuid, []),
            )
        )

    return gpu_infos


def _to_float(value: str) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_percent(numerator: str, denominator: str) -> str:
    used = _to_float(numerator)
    total = _to_float(denominator)
    if used is None or total is None or total <= 0:
        return "N/A"
    return f"{(used / total) * 100:.1f}%"


def format_gpu_info_for_text(gpu_infos: List[GpuInfo]) -> str:
    if not gpu_infos:
        return ""

    lines: List[str] = []
    for gpu in gpu_infos:
        memory_percent = _format_percent(gpu.memory_used_mib, gpu.memory_total_mib)
        lines.append(
            f"*GPU {gpu.index}* | {gpu.name}"
        )
        lines.append(
            f"VRAM {gpu.memory_used_mib}/{gpu.memory_total_mib} MiB ({memory_percent}) | "
            f"util {gpu.utilization_gpu_percent}% | temp {gpu.temperature_gpu_c}C"
        )
        if not gpu.processes:
            lines.append("Details: no active compute processes")
            continue

        lines.append("Details:")
        for proc in gpu.processes:
            process_percent = _format_percent(proc.used_memory_mib, gpu.memory_total_mib)
            lines.append(
                f"- {proc.process.user} | pid {proc.pid} | "
                f"{proc.used_memory_mib} MiB ({process_percent}) | elapsed {proc.process.elapsed}"
            )

    return "\n".join(lines)
