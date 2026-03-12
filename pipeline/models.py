from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class Document(BaseModel):
    filename: str
    content: str
    token_count: int


class AnalysisResult(BaseModel):
    title: str
    subtitle: str
    theme: Literal["dark-tech", "clean-corporate", "gradient-modern"]
    accent_color: str           # hex, e.g. "#58a6ff"
    background_color: str       # hex e.g. "#0d1117" or sentinel "gradient"
    suggested_slide_count: int = Field(ge=5, le=20)
    topics: List[str]


class SlideSpec(BaseModel):
    type: Literal["title", "content", "two-column", "code", "closing"]
    title: str
    subtitle: Optional[str] = None
    bullets: Optional[List[str]] = None
    left_title: Optional[str] = None
    left_bullets: Optional[List[str]] = None
    right_title: Optional[str] = None
    right_bullets: Optional[List[str]] = None
    language: Optional[str] = None
    code: Optional[str] = None
    message: Optional[str] = None
    submessage: Optional[str] = None


class Outline(BaseModel):
    slides: List[SlideSpec]


class DocSummary(BaseModel):
    summary: str
