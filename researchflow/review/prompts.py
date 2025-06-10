from typing import Dict

DEFAULT_SYSTEM_INSTRUCTION_EN = (
    "You are an expert research paper reviewer. Your task is to analyze the provided research paper. "
    "Focus on the paper's core contributions, methodology, key results, and potential impact. "
    "Please structure your output clearly."
)
DEFAULT_USER_PROMPT_EN = (
    "Please review the attached research paper. I need a comprehensive analysis covering the following aspects:\n"
    "1.  **Title**: Suggest a concise title if the original is too long or unclear, otherwise use the original.\n"
    "2.  **Core Idea/Summary**: A brief summary of the paper's main purpose and findings (1-2 paragraphs).\n"
    "3.  **Key Contributions**: List the main contributions of this work.\n"
    "4.  **Methodology**: Briefly describe the methods used.\n"
    "5.  **Strengths**: What are the strengths of this paper?\n"
    "6.  **Weaknesses/Areas for Improvement**: What are the limitations or areas that could be improved?\n"
    "7.  **Overall Assessment & Potential Impact**: Your general thoughts on the paper and its potential significance.\n\n"
    "Provide the output in plain text, using markdown for formatting (e.g., bold for headings, bullet points for lists)."
)

DEFAULT_SYSTEM_INSTRUCTION_KO = (
    "당신은 전문 연구 논문 검토자입니다. 제공된 연구 논문을 분석하는 것이 당신의 임무입니다. "
    "논문의 핵심 기여, 방법론, 주요 결과 및 잠재적 영향에 중점을 두십시오. "
    "결과물을 명확하게 구성해 주세요."
)
DEFAULT_USER_PROMPT_KO = (
    "첨부된 연구 논문을 검토해 주십시오. 다음 측면을 다루는 포괄적인 분석이 필요합니다:\n"
    "1.  **제목**: 원본 제목이 너무 길거나 불분명한 경우 간결한 제목을 제안하고, 그렇지 않으면 원본 제목을 사용하십시오.\n"
    "2.  **핵심 아이디어/요약**: 논문의 주요 목적과 연구 결과에 대한 간략한 요약 (1-2 문단).\n"
    "3.  **주요 기여**: 이 연구의 주요 기여 사항을 나열하십시오.\n"
    "4.  **방법론**: 사용된 방법을 간략하게 설명하십시오.\n"
    "5.  **강점**: 이 논문의 강점은 무엇입니까?\n"
    "6.  **약점/개선 영역**: 이 논문의 한계점이나 개선할 수 있는 부분은 무엇입니까?\n"
    "7.  **종합 평가 및 잠재적 영향**: 논문에 대한 전반적인 생각과 잠재적 중요성.\n\n"
    "결과물을 일반 텍스트로 제공하고, 서식에는 마크다운을 사용하십시오 (예: 제목에는 굵게, 목록에는 글머리 기호 사용)."
)


SYSTEM_INSTRUCTIONS: Dict[str, str] = {
    "en": DEFAULT_SYSTEM_INSTRUCTION_EN,
    "ko": DEFAULT_SYSTEM_INSTRUCTION_KO,
}

USER_PROMPTS: Dict[str, str] = {
    "en": DEFAULT_USER_PROMPT_EN,
    "ko": DEFAULT_USER_PROMPT_KO,
}

def get_system_instruction(language_code: str = "ko") -> str:
    return SYSTEM_INSTRUCTIONS.get(language_code.lower(), DEFAULT_SYSTEM_INSTRUCTION_EN)

def get_user_prompt(language_code: str = "ko") -> str:
    return USER_PROMPTS.get(language_code.lower(), DEFAULT_USER_PROMPT_EN)
