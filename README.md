# researchflow


## 1. Setup

```bash
git clone https://github.com/mjk0618/researchflow.git
cd researchflow
pip install -e .
```

### 환경 변수 설정

Slack 알림 및 Gemini API 연동을 위해 환경 변수가 필요합니다. 
Root Directory에 `.env` 파일을 생성하고 아래와 같이 설정합니다.
```
researchflow/
├── examples
├── pyproject.toml
├── README.md
├── researchflow
├── src
└── .env (새로 생성)
```

```
SLACK_WEBHOOK_URL="YOUR_SLACK_WEBHOOK_URL"
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```

## 2. Get Slack Webhook

Slack 웹훅(Webhook) URL을 생성하여 `alarm` 명령어를 통해 Slack 채널로 메시지를 보낼 수 있도록 설정하는 방법입니다.

1.  **Slack 앱 생성 또는 기존 앱 선택**:
      * [Slack API 웹사이트](https://api.slack.com/apps)에 접속합니다.
      * "Create New App" 버튼을 클릭하거나, 이미 생성된 앱이 있다면 해당 앱을 선택합니다.
      * 앱 생성 시 "From scratch"를 선택하고 앱 이름과 작업 공간(Workspace)을 지정합니다.
2.  **Incoming Webhooks 활성화**:
      * 앱 설정 페이지 좌측 사이드바에서 "Features" 아래의 "Incoming Webhooks"를 클릭합니다.
      * "Activate Incoming Webhooks" 토글을 "On"으로 설정합니다.
3.  **새 웹훅 URL 추가**:
      * "Add New Webhook to Workspace" 버튼을 클릭합니다.
      * 메시지를 게시할 채널을 선택하고 "Allow"를 클릭합니다.
4.  **웹훅 URL 복사**:
      * 생성된 웹훅 URL을 복사하여 `.env` 파일의 `SLACK_WEBHOOK_URL` 변수에 붙여넣습니다.

더 자세한 내용은 [Sending messages using Incoming Webhooks](https://api.slack.com/messaging/webhooks) 문서를 참고해 주세요.

## 3. Get Gemini API

Gemini API 키를 발급받아 `review` 명령어를 통해 Slack 채널로 논문 리뷰를 전송할 수 있도록 설정하는 방법입니다.

1.  **Google AI Studio 접속**:
      * [Google AI Studio](https://aistudio.google.com/) 웹사이트에 접속합니다.
2.  **API 키 생성**:
      * 우측 위 "Get API key"를 클릭해서 페이지를 이동합니다.
      * 우측 위 "API 키 만들기"를 클릭해서 API Key를 생성합니다.
3.  **API 키 복사**:
      * 생성된 API 키를 복사하여 `.env` 파일의 `GEMINI_API_KEY` 변수에 붙여넣습니다.

더 자세한 내용은 [Generative AI Quickstart](https://ai.google.dev/gemini-api/docs/api-key) 문서를 참고해 주세요.

-----

사용 예시는 [examples](examples/readme.md)를 참고해 주세요.