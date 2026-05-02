import json
import os
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .constants import (
    RESEARCHFLOW_CONFIG_ENV_KEY,
)
from .utils import (
    ensure_dotenv_is_loaded,
    get_slack_bot_token_from_env,
    get_slack_channel_from_env,
    get_log_dir_from_env,
    get_slack_destination_from_env,
    get_slack_team_id_from_env,
    get_slack_user_id_from_env,
    get_slack_webhook_url_from_env,
)


VALID_DESTINATIONS = {"auto", "channel", "dm", "webhook", "off"}


@dataclass(frozen=True)
class ResearchFlowConfig:
    slack_destination: str = "auto"
    slack_bot_token: Optional[str] = None
    slack_channel: Optional[str] = None
    slack_user_id: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    slack_team_id: Optional[str] = None
    slack_team_name: Optional[str] = None
    log_dir: Optional[str] = None
    include_gpu: bool = True
    mention_user: bool = False


def get_default_config_path() -> Path:
    return Path.home() / ".config" / "researchflow" / "config.json"


def get_project_config_path() -> Path:
    return Path.cwd() / ".researchflow.json"


def get_config_template() -> Dict[str, Any]:
    return {
        "slack_destination": "auto",
        "slack_channel": "C0123456789",
        "slack_user_id": "U0123456789",
        "slack_team_id": "",
        "slack_team_name": "",
        "log_dir": "",
        "include_gpu": True,
        "mention_user": False,
    }


def _candidate_config_paths(config_path: Optional[str] = None) -> Iterable[Path]:
    ensure_dotenv_is_loaded()
    explicit_path = config_path or os.environ.get(RESEARCHFLOW_CONFIG_ENV_KEY)
    if explicit_path:
        yield Path(explicit_path).expanduser()
        return

    yield get_default_config_path()

    project_config_path = get_project_config_path()
    if project_config_path.exists():
        yield project_config_path


def _read_config_file(config_path: Optional[str] = None) -> Dict[str, Any]:
    merged_data: Dict[str, Any] = {}
    for path in _candidate_config_paths(config_path):
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                sys.stderr.write(f"[ResearchFlowConfig] Ignoring non-object config file: {path}\n")
                continue
            merged_data.update(data)
        except json.JSONDecodeError as e:
            sys.stderr.write(f"[ResearchFlowConfig] Ignoring invalid JSON in {path}: {e}\n")
            continue
        except OSError as e:
            sys.stderr.write(f"[ResearchFlowConfig] Could not read {path}: {e}\n")
            continue
    return merged_data


def _normalize_destination(value: Optional[str]) -> str:
    if not value:
        return "auto"
    normalized = value.strip().lower()
    if normalized not in VALID_DESTINATIONS:
        sys.stderr.write(
            f"[ResearchFlowConfig] Unknown slack_destination '{value}'. "
            "Using 'auto'.\n"
        )
        return "auto"
    return normalized


def _coerce_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def load_config(config_path: Optional[str] = None, **overrides: Any) -> ResearchFlowConfig:
    file_data = _read_config_file(config_path)

    config = ResearchFlowConfig(
        slack_destination=_normalize_destination(file_data.get("slack_destination")),
        slack_bot_token=file_data.get("slack_bot_token"),
        slack_channel=file_data.get("slack_channel"),
        slack_user_id=file_data.get("slack_user_id"),
        slack_webhook_url=file_data.get("slack_webhook_url"),
        slack_team_id=file_data.get("slack_team_id"),
        slack_team_name=file_data.get("slack_team_name"),
        log_dir=file_data.get("log_dir"),
        include_gpu=_coerce_bool(file_data.get("include_gpu"), True),
        mention_user=_coerce_bool(file_data.get("mention_user"), False),
    )

    env_destination = get_slack_destination_from_env()
    env_config = {
        "slack_destination": _normalize_destination(env_destination) if env_destination else config.slack_destination,
        "slack_bot_token": get_slack_bot_token_from_env() or config.slack_bot_token,
        "slack_channel": get_slack_channel_from_env() or config.slack_channel,
        "slack_user_id": get_slack_user_id_from_env() or config.slack_user_id,
        "slack_webhook_url": get_slack_webhook_url_from_env() or config.slack_webhook_url,
        "slack_team_id": get_slack_team_id_from_env() or config.slack_team_id,
        "log_dir": get_log_dir_from_env() or config.log_dir,
    }
    config = replace(config, **env_config)

    clean_overrides = {}
    for key, value in overrides.items():
        if value is None:
            continue
        if key == "slack_destination":
            clean_overrides[key] = _normalize_destination(value)
        else:
            clean_overrides[key] = value

    if clean_overrides:
        config = replace(config, **clean_overrides)

    return config


def write_default_config(path: Optional[str] = None, overwrite: bool = False) -> Path:
    target_path = Path(path).expanduser() if path else get_default_config_path()
    if target_path.exists() and not overwrite:
        raise FileExistsError(f"Config file already exists: {target_path}")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("w", encoding="utf-8") as f:
        json.dump(get_config_template(), f, indent=2)
        f.write("\n")
    return target_path


def update_config_file(values: Dict[str, Any], path: Optional[str] = None) -> Path:
    target_path = Path(path).expanduser() if path else get_default_config_path()
    existing_data: Dict[str, Any] = {}
    if target_path.exists():
        try:
            with target_path.open("r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            if isinstance(loaded_data, dict):
                existing_data = loaded_data
        except (json.JSONDecodeError, OSError) as e:
            sys.stderr.write(f"[ResearchFlowConfig] Could not merge existing config {target_path}: {e}\n")

    existing_data.update({key: value for key, value in values.items() if value is not None})
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2)
        f.write("\n")
    return target_path
