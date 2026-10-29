"""Sphinx configuration for the staged sources prepared by build_docs.py."""
import os
from pathlib import Path

project = "GenIE"
author = "GenIE contributors"
extensions = ["myst_parser", "sphinx.ext.autodoc", "sphinx.ext.mathjax", "sphinx_copybutton"]
source_suffix = {".md": "markdown", ".rst": "restructuredtext"}
root_doc = "index"
exclude_patterns = ["docs/index.md"]
html_theme = "furo"
html_title = "GenIE Documentation"
_static = Path(__file__).resolve().parent / "_static"
html_logo = str(_static / "genie-logo.png")
html_favicon = str(_static / "favicon.ico")
html_static_path = [str(_static)]
html_baseurl = "https://tum-ei-eda.github.io/GenIE/"
html_theme_options = {
    "source_repository": "https://github.com/tum-ei-eda/GenIE/",
    "source_branch": os.environ.get("GENIE_DOCS_REF", "main"),
    "source_directory": "",
}
myst_heading_anchors = 6
myst_enable_extensions = ["colon_fence", "dollarmath", "tasklist"]
autodoc_typehints = "none"
autodoc_member_order = "bysource"
copybutton_prompt_text = r"\$ "
copybutton_prompt_is_regexp = True
