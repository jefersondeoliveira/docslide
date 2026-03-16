# Presentation Generator

Transforms a folder of documents into a polished, animated HTML presentation using AI. Drop in your Markdown, text, PDF, or DOCX files — get a ready-to-present slide deck.

## How It Works

```
Input Folder → Extract Text → AI Analysis → Slide Outline → HTML Presentation
```

1. **Extract** — Reads all supported files from the input folder
2. **Analyze** — OpenAI analyzes the corpus to determine title, theme, and colors
3. **Outline** — AI generates a structured slide-by-slide outline
4. **Render** — Jinja2 renders a Reveal.js + GSAP powered HTML file

For large corpora (>80K tokens), a map-reduce strategy summarizes individual documents before analysis.

## Features

- **Multi-format input**: `.md`, `.txt`, `.pdf`, `.docx`
- **AI-driven layout**: 5 slide types — title, bullets, two-column, code, closing
- **Auto theming**: AI picks from 3 visual presets (`dark-tech`, `clean-corporate`, `gradient-modern`)
- **Smooth animations**: GSAP animations per slide type (staggered bullets, clip-path reveals, etc.)
- **Syntax highlighting**: Code slides with language detection
- **Standalone output**: Single `.html` file, no build step required

## Setup

**Requirements:** Python 3.8+, OpenAI API key

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your OPENAI_API_KEY to .env
```

## Usage

```bash
python generate.py ./path/to/documents/
```

Output is saved to `presentations/<slug>_<YYYY-MM-DD>.html`. Open in any modern browser.

## Configuration

`.env` variables:

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes | — | Your OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4o` | Model to use (`gpt-4o-mini` for faster/cheaper) |

## Tech Stack

| Layer | Technology |
|---|---|
| AI | OpenAI API (structured output via Pydantic) |
| Document parsing | pdfplumber, python-docx |
| Token counting | tiktoken |
| Templating | Jinja2 |
| Presentation | Reveal.js 5.1 |
| Animations | GSAP 3.12 |
| Console UI | Rich |

## Project Structure

```
presentation-generate/
├── generate.py          # CLI entry point and pipeline orchestrator
├── pipeline/
│   ├── models.py        # Pydantic data models
│   ├── extractor.py     # Step 1: Extract text from documents
│   ├── analyzer.py      # Step 2: AI corpus analysis and theme detection
│   ├── outliner.py      # Step 3: AI slide outline generation
│   └── renderer.py      # Step 4: HTML rendering
├── templates/
│   └── base.html        # Reveal.js + GSAP Jinja2 template
├── tests/
│   └── test_models.py   # Pydantic model validation tests
└── presentations/       # Generated output (auto-created)
```

## Running Tests

```bash
pytest tests/
```
