import getpass
import sys
from typing import Any, Dict, List, Optional, Tuple

import requests

from .config import load_config, update_config_file


class SlackApiError(RuntimeError):
    def __init__(self, method: str, error: str, needed: Optional[str] = None, provided: Optional[str] = None):
        self.method = method
        self.error = error
        self.needed = needed
        self.provided = provided
        detail = f" needed={needed} provided={provided}" if needed or provided else ""
        super().__init__(f"{method} failed: {error}{detail}")


class SlackSetupClient:
    def __init__(self, token: str, team_id: Optional[str] = None):
        self.token = token
        self.team_id = team_id

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def _get(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = requests.get(
            f"https://slack.com/api/{method}",
            headers=self._headers(),
            params=params or {},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            error = data.get("error", "unknown_error")
            needed = data.get("needed")
            provided = data.get("provided")
            raise SlackApiError(method=method, error=error, needed=needed, provided=provided)
        return data

    def auth_test(self) -> Dict[str, Any]:
        return self._get("auth.test")

    def channel_info(self, channel_id: str) -> Dict[str, Any]:
        return self._get("conversations.info", {"channel": channel_id})

    def list_channels(self) -> List[Dict[str, Any]]:
        channels: List[Dict[str, Any]] = []
        cursor = ""
        while True:
            params = {
                "types": "public_channel,private_channel",
                "exclude_archived": "true",
                "limit": 200,
                "cursor": cursor,
            }
            if self.team_id:
                params["team_id"] = self.team_id
            data = self._get(
                "conversations.list",
                params,
            )
            channels.extend(data.get("channels", []))
            cursor = (data.get("response_metadata") or {}).get("next_cursor", "")
            if not cursor:
                break
        return channels

    def list_users(self) -> List[Dict[str, Any]]:
        users: List[Dict[str, Any]] = []
        cursor = ""
        while True:
            data = self._get("users.list", {"limit": 200, "cursor": cursor})
            users.extend(data.get("members", []))
            cursor = (data.get("response_metadata") or {}).get("next_cursor", "")
            if not cursor:
                break
        return users


def _prompt(text: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    return value or (default or "")


def _prompt_yes_no(text: str, default: bool = False) -> bool:
    default_text = "Y/n" if default else "y/N"
    value = input(f"{text} [{default_text}]: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes"}


def _format_channel(channel: Dict[str, Any]) -> str:
    prefix = "#" if not channel.get("is_private") else "private:"
    member_hint = "member" if channel.get("is_member") else "not-member"
    return f"{prefix}{channel.get('name', 'unknown')} ({channel.get('id')}, {member_hint})"


def _format_user(user: Dict[str, Any]) -> str:
    profile = user.get("profile") or {}
    display_name = profile.get("display_name") or profile.get("real_name") or user.get("name") or "unknown"
    return f"{display_name} ({user.get('id')}, @{user.get('name', 'unknown')})"


def _get_user_display_name(user: Dict[str, Any]) -> str:
    profile = user.get("profile") or {}
    return profile.get("display_name") or profile.get("real_name") or user.get("name") or user.get("id") or ""


def _format_slack_api_error(e: Exception, target: str) -> str:
    if not isinstance(e, SlackApiError):
        return str(e)
    if e.error != "missing_scope":
        return str(e)

    lines = [
        str(e),
        f"[SlackSetup] The configured token cannot list Slack {target}s yet.",
    ]
    if e.provided == "incoming-webhook":
        lines.append(
            "[SlackSetup] Slack says the app currently only has the incoming-webhook scope. "
            "That can send to the webhook's fixed channel, but it cannot list channels/users."
        )
    if target == "channel":
        lines.append("[SlackSetup] Add bot scopes channels:read and groups:read, then reinstall the Slack App to the workspace.")
    elif target == "user":
        lines.append("[SlackSetup] Add bot scope users:read, then reinstall the Slack App to the workspace.")
    lines.append("[SlackSetup] Message sending still requires chat:write, and DM sending requires im:write.")
    return "\n".join(lines)


def _filter_items(items: List[Dict[str, Any]], query: str, item_type: str) -> List[Dict[str, Any]]:
    if not query:
        return items
    query = query.lower()
    filtered = []
    for item in items:
        if item_type == "channel":
            haystack = " ".join([str(item.get("name", "")), str(item.get("id", ""))]).lower()
        else:
            profile = item.get("profile") or {}
            haystack = " ".join(
                [
                    str(item.get("name", "")),
                    str(item.get("id", "")),
                    str(profile.get("display_name", "")),
                    str(profile.get("real_name", "")),
                    str(profile.get("email", "")),
                ]
            ).lower()
        if query in haystack:
            filtered.append(item)
    return filtered


def _score_user_match(user: Dict[str, Any], query: str) -> int:
    profile = user.get("profile") or {}
    query = query.strip().lower()
    if not query:
        return 0

    candidates = [
        str(profile.get("display_name", "")),
        str(profile.get("real_name", "")),
        str(user.get("name", "")),
        str(user.get("id", "")),
        str(profile.get("email", "")),
    ]
    normalized_candidates = [candidate.lower() for candidate in candidates if candidate]

    if query in normalized_candidates:
        return 100
    if any(candidate.startswith(query) for candidate in normalized_candidates):
        return 70
    if any(query in candidate for candidate in normalized_candidates):
        return 40
    query_words = set(query.split())
    if query_words and any(query_words.issubset(set(candidate.split())) for candidate in normalized_candidates):
        return 30
    return 0


def _find_user_matches(users: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    scored = []
    for user in users:
        score = _score_user_match(user, query)
        if score:
            scored.append((score, user))
    scored.sort(key=lambda item: (-item[0], _format_user(item[1]).lower()))
    return [user for _, user in scored]


def _choose_item(items: List[Dict[str, Any]], item_type: str, manual_prefixes: Tuple[str, ...]) -> Optional[str]:
    if not items:
        sys.stdout.write(f"[SlackSetup] No {item_type}s returned. You can enter an ID manually.\n")

    while True:
        query = _prompt(f"Search {item_type}s, or press Enter to list")
        filtered = _filter_items(items, query, item_type)
        formatter = _format_channel if item_type == "channel" else _format_user
        visible = filtered[:30]

        for index, item in enumerate(visible, start=1):
            sys.stdout.write(f"{index:>2}. {formatter(item)}\n")

        if len(filtered) > len(visible):
            sys.stdout.write(f"... showing 30 of {len(filtered)} matches. Search more narrowly if needed.\n")

        choice = _prompt(f"Choose number or enter {item_type} ID")
        if choice.startswith(manual_prefixes):
            return choice
        if choice.isdigit():
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(visible):
                return visible[choice_index].get("id")
        sys.stderr.write("[SlackSetup] Invalid choice. Try again.\n")


def _resolve_token_and_team(
    config_path: Optional[str] = None,
    bot_token: Optional[str] = None,
    team_id: Optional[str] = None,
    destination: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str], Any]:
    current_config = load_config(config_path=config_path, slack_bot_token=bot_token, slack_destination=destination)
    token = current_config.slack_bot_token
    resolved_team_id = team_id or current_config.slack_team_id
    return token, resolved_team_id, current_config


def list_slack_channels(config_path: Optional[str] = None, bot_token: Optional[str] = None, team_id: Optional[str] = None) -> int:
    token, resolved_team_id, _ = _resolve_token_and_team(config_path=config_path, bot_token=bot_token, team_id=team_id)
    if not token:
        sys.stderr.write("[SlackSetup] Slack bot token is required. Set RESEARCHFLOW_SLACK_BOT_TOKEN or pass --bot-token.\n")
        return 1
    try:
        client = SlackSetupClient(token, team_id=resolved_team_id)
        auth = client.auth_test()
        sys.stdout.write(f"Workspace: {auth.get('team')} ({auth.get('team_id')})\n")
        for channel in client.list_channels():
            sys.stdout.write(f"{_format_channel(channel)}\n")
    except Exception as e:
        sys.stderr.write(f"[SlackSetup] Could not list Slack channels: {_format_slack_api_error(e, 'channel')}\n")
        return 1
    return 0


def list_slack_users(config_path: Optional[str] = None, bot_token: Optional[str] = None, team_id: Optional[str] = None) -> int:
    token, resolved_team_id, _ = _resolve_token_and_team(config_path=config_path, bot_token=bot_token, team_id=team_id)
    if not token:
        sys.stderr.write("[SlackSetup] Slack bot token is required. Set RESEARCHFLOW_SLACK_BOT_TOKEN or pass --bot-token.\n")
        return 1
    try:
        client = SlackSetupClient(token, team_id=resolved_team_id)
        auth = client.auth_test()
        sys.stdout.write(f"Workspace: {auth.get('team')} ({auth.get('team_id')})\n")
        users = [
            user
            for user in client.list_users()
            if not user.get("deleted") and not user.get("is_bot") and user.get("id") != "USLACKBOT"
        ]
        for user in users:
            sys.stdout.write(f"{_format_user(user)}\n")
    except Exception as e:
        sys.stderr.write(f"[SlackSetup] Could not list Slack users: {_format_slack_api_error(e, 'user')}\n")
        return 1
    return 0


def setup_dm_by_name(
    name_query: str,
    config_path: Optional[str] = None,
    bot_token: Optional[str] = None,
    team_id: Optional[str] = None,
    run_check: bool = True,
) -> int:
    token, resolved_team_id, _ = _resolve_token_and_team(config_path=config_path, bot_token=bot_token, team_id=team_id)
    if not token:
        sys.stderr.write("[SlackSetup] Slack bot token is required. Set RESEARCHFLOW_SLACK_BOT_TOKEN or pass --bot-token.\n")
        return 1
    if not name_query.strip():
        sys.stderr.write("[SlackSetup] A Slack display name, real name, handle, email, or user ID is required.\n")
        return 1

    try:
        client = SlackSetupClient(token, team_id=resolved_team_id)
        auth = client.auth_test()
        users = [
            user
            for user in client.list_users()
            if not user.get("deleted") and not user.get("is_bot") and user.get("id") != "USLACKBOT"
        ]
    except Exception as e:
        sys.stderr.write(f"[SlackSetup] Could not search Slack users: {_format_slack_api_error(e, 'user')}\n")
        return 1

    matches = _find_user_matches(users, name_query)
    if not matches:
        sys.stderr.write(f"[SlackSetup] No Slack user matched '{name_query}'. Try --list-slack-users to inspect names.\n")
        return 1

    top_score = _score_user_match(matches[0], name_query)
    top_matches = [user for user in matches if _score_user_match(user, name_query) == top_score]
    if len(top_matches) > 1:
        sys.stderr.write(f"[SlackSetup] More than one Slack user matched '{name_query}'. Refine the name or use a user ID.\n")
        for user in top_matches[:10]:
            sys.stderr.write(f"  - {_format_user(user)}\n")
        return 1

    selected_user = matches[0]
    selected_user_id = selected_user.get("id")
    config_updates = {
        "slack_destination": "dm",
        "slack_user_id": selected_user_id,
        "slack_user_name": _get_user_display_name(selected_user),
        "slack_user_query": name_query,
        "slack_channel": "",
        "slack_team_id": auth.get("team_id"),
        "slack_team_name": auth.get("team"),
    }
    written_path = update_config_file(config_updates, path=config_path)

    sys.stdout.write(f"[SlackSetup] Matched user: {_format_user(selected_user)}\n")
    sys.stdout.write(f"[SlackSetup] Updated DM config: {written_path}\n")
    if run_check:
        return check_slack_target(
            user_id=selected_user_id,
            config_path=config_path,
            bot_token=bot_token,
            team_id=resolved_team_id,
        )
    return 0


def check_slack_target(
    channel_id: Optional[str] = None,
    user_id: Optional[str] = None,
    config_path: Optional[str] = None,
    bot_token: Optional[str] = None,
    team_id: Optional[str] = None,
) -> int:
    token, resolved_team_id, current_config = _resolve_token_and_team(
        config_path=config_path,
        bot_token=bot_token,
        team_id=team_id,
    )
    if not token:
        sys.stderr.write("[SlackSetup] Slack bot token is required. Set RESEARCHFLOW_SLACK_BOT_TOKEN or pass --bot-token.\n")
        return 1

    target_channel = channel_id or current_config.slack_channel
    target_user = user_id or current_config.slack_user_id
    client = SlackSetupClient(token, team_id=resolved_team_id)

    try:
        auth = client.auth_test()
        sys.stdout.write(f"Workspace: {auth.get('team')} ({auth.get('team_id')})\n")
        sys.stdout.write(f"Bot/User ID: {auth.get('user_id')}\n")

        if target_channel:
            info = client.channel_info(target_channel)
            channel = info.get("channel") or {}
            name = channel.get("name") or channel.get("id")
            is_private = channel.get("is_private")
            is_member = channel.get("is_member")
            sys.stdout.write(f"Channel: {name} ({channel.get('id')}) private={is_private} member={is_member}\n")
            if is_private and not is_member:
                sys.stderr.write("[SlackSetup] Bot is not a member of this private channel. Invite it with /invite @bot-name.\n")
                return 1
            return 0

        if target_user:
            data = client._get("users.info", {"user": target_user})
            user = data.get("user") or {}
            sys.stdout.write(f"User: {_format_user(user)}\n")
            return 0

        sys.stderr.write("[SlackSetup] No target configured. Pass --channel or --dm.\n")
        return 1
    except Exception as e:
        target = "channel" if target_channel else "user"
        sys.stderr.write(f"[SlackSetup] Could not inspect Slack target: {_format_slack_api_error(e, target)}\n")
        if isinstance(e, SlackApiError) and e.error == "channel_not_found":
            sys.stderr.write(
                "[SlackSetup] For private channels, this usually means the bot is not a member, "
                "the channel ID belongs to a different workspace, or the app was not reinstalled after scope changes.\n"
            )
        return 1


def run_interactive_slack_setup(
    config_path: Optional[str] = None,
    bot_token: Optional[str] = None,
    team_id: Optional[str] = None,
    destination: Optional[str] = None,
) -> int:
    token, resolved_team_id, current_config = _resolve_token_and_team(
        config_path=config_path,
        bot_token=bot_token,
        team_id=team_id,
        destination=destination,
    )
    token_from_existing_config = bool(token)
    if not token:
        token = getpass.getpass("Slack bot token (xoxb-...): ").strip()

    if not token:
        sys.stderr.write("[SlackSetup] Slack bot token is required.\n")
        return 1

    client = SlackSetupClient(token, team_id=resolved_team_id)
    try:
        auth = client.auth_test()
    except Exception as e:
        sys.stderr.write(f"[SlackSetup] Could not verify Slack token: {e}\n")
        return 1

    team_name = auth.get("team")
    team_id = auth.get("team_id")
    bot_user_id = auth.get("user_id")
    sys.stdout.write(f"[SlackSetup] Connected to workspace: {team_name} ({team_id}) as {bot_user_id}\n")

    selected_destination = (destination or current_config.slack_destination or "auto").lower()
    if selected_destination == "auto":
        selected_destination = _prompt("Destination: channel or dm", "channel").lower()
    if selected_destination not in {"channel", "dm"}:
        sys.stderr.write("[SlackSetup] Interactive setup supports 'channel' or 'dm'.\n")
        return 1

    config_updates: Dict[str, Any] = {
        "slack_destination": selected_destination,
        "slack_team_id": team_id,
        "slack_team_name": team_name,
    }

    try:
        if selected_destination == "channel":
            channels = client.list_channels()
            selected_channel = _choose_item(channels, "channel", ("C", "G"))
            config_updates["slack_channel"] = selected_channel
            config_updates["slack_user_id"] = ""
        else:
            users = [
                user
                for user in client.list_users()
                if not user.get("deleted") and not user.get("is_bot") and user.get("id") != "USLACKBOT"
            ]
            selected_user = _choose_item(users, "user", ("U", "W"))
            config_updates["slack_user_id"] = selected_user
            config_updates["slack_channel"] = ""
    except Exception as e:
        target = "channel" if selected_destination == "channel" else "user"
        sys.stderr.write(f"[SlackSetup] Could not list Slack {selected_destination}s: {_format_slack_api_error(e, target)}\n")
        sys.stderr.write("[SlackSetup] Add the required read scope or set the ID manually in config.\n")
        return 1

    should_save_token = False
    if not token_from_existing_config:
        should_save_token = _prompt_yes_no("Save bot token into config file? Prefer .env for shared servers", False)
    if should_save_token:
        config_updates["slack_bot_token"] = token

    written_path = update_config_file(config_updates, path=config_path)
    sys.stdout.write(f"[SlackSetup] Updated config: {written_path}\n")
    if not should_save_token and not token_from_existing_config:
        sys.stdout.write("[SlackSetup] Keep this token in .env as RESEARCHFLOW_SLACK_BOT_TOKEN.\n")
    return 0
