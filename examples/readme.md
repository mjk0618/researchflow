# Usage Example

## alarm

`alarm` 명령어는 스크립트 실행 결과를 Slack으로 알림으로 전송합니다. 


프로젝트의 Root Directory에서 다음 명령어를 실행하여 `alarm` 기능이 정상적으로 작동하는지 확인할 수 있습니다:

```bash
alarm examples/sample_script.py
```


- `--log` 인자를 사용하면 `nohup` 명령어처럼 백그라운드에서 실행되며 log 파일을 생성합니다.

    - 내부적으로는 다음과 같은 명령어가 실행됩니다:

        ```bash
        nohup alarm <script_to_run> [script_arguments] > <script_name>.log 2>&1 &
        ```

- 실행하려는 Python Script에서 아래와 같은 함수를 import하고 argument parsing이 이뤄진 후, 이 함수를 호출하면 Slack 알림에 스크립트 실행에 사용한 인자를 함께 출력할 수 있습니다.
    ```python
    from researchflow.core.utils import report_arguments
    ...
    def main():
        ...
        args = parser.parse_args()
        report_arguments(args)  
        ...
    ```

## review

`review` 명령어는 Gemini API를 사용하여 논문을 리뷰하고, 그 결과를 Slack으로 전송합니다.

- `paper_input`에는 리뷰하려는 논문의 arxiv PDF URL을 입력해야 합니다.
- `--user-interests`를 사용하면 사용자의 관심 분야를 반영하여 논문을 리뷰합니다. 
    - `-u`와 같이 단축된 형태로 사용할 수 있습니다.



다음 명령어를 사용하여 유명한 "Attention Is All You Need" 논문을 리뷰할 수 있습니다:

```bash
review https://arxiv.org/pdf/1706.03762
review https://arxiv.org/pdf/1706.03762 -u "LLM", "NLP"
```

- review 기능은 코드가 완전하지 않아 불안정할 수 있습니다.