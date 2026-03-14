import argparse
import os
import sys

import openai
from dotenv import load_dotenv
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from pipeline import extractor, analyzer, outliner, renderer

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate HTML presentation from documents")
    parser.add_argument("folder", help="Path to folder with .md, .txt, .pdf, .docx files")
    args = parser.parse_args()

    load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        console.print(Panel("[bold red]OPENAI_API_KEY is not set or empty.[/bold red]", title="Error"))
        sys.exit(1)

    folder_path = args.folder
    output_path = "presentation.html"

    try:
        console.print("[bold cyan]Step 1/4:[/bold cyan] Extracting documents...")
        docs = extractor.extract(folder_path)

        console.print("[bold cyan]Step 2/4:[/bold cyan] Analyzing content...")
        analysis, corpus_text = analyzer.analyze(docs)

        console.print("[bold cyan]Step 3/4:[/bold cyan] Generating outline...")
        outline = outliner.generate(corpus_text, analysis)

        console.print("[bold cyan]Step 4/4:[/bold cyan] Rendering HTML...")
        renderer.render(analysis, outline, output_path)

        console.print(
            f"[bold green]✓ Done![/bold green] Presentation saved to [underline]{output_path}[/underline]"
        )

    except openai.RateLimitError:
        console.print(Panel("Rate limit exceeded after retries", title="Error"))
        sys.exit(1)
    except openai.APIError as e:
        console.print(Panel(str(e), title="Error"))
        sys.exit(1)
    except ValidationError as e:
        console.print(Panel(f"Unexpected LLM response format\n{e}", title="Error"))
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)


if __name__ == "__main__":
    main()
