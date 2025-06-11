# researchflow

`researchflow` is a command-line tool designed to streamline research workflows by automating notifications for script executions and generating AI-powered reviews of research papers.

_README in Korean can be found [here](readme_ko.md)._

## 1\. Setup

First, clone the repository and install the necessary dependencies.

```bash
git clone https://github.com/mjk0618/researchflow.git
cd researchflow
pip install -e .
```

## 2\. Usage Examples

### 2.1 alarm: Script Execution Notifier

The `alarm` command executes a target Python script and sends a notification to a Slack channel with the results (e.g., success or failure, execution time, arguments).

You can test the `alarm` functionality by running the sample script from the project's root directory:

```bash
alarm examples/sample_script.py
```

  * **Background Execution (`--log`)**: Using the `--log` flag runs the script in the background and creates a log file, similar to `nohup`.

  * **Reporting Arguments**: To include the script's arguments in the Slack notification, import and call the `report_arguments` function from `researchflow.core.utils` after parsing arguments in your script.

    ```python
    # In your script (e.g., examples/sample_script.py)
    from researchflow.core.utils import report_arguments

    def main():
        # ... (argument parsing code)
        args = parser.parse_args()
        report_arguments(args) # Call this function
        # ... (rest of your script)
    ```

### 2.2 review: AI-Powered Paper Reviewer

The `review` command uses the Gemini API to review a research paper from an arXiv URL and sends a formatted summary to a Slack channel.

  * `paper_input`: You must provide the arXiv URL for the paper you want to review.
  * `--user-interests` (or `-u`): You can specify your research interests to tailor the review's evaluation.

Here’s how to review the famous "Attention Is All You Need" paper:

```bash
# Basic review
review https://arxiv.org/pdf/1706.03762

# Review with user interests
review https://arxiv.org/pdf/1706.03762 -u "LLM" "NLP"
```

*Note: The `review` feature is under development and may be unstable.*

## 3\. Configuration

### 3.1 Setting Up Environment Variables

Environment variables are required for Slack notifications and Gemini API integration. Create a `.env` file in the root directory of the project and add your credentials as shown below.

**Directory Structure:**

```
researchflow/
├── examples
├── pyproject.toml
├── README.md
├── researchflow
└── .env (Create this file)
```

**`.env` file content:**

```
SLACK_WEBHOOK_URL="YOUR_SLACK_WEBHOOK_URL"
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```

### 3.2 Obtaining a Slack Webhook URL

Follow these steps to generate a Slack Webhook URL, which is required for the `alarm` and `review` commands to send messages to a Slack channel.

1.  **Create or Select a Slack App**:
      * Navigate to the [Slack API website](https://api.slack.com/apps).
      * Click "Create New App" or select an existing one.
      * When creating a new app, choose "From scratch," provide an app name, and select your workspace.
2.  **Enable Incoming Webhooks**:
      * In the app's settings page, go to "Incoming Webhooks" under the "Features" section in the left sidebar.
      * Toggle the "Activate Incoming Webhooks" switch to "On".
3.  **Add a New Webhook URL**:
      * Click the "Add New Webhook to Workspace" button.
      * Choose the channel where messages will be posted and click "Allow."
4.  **Copy the Webhook URL**:
      * Copy the generated Webhook URL and paste it as the value for `SLACK_WEBHOOK_URL` in your `.env` file.

For more details, refer to the official documentation on [Sending messages using Incoming Webhooks](https://api.slack.com/messaging/webhooks).

### 3.3 Obtaining a Gemini API Key

An API key is necessary for the `review` command. Follow these steps to get your Gemini API key.

1.  **Go to Google AI Studio**:
      * Visit the [Google AI Studio](https://aistudio.google.com/) website.
2.  **Generate an API Key**:
      * Click "Get API key" in the top right corner.
      * On the next page, click "Create API key".
3.  **Copy the API Key**:
      * Copy the generated key and paste it as the value for `GEMINI_API_KEY` in your `.env` file.

For more details, refer to the [Generative AI Quickstart guide](https://ai.google.dev/gemini-api/docs/api-key).