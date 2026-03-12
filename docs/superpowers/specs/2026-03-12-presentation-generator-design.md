# Presentation Generator — Design Spec
Date: 2026-03-12

## Context

The user needs a CLI tool that reads a folder of documents (.md, .txt, .pdf, .docx) about a subject and automatically generates a polished, animated HTML presentation. The goal is to eliminate manual slide creation: just point the tool at a folder and get a presentation.html ready to open in any browser.

## Requirements

- **CLI**: `python generate.py ./input-folder/`
- **Input**: reads all .md, .txt, .pdf, .docx files from the given folder (flat, non-recursive)
- **Output**: `presentation.html` saved in the current working directory (overwrite if exists)
- **AI**: OpenAI API (key from `.env` file: `OPENAI_API_KEY`)
- **Presentation library**: Reveal.js 5.1 + GSAP 3.12 (both via CDN, pinned minor versions)
- **Theme/color**: AI chooses automatically based on content analysis
- **Control level**: fully automatic — no user review of outline

---

## Architecture

### Project Structure

```
presentation-generate/
├── generate.py          # CLI entry point and pipeline orchestrator
├── pipeline/
│   ├── __init__.py
│   ├── models.py        # Pydantic models shared across all steps
│   ├── extractor.py     # Step 1: read files, extract raw text
│   ├── analyzer.py      # Step 2: LLM analyzes corpus → theme/title/topics
│   ├── outliner.py      # Step 3: LLM generates slide-by-slide outline
│   └── renderer.py      # Step 4: assembles final HTML
├── templates/
│   └── base.html        # Reveal.js + GSAP base template (Jinja2)
├── .env                 # OPENAI_API_KEY=sk-...
├── requirements.txt
└── README.md
```

### Data Flow

```
folder/
  → extractor  → (docs: List[Document], summaries: Optional[List[str]])
                    ↓                              ↓
  → analyzer   → AnalysisResult            (summaries computed here if needed)
                    ↓                              ↓
  → outliner   → Outline  ←── receives AnalysisResult + corpus_text (str)
                    ↓
  → renderer   → presentation.html  ←── receives AnalysisResult + Outline
```

### Orchestration (`generate.py`)

```python
docs = extractor.extract(folder_path)                     # Step 1
analysis, corpus_text = analyzer.analyze(docs)            # Step 2
#   corpus_text = joined full text OR joined summaries (map-reduce)
#   analyzer returns both so outliner can use the same pre-computed text
outline = outliner.generate(corpus_text, analysis)         # Step 3
renderer.render(analysis, outline, output_path)            # Step 4
```

`rich` progress is printed before each step call.

---

## Data Models (`pipeline/models.py`)

```python
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
    background_color: str       # hex, e.g. "#0d1117"
    suggested_slide_count: int = Field(ge=5, le=20)
    topics: List[str]

class SlideSpec(BaseModel):
    type: Literal["title", "content", "two-column", "code", "closing"]
    title: str
    subtitle: Optional[str] = None           # title slides
    bullets: Optional[List[str]] = None      # content slides (3-5 items)
    left_title: Optional[str] = None         # two-column
    left_bullets: Optional[List[str]] = None
    right_title: Optional[str] = None
    right_bullets: Optional[List[str]] = None
    language: Optional[str] = None           # code slides
    code: Optional[str] = None
    message: Optional[str] = None            # closing: main tagline / call-to-action
    submessage: Optional[str] = None         # closing: secondary line (e.g. "Thank you")

class Outline(BaseModel):
    slides: List[SlideSpec]

class DocSummary(BaseModel):
    summary: str   # prose summary, max ~500 tokens
```

**OpenAI structured output call pattern** (same for all LLM calls):
```python
response = client.beta.chat.completions.parse(
    model=model,
    messages=[...],
    response_format=AnalysisResult,   # or Outline, DocSummary
)
result = response.choices[0].message.parsed
```
Use the `.parse()` method from `openai>=1.40.0` — it handles schema registration automatically and returns the validated Pydantic object directly.

---

## Pipeline Steps

### Step 1 — Extractor (`pipeline/extractor.py`)

Reads the input folder (flat, not recursive) and extracts text.

| Format | Library | Notes |
|--------|---------|-------|
| `.md`, `.txt` | `open()` | `encoding='utf-8', errors='replace'` |
| `.pdf` | `pdfplumber` | `page.extract_text()` for each page |
| `.docx` | `python-docx` | join all `paragraph.text` |

Files that throw extraction exceptions are skipped with a `rich` warning.

**Error handling:**
- Empty folder (no supported files found) → `rich` error panel + `sys.exit(1)`
- All files fail extraction → `rich` error panel + `sys.exit(1)`
- Individual file failure → warn and skip, continue

Token count per document: `tiktoken.get_encoding("cl100k_base").encode(content)`.

---

### Step 2 — Analyzer (`pipeline/analyzer.py`)

**Signature**: `analyze(docs: List[Document]) -> Tuple[AnalysisResult, str]`

Returns both `AnalysisResult` and `corpus_text` (a single string). `corpus_text` is what gets forwarded to the outliner.

**Normal path** (total tokens ≤ 80,000):
- `corpus_text` = all document contents joined with `\n---\n`
- Single LLM call → `AnalysisResult`

**Map-reduce path** (total tokens > 80,000):
- Map: one LLM call per document → `DocSummary.summary`
- Reduce: join summaries with `\n---\n` into `corpus_text` → single LLM call → `AnalysisResult`
- The same `corpus_text` (joined summaries) is returned and used by the outliner

**Token budget note**: 80,000-token threshold is chosen so that corpus_text + system prompt + analysis JSON comfortably fits within gpt-4o's 128k context window.

