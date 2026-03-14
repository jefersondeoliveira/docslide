import os
import time
from typing import List, Tuple

import openai
from rich.console import Console

from .models import AnalysisResult, DocSummary, Document

TOKEN_THRESHOLD = 80_000

console = Console()

ANALYSIS_SYSTEM_PROMPT = """\
You are an expert presentation designer. Analyze the provided document corpus and return a structured \
analysis that will drive slide generation.

Choose the theme based on content:
- "dark-tech": technical content, code, engineering, APIs, data
- "clean-corporate": business reports, strategy, finance, presentations to executives
- "gradient-modern": startups, creative, design, marketing, innovation

For "gradient-modern", set background_color to the sentinel value "gradient".
For other themes, set background_color to an appropriate hex color (e.g. "#0d1117" for dark-tech, \
"#ffffff" for clean-corporate).

Set accent_color to a hex color that complements the theme and content.
Set suggested_slide_count between 5 and 20 based on content depth.
Provide a concise, compelling title and subtitle for the presentation.
List the key topics covered in the corpus.
"""

SUMMARIZE_SYSTEM_PROMPT = """\
You are a precise document summarizer. Summarize the provided document in clear prose, \
capturing all key points, arguments, data, and conclusions. \
The summary should be comprehensive yet concise — aim for roughly 400-500 tokens.
"""


def _call_parse(response_format, messages):
    """Call the OpenAI structured output endpoint, retrying once on RateLimitError."""
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")
    try:
        response = client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=response_format,
        )
        return response.choices[0].message.parsed
    except openai.RateLimitError:
        console.print("Rate limit, retrying in 60s...")
        time.sleep(60)
        response = client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=response_format,
        )
        return response.choices[0].message.parsed


def _summarize_document(doc: Document) -> str:
    messages = [
        {"role": "system", "content": SUMMARIZE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Document: {doc.filename}\n\n{doc.content}",
        },
    ]
    result: DocSummary = _call_parse(DocSummary, messages)
    return result.summary


def _analyze_corpus(corpus_text: str) -> AnalysisResult:
    messages = [
        {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
        {"role": "user", "content": corpus_text},
    ]
    return _call_parse(AnalysisResult, messages)


def analyze(docs: List[Document]) -> Tuple[AnalysisResult, str]:
    total_tokens = sum(doc.token_count for doc in docs)

    if total_tokens <= TOKEN_THRESHOLD:
        console.print("[bold]Analyzing corpus...[/bold]")
        corpus_text = "\n---\n".join(doc.content for doc in docs)
    else:
        console.print("[bold]Summarizing documents (map-reduce)...[/bold]")
        summaries = [_summarize_document(doc) for doc in docs]
        corpus_text = "\n---\n".join(summaries)
        console.print("[bold]Analyzing corpus...[/bold]")

    result = _analyze_corpus(corpus_text)
    return result, corpus_text
