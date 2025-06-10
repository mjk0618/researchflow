import httpx
import json
import os
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from google import genai
from google.genai import types

class Author(BaseModel):
    name: str
    affiliation: Optional[str] = None
    url: Optional[str] = None

class MetaData(BaseModel):
    id: str = Field(
        pattern=r'^(\d{4}\.\d{4,5}(v\d+)?|[a-z\-]+(\.[A-Z]{2})?/\d{7})$'
    )
    title: str
    authors: List[Author]
    date: datetime
    abstract: Optional[str] = None
    categories: Optional[List[str]] = None
    # doi: Optional[str] = None
    journal_ref: Optional[str] = None
    # updated_date: Optional[datetime] = None
    pdf_url: Optional[str] = None

class Evaluation(BaseModel):
    completeness: int = Field(ge=1, le=10)
    originality: int = Field(ge=1, le=10)
    clarity: int = Field(ge=1, le=10)
    impact: int = Field(ge=1, le=10)
    interest_relevance: int = Field(ge=1, le=10)
    justification: str

class Review(BaseModel):
    summary: str
    contribution_and_method: List[str]
    limitations_and_further_study: List[str]
    insights: List[str]
    related_works: List[str]
    recommended_papers: List[str]
    evaluation: Evaluation

class GeminiAgent:
    def __init__(self, api_key, user_interests: Optional[List[str]] = None,
                 default_model = "gemini-2.5-flash-preview-05-20"):
        self.agent = None
        self.default_model = default_model
        self.user_interests = user_interests or []
        self._setup_agent(api_key)

    def _setup_agent(self, api_key: str):
        self.agent = genai.Client(api_key=api_key)
        
    def _prepare_file_content(self, url: str) -> types.Part:
        pdf_url = url.replace("/abs/", "/pdf/") if "/abs/" in url else url
        # if not pdf_url.endswith(".pdf"):
        #      pdf_url += ".pdf"
        content = httpx.get(pdf_url).content
        return types.Part.from_bytes(
            data=content,
            mime_type="application/pdf",
        )
    
    def review_paper(self, url: str, model: Optional[str] = None) -> Review:
        paper_content = self._prepare_file_content(url)
        
        review_response = self.agent.models.generate_content(
            model=model if model else self.default_model,
            contents=[paper_content],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=Review,
                system_instruction=self._get_system_instruction()
            ),
        )
        
        return Review.model_validate_json(review_response.text)

    def _get_system_instruction(self) -> str:
        interest_prompt_part = ""
        if self.user_interests:
            interests_str = ", ".join(self.user_interests)
            interest_prompt_part = f"""    - **interest_relevance(관심사 관련성)**: 사용자의 관심 분야인 [{interests_str}]와 논문의 주제가 얼마나 깊은 관련이 있는지 평가하세요."""

        return f"""당신은 주어진 논문을 전문적으로 분석하고, 아래 지침에 따라 냉철하고 비판적인 관점에서 리뷰를 생성하는 AI 리뷰어입니다.

    **출력 형식 및 언어 규칙:**
    - 결과는 반드시 요청된 JSON 형식에 맞춰 출력해야 합니다.
    - 각 필드의 내용은 간결하고 명확한 서술체("~함", "~했음" 등)로 작성하세요.
    - 부자연스러운 의역을 지양하고, 기술적인 용어는 통상적으로 사용되는 번역어가 없을 경우 영문 원문을 그대로 표기하세요.
    - 통상적으로 사용되는 번역어가 있을 경우에도 혼동을 피하기 위해 원문을 괄호 안에 함께 표기하세요.
    - 모든 Bullet Point 항목은 최대 3개의 항목으로 제한하세요.

    **평가 및 분석 지침:**
    - 'evaluation' 항목에서는 논문을 매우 비판적이고 엄격한 관점에서 평가해야 합니다. 사소하더라도 기준에 미치지 못하는 부분은 과감하게 감점 처리하세요.
    - 'related_works' 항목은 논문의 주요 기반이 되는 '관련 연구 분야(Research Fields)'를 영문으로 나열해야 합니다. 너무 세부적인 주제나 중복적인 내용을 피하고, 포괄적인 상위 분야를 중심으로 3개 이내로 기술하세요.

    **요약 및 핵심 내용:**
    1.  **summary**: 논문의 핵심 목표, 방법론, 결과를 포함하여 3-5줄의 완성된 문단으로 요약하세요.
    2.  **contribution_and_method**: 이 논문이 학계나 산업에 기여하는 바(Contribution)와, 이를 위해 제안한 독창적인 핵심 방법론(Novelty)을 중심으로 간결하게 요약하세요.
    3.  **limitations_and_further_study**: 논문 저자가 명시적으로 언급했거나, 분석을 통해 발견된 방법론적/실험적 한계점을 지적하고, 각 한계의 근거가 되는 논문 섹션(e.g., Section 4.2, 'Ablation Studies')을 명시하십시오. 이를 바탕으로 가능한 향후 연구 방향을 제시하세요.
    4.  **insights**: 논문의 내용을 바탕으로 간접적으로 얻을 수 있는 핵심적인 가치를 발견하세요.
    5.  **related_works**: 논문의 주요 기반이 되는 관련 연구 분야(Research Fields)를 **영문**으로 나열하세요. (예: Knowledge Distillation, Instruction Tuning, Reasoning in LLMs)
    6.  **recommended_papers**: 논문의 핵심 개념을 더 깊이 이해하는 데 도움이 되거나, 연구의 이론적 기반이 되는 중요 논문(foundational papers) 또는 논문에서 직접 인용한 핵심 참고 문헌을 2-3개 추천하세요.

    **평가 기준:**
    {interest_prompt_part}
        - **completeness(완성도)**: 연구의 구성, 실험, 설명이 얼마나 체계적이고 완전한가.
        - **originality(독창성)**: 제안된 아이디어나 접근법이 기존 연구와 비교하여 얼마나 새롭고 독창적인가.
        - **clarity(명료성)**: 논문의 주장과 내용이 얼마나 명확하고 이해하기 쉽게 서술되었는가.
        - **impact(기대 효과)**: 연구 결과가 해당 분야에 미칠 잠재적 영향력이나 기여도가 얼마나 큰가.
    """

    def get_metadata(self, url: str, model: Optional[str] = None) -> MetaData:
        paper_content = self._prepare_file_content(url)
        prompt = f"""Extract the metadata for the paper from the provided sources. 
If any piece of information cannot be found, please leave the corresponding field empty or null.

Paper Abstract URL: {url}"""

        metadata_response = self.agent.models.generate_content(
            model=model if model else "gemini-2.0-flash",
            contents=[prompt, paper_content],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=MetaData
            )
        )

        return MetaData.model_validate_json(metadata_response.text)

def format_paper_data_for_slack(metadata: MetaData, review: Review) -> Dict[str, Any]:
    authors_formatted = []
    if metadata.authors:
        for author in metadata.authors[:2]:
            author_str = author.name
            if author.affiliation:
                author_str += f" ({author.affiliation})"
            authors_formatted.append(author_str)

    date_formatted = ""
    if metadata.date:
        date_formatted = metadata.date.strftime('%y-%m-%d')

    formatted_data = {
        "Title": metadata.title,
        "Authors": authors_formatted,
        "Date": date_formatted,
        "categories": metadata.categories,
        "pdf_url": metadata.pdf_url,
        "id": metadata.id
    }
    
    formatted_data.update(review.model_dump())
    return formatted_data