# researchflow

## 1\. 설치


```bash
git clone https://github.com/mjk0618/researchflow.git
cd researchflow
pip install -e .
```

## 2\. 사용 예시

### 2.1 alarm: 스크립트 실행 알림

`alarm` 명령어는 대상 Python 스크립트의 실행 결과를 Slack 채널에 전송합니다.

프로젝트의 Root Directory에서 샘플 스크립트를 실행하여 `alarm` 기능을 테스트할 수 있습니다:

```bash
alarm examples/sample_script.py
```

  * **백그라운드 실행 (`--log`)**: `--log` 플래그를 사용하면 스크립트가 백그라운드에서 실행되고 `nohup`과 유사하게 로그 파일이 생성됩니다.

  * **명령줄 인자 출력**: Commandline arguments를 Slack 알림에 포함하려면, 스크립트에서 인자를 파싱한 후 `researchflow.core.utils`에서 `report_arguments` 함수를 불러온 후 호출하세요.

    ```python
    # 스크립트 내 (예: examples/sample_script.py)
    from researchflow.core.utils import report_arguments

    def main():
        # ... (argument parsing 코드)
        args = parser.parse_args()
        report_arguments(args) # 이 함수를 호출하세요
        # ... (나머지 코드)
    ```

### 2.2 review: AI 기반 논문 리뷰

`review` 명령어는 Gemini API를 사용하여 arXiv URL의 연구 논문을 리뷰하고 그 결과를 Slack 채널로 전송합니다.

  * `paper_input`: 리뷰하고자 하는 논문의 arXiv URL을 입력하세요.
  * `--user-interests` (또는 `-u`): 사용자의 관심사를 반영한 논문 리뷰를 수행합니다.

"Attention Is All You Need" 논문을 리뷰하는 예시입니다:

```bash
# 기본 리뷰
review https://arxiv.org/pdf/1706.03762

# 관심사 기반 리뷰
review https://arxiv.org/pdf/1706.03762 -u "LLM" "NLP"
```

*참고: `review` 기능은 불안정할 수 있습니다.*

## 3\. 설정

### 3.1 환경 변수 설정

Slack 알림 및 Gemini API 연동을 위해서는 환경 변수가 필요합니다. 프로젝트의 루트 디렉토리에 `.env` 파일을 생성하고 아래와 같이 환경 변수를 추가하세요.

**디렉토리 구조:**

```
researchflow/
├── examples
├── pyproject.toml
├── README.md
├── researchflow
└── .env (이 파일 생성)
```

**`.env` 파일 내용:**

```
SLACK_WEBHOOK_URL="YOUR_SLACK_WEBHOOK_URL"
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```

### 3.2 Slack Webhook URL 얻기

`alarm` 및 `review` 명령어가 Slack 채널로 메시지를 보내는 데 필요한 Slack 웹훅 URL을 생성하려면 다음 단계를 따르세요.

1.  **Slack 앱 생성 또는 선택**:
      * [Slack API 웹사이트](https://api.slack.com/apps)로 이동합니다.
      * "Create New App"을 클릭하거나 기존 앱을 선택합니다.
      * 새 앱을 생성할 때 "From scratch"를 선택하고, 앱 이름을 제공한 후 워크스페이스를 선택합니다.
2.  **Incoming Webhooks 활성화**:
      * 앱 설정 페이지의 왼쪽 사이드바 "Features" 섹션 아래에 있는 "Incoming Webhooks"로 이동합니다.
      * "Activate Incoming Webhooks" 스위치를 "On"으로 전환합니다.
3.  **새 웹훅 URL 추가**:
      * "Add New Webhook to Workspace" 버튼을 클릭합니다.
      * 메시지가 게시될 채널을 선택하고 "Allow"를 클릭합니다.
4.  **웹훅 URL 복사**:
      * 생성된 웹훅 URL을 복사하여 `.env` 파일의 `SLACK_WEBHOOK_URL` 값으로 붙여넣습니다.

자세한 내용은 [Incoming Webhooks를 사용하여 메시지 보내기](https://api.slack.com/messaging/webhooks)에 대한 공식 문서를 참조하세요.

### 3.3 Gemini API 키 얻기

`review` 명령어를 사용하려면 API 키가 필요합니다. Gemini API 키를 얻으려면 다음 단계를 따르세요.

1.  **Google AI Studio로 이동**:
      * [Google AI Studio](https://aistudio.google.com/) 웹사이트를 방문합니다.
2.  **API 키 생성**:
      * 오른쪽 상단에서 "Get API key"를 클릭합니다.
      * 다음 페이지에서 "Create API key"를 클릭합니다.
3.  **API 키 복사**:
      * 생성된 키를 복사하여 `.env` 파일의 `GEMINI_API_KEY` 값으로 붙여넣습니다.

자세한 내용은 [Generative AI Guide](https://ai.google.dev/gemini-api/docs/api-key)를 참조하세요.