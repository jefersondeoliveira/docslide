from pathlib import Path

import jinja2
from rich.console import Console

from pipeline.models import AnalysisResult, Outline

console = Console()


def render(analysis: AnalysisResult, outline: Outline, output_path: str) -> None:
    console.print("[bold]Rendering presentation...[/bold]")

    templates_dir = Path(__file__).parent.parent / "templates"
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(templates_dir)))
    template = env.get_template("base.html")

    rendered = template.render(analysis=analysis, outline=outline)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered)
