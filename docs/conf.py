from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

project = "Yardmaster"
author = "Flatcar Team"

try:
    import yardmaster

    release = yardmaster.__version__
except ImportError:
    release = "0.0.0"

version = release

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
root_doc = "index"

html_theme = "alabaster"
html_static_path = ["_static"]
