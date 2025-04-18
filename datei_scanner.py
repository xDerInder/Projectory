import os
import re
from pathlib import Path

DEV_EXTENSIONS = [
    ".py", ".js", ".ts", ".rs", ".cpp", ".c", ".cs", ".java", ".go",
    ".html", ".css", ".md", ".json", ".yml", ".toml", ".xml"
]

IGNORED_FOLDERS = [
    "node_modules", ".venv", "__pycache__", ".git", ".idea", ".vscode",
    ".gradle", ".settings", "__init__.py", ".DS_Store"
]


def looks_like_project_by_files(path):
    try:
        for file in os.listdir(path):
            full_path = Path(path) / file
            if full_path.is_file() and full_path.suffix.lower() in DEV_EXTENSIONS:
                return True
    except:
        pass
    return False


def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]


def scan_projects_in_path(base_path):
    found_projects = set()
    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_FOLDERS]
        path = Path(root)

        if looks_like_project_by_files(root):
            found_projects.add(str(path))

    sorted_projects = sorted(list(found_projects),
                             key=lambda p: natural_sort_key(Path(p).name))
    return sorted_projects
