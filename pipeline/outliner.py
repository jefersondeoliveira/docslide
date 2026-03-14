import os
import time

import openai
from rich.console import Console

from pipeline.models import AnalysisResult, Outline

console = Console()

_SYSTEM_PROMPT = """\
You are a presentation outline generator. Given source material and an analysis, \
produce a structured slide outline following these rules:

- The first slide MUST have type "title".
- The last slide MUST have type "closing". Set `message` to the main tagline or \
call-to-action and `submessage` to "Thank you" or an equivalent closing phrase.
- "content" slides: include 3–5 concise bullets each.
- "two-column" slides: use for comparisons, pros/cons, or before/after contrasts.
- "code" slides: only include if the source material contains actual code snippets.
- Aim for the number of slides specified by `suggested_slide_count`; you may vary \
±3 based on content needs.

Respond only with a valid JSON object matching the Outline schema.
"""


def generate(corpus_text: str, analysis: AnalysisResult) -> Outline:
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    client = openai.OpenAI(api_key=api_key)

    user_message = (
        f"Source material:\n{corpus_text}\n\n"
        f"Analysis:\n{analysis.model_dump_json(indent=2)}"
    )

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    console.print("[bold]Generating slide outline...[/bold]")

    def _call() -> Outline:
        response = client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=Outline,
        )
        return response.choices[0].message.parsed

    try:
        return _call()
    except openai.RateLimitError:
        print("Rate limit, retrying in 60s...")
        time.sleep(60)
        return _call()
    except openai.APIError:
        raise
