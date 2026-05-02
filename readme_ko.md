# researchflow

`researchflow`는 Python 실험 스크립트를 `alarm`으로 감싸 실행하고, 프로세스가 끝났을 때 Slack DM 또는 채널 메시지를 보내는 CLI 도구입니다.

## Quick Setup

연구실 사용자는 Slack App과 `.env`가 이미 준비되어 있다고 가정합니다. 패키지를 설치하고, 내 Slack DM 대상을 설정한 뒤 테스트 메시지를 보냅니다.

```bash
pip install -e .
alarm --setup "Slack 표시 이름"
```

사용자가 안 잡히면 실제 Slack 이름을 먼저 확인하세요.

```bash
alarm --list-slack-users
```

## Quick Usage

Python script 앞에 `alarm`을 붙이면 됩니다. script path 뒤의 인자는 그대로 원래 script에 전달됩니다.

```bash
alarm script.py --your-arg value
```

테스트 명령:

```bash
alarm tests/fixtures/sample_experiment.py --epochs 1 --total-runtime-factor 0
```

`--log`를 붙이면 백그라운드로 실행하고 stdout/stderr를 로그 파일로 저장합니다.

```bash
alarm --log script.py --your-arg value
```

## Setup

```bash
git clone https://github.com/mjk0618/researchflow.git
cd researchflow
pip install -e .
```

기본 DM 수신 대상 설정:

```bash
alarm --setup "Slack 표시 이름"
```

저장된 설정 확인:

```bash
alarm --print-config
```

사용자 설정 파일 위치:

```text
~/.config/researchflow/config.json
```

## Logging

`--log`는 stdout/stderr를 파일로 저장하고 script를 백그라운드로 실행합니다.

```bash
alarm --log train.py --config configs/run.yaml
```

기본 로그 저장 위치:

```text
<script_dir>/logs/{YYYYMMDD_HHMMSS_KST}_{script_name}.log
```

실행할 때마다 로그 디렉토리 지정:

```bash
alarm --log --log-dir /path/to/researchflow_logs train.py
```

기본 로그 디렉토리 저장:

```bash
alarm --set-log-dir /path/to/researchflow_logs
```

## Useful Commands

Slack 없이 실행:

```bash
alarm --destination off script.py
```

secret을 마스킹한 설정 확인:

```bash
alarm --print-config
```

메시지를 보내기 전에 현재 Slack target 확인:

```bash
alarm --check-slack-target
```

GPU/process snapshot 제어:

```bash
alarm --gpu-info script.py
alarm --no-gpu-info script.py
```

`alarm`은 `nvidia-smi`가 있으면 GPU 이름, VRAM 사용량, utilization, temperature, active compute PID, process owner, elapsed time, command를 알림에 포함할 수 있습니다.

테스트 산출물 삭제:

```bash
rm -rf test_artifacts
```

## 추가 기능

### 채널 메시지 설정

대부분의 연구실 사용자는 DM 설정을 쓰면 됩니다. 채널 메시지는 공용 알림이나 관리자용으로 사용합니다.

```bash
alarm --team-id T07CSJGATDW --list-slack-channels
alarm --team-id T07CSJGATDW --channel C08RV70M4FM --check-slack-target
```

특정 run만 채널로 전송:

```bash
alarm \
  --destination channel \
  --channel C08RV70M4FM \
  --team-id T07CSJGATDW \
  script.py --your-arg value
```

private channel은 먼저 bot을 초대해야 합니다.

```text
/invite @researchflow
```

### Interactive Setup

```bash
alarm --team-id T07CSJGATDW --configure-slack
alarm --team-id T07CSJGATDW --list-slack-users
```

### Slack App Setup

연구실 private 배포 전에는 관리자가 `.env`를 준비합니다.

```bash
RESEARCHFLOW_SLACK_BOT_TOKEN="xoxb-..."
RESEARCHFLOW_SLACK_TEAM_ID="T07CSJGATDW"
```

공용 Slack App에는 다음 bot scope가 필요합니다.

- `chat:write`: 메시지 전송
- `im:write`: DM conversation 열기
- `users:read`: `--setup` 및 user 검색
- `channels:read`: public channel 목록 조회
- `groups:read`: private channel 목록 조회

scope를 바꾼 뒤에는 Slack App을 workspace에 다시 reinstall 해야 합니다.

`RESEARCHFLOW_SLACK_BOT_TOKEN` 같은 secret은 `.env` 또는 서버 환경변수에만 두세요. 소스 코드, README, 패키지 배포물에 포함하면 안 됩니다.

## 실험 메타데이터

Slack 알림에 argparse 결과를 포함하려면 실험 스크립트에서 `report_arguments`를 호출하세요.

```python
from researchflow.core.utils import report_arguments

args = parser.parse_args()
report_arguments(args)
```
