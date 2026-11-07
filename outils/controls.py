"""Contrôles après rendu : avertissements de Quarto et images manquantes.

Repère notamment :
  - les renvois vers des équations ou figures masquées dans une version
    (« Unable to resolve crossref @eq-… ») : la règle d'or des marques est enfreinte ;
  - les références bibliographiques introuvables (« Citeproc: citation … not found ») ;
  - les images référencées mais absentes du rendu HTML.
"""

import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ANSI = re.compile(r"\x1b\[[0-9;]*m")
WARNING = re.compile(r"WARN")
# Avertissements sans rapport avec le contenu du cours
IGNORED = ("IPKernelApp",)


def check_logs(paths: list[Path]) -> list[str]:
    problems = []
    for path in paths:
        for number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            clean = ANSI.sub("", line).strip()
            if WARNING.search(clean) and not any(i in clean for i in IGNORED):
                problems.append(f"{path.name}:{number} : {clean}")
    return problems


class _ImageSources(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.sources: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            for name, value in attrs:
                if name in ("src", "data-src") and value:
                    self.sources.append(value)


def check_images(output: Path) -> list[str]:
    problems = []
    for page in sorted(output.rglob("*.html")):
        if "site_libs" in page.parts or any(p.endswith("_files") for p in page.parts):
            continue
        parser = _ImageSources()
        parser.feed(page.read_text(encoding="utf-8", errors="replace"))
        for src in parser.sources:
            url = urlparse(src)
            if url.scheme or src.startswith("//"):
                continue  # data:, http(s):, etc.
            target = (page.parent / unquote(url.path)).resolve()
            if not target.exists():
                problems.append(f"{page.relative_to(output)} : image introuvable {src}")
    return problems