**Themes** (in analyzer system prompt):
- `dark-tech` — technical content, code, engineering, APIs, data
- `clean-corporate` — business reports, strategy, finance, presentations to executives
- `gradient-modern` — startups, creative, design, marketing, innovation

---

### Step 3 — Outliner (`pipeline/outliner.py`)

**Signature**: `generate(corpus_text: str, analysis: AnalysisResult) -> Outline`

LLM receives: system prompt with slide rules + `corpus_text` + `AnalysisResult` JSON.

**Slide rules** (in system prompt):
- First slide: always `type: title`
- Last slide: always `type: closing` — set `message` to main tagline, `submessage` to "Thank you" or equivalent
- `content` slides: 3-5 bullets each, concise
- `two-column`: comparisons, pros/cons, before/after
- `code`: only if source material contains actual code snippets
- Aim for `analysis.suggested_slide_count` slides; may vary ±3 based on content

---

### Step 4 — Renderer (`pipeline/renderer.py`)

**Signature**: `render(analysis: AnalysisResult, outline: Outline, output_path: str) -> None`

Assembles the final HTML using Jinja2 with `templates/base.html`.

**CDN dependencies (pinned versions):**
```html
<!-- Reveal.js -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.css">
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.js"></script>
<!-- Reveal.js highlight plugin (use bundled, NOT standalone hljs) -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/plugin/highlight/monokai.css">
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/plugin/highlight/highlight.js"></script>
<!-- GSAP -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
```

**Important**: use the Reveal.js bundled highlight plugin, NOT standalone hljs. Initialize via `Reveal.initialize({ plugins: [RevealHighlight] })`.

**Visual theme implementation**: No Reveal.js built-in theme is loaded. Instead, `base.html` has a `<style>` block where background, text, and accent colors are injected from `AnalysisResult` via Jinja2 variables:

```css
:root {
  --bg: {{ analysis.background_color }};
  --accent: {{ analysis.accent_color }};
  /* text color derived: dark bg → white text, light bg → dark text */
}
.reveal { background: var(--bg); }
.reveal h1, .reveal h2 { color: var(--accent); }
```

For `gradient-modern`, `background_color` is set to `"gradient"` (sentinel) and a CSS gradient is applied instead.

**GSAP animations**: `slidechanged` event handler:

```js
Reveal.on('slidechanged', function(event) {
  gsap.killTweensOf("*");
  const slide = event.currentSlide;
  const type = slide.dataset.type;
  // dispatch animation based on type...
});
```

| Slide type | Animation |
|---|---|
| `title` | Title: `y:60→0` + fade (0.7s). Subtitle: fade at 0.3s delay. Accent line: `scaleX:0→1`. |
| `content` | Title: `x:-40→0`. Bullets stagger in (`y:20→0` + fade, 0.1s stagger). |
| `two-column` | Left col: `x:-40→0`. Right col: `x:40→0`. Simultaneous. |
| `code` | Code block: clip-path `inset(100% 0 0 0) → inset(0% 0 0 0)` over 0.6s. |
| `closing` | Center: scale `0.8→1.0` + fade. Then gentle pulse (scale 1.0→1.03→1.0, yoyo, 2s repeat). |

**Reveal.js config:**
```js
Reveal.initialize({
  transition: 'fade',
  transitionSpeed: 'fast',
  controls: true,
  progress: true,
  slideNumber: true,
  keyboard: true,
  touch: true,
  hash: true,
  plugins: [RevealHighlight]
});
```

---

## CLI Interface

```python
# generate.py
import argparse

parser = argparse.ArgumentParser(description='Generate HTML presentation from documents')
parser.add_argument('folder', help='Path to folder with .md, .txt, .pdf, .docx files')
```

**Startup validation** (before pipeline runs):
- Load `.env` with `python-dotenv`
- Check `OPENAI_API_KEY` non-empty → if missing: `rich` error panel + `sys.exit(1)`

**OpenAI error handling** (in each pipeline step):
- `openai.RateLimitError` → print "Rate limit, retrying in 60s..." → `time.sleep(60)` → retry once → if fails again, exit
- `openai.APIError` → print error + `sys.exit(1)`
- Pydantic validation error on parsed response → print error + `sys.exit(1)`

---

## Configuration

`.env` file:
```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o    # optional, default: gpt-4o
```

---

## Dependencies (`requirements.txt`)

```
openai>=1.40.0
python-dotenv>=1.0.0
pdfplumber>=0.11.0
python-docx>=1.1.0
tiktoken>=0.7.0
rich>=13.0.0
jinja2>=3.1.0
pydantic>=2.0.0
```

---

## Verification Plan

1. **Basic run**: `test-folder/` with `intro.md`, `data.txt`, `summary.pdf` → `python generate.py ./test-folder/` → confirm `presentation.html` created
2. **Browser / navigation**: open `presentation.html` → Reveal.js loads, arrow keys navigate, slide counter shows
3. **GSAP**: advance and revisit slides → animations trigger each time, no stacking
4. **Code slide**: source with code snippet → verify `code` slide with syntax highlighting renders
5. **Themes**: technical content → expect `dark-tech`; business doc → expect `clean-corporate`
6. **Map-reduce**: 15+ large files totaling >80K tokens → output is coherent
7. **Missing key**: remove `OPENAI_API_KEY` → clear error + exit code 1
8. **Empty folder**: point to empty folder → clear error + exit code 1
9. **No supported files**: folder with only `.jpg`/`.mp3` → "no supported file types found" error + exit 1
10. **Overwrite**: run twice → second run overwrites silently
11. **Closing slide**: verify `message` and `submessage` both render, pulse animation runs
