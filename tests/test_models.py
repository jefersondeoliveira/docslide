import pytest
from pipeline.models import (
    Document, AnalysisResult, SlideSpec, Outline, DocSummary
)

def test_document_model():
    doc = Document(filename="test.md", content="hello", token_count=1)
    assert doc.filename == "test.md"

def test_analysis_result_theme_validation():
    with pytest.raises(Exception):
        AnalysisResult(
            title="T", subtitle="S", theme="invalid-theme",
            accent_color="#fff", background_color="#000",
            suggested_slide_count=10, topics=[]
        )

def test_analysis_result_slide_count_bounds():
    with pytest.raises(Exception):
        AnalysisResult(
            title="T", subtitle="S", theme="dark-tech",
            accent_color="#58a6ff", background_color="#0d1117",
            suggested_slide_count=100, topics=[]  # > 20, should fail
        )

def test_slide_spec_types():
    slide = SlideSpec(type="content", title="My Slide", bullets=["a", "b"])
    assert slide.type == "content"
    assert slide.code is None

def test_outline_contains_slides():
    outline = Outline(slides=[
        SlideSpec(type="title", title="Hello"),
        SlideSpec(type="closing", title="End", message="Thanks", submessage="Bye"),
    ])
    assert len(outline.slides) == 2

def test_doc_summary():
    s = DocSummary(summary="A brief summary of the document.")
    assert "summary" in s.summary
