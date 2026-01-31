# scripts/fix_readme.py
# Fixes README.md by replacing the "Run locally (from zero)" section
# with a canonical, valid Markdown block.
#
# IMPORTANT: uses repo root derived from this file's location (works regardless of CWD).

from pathlib import Path

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[1]
README_PATH = REPO_ROOT / "README.md"

START_MARK = "## Run locally (from zero)"
END_MARK = "## Dataset (canonical)"

CANON_BLOCK = (
    "## Run locally (from zero)\n\n"
    "This project is fully reproducible from a clean environment.\n\n"
    "### Requirements\n"
    "- Python **3.11+**\n"
    "- Git\n\n"
    "### Setup\n"
    "```bash\n"
    "git clone https://github.com/<your-username>/<repo-name>.git\n"
    "cd <repo-name>\n\n"
    "python -m venv .venv\n"
    "source .venv/bin/activate  # Windows: .\\.venv\\Scripts\\activate\n\n"
    "pip install -r requirements.txt\n"
    "```\n\n"
    "### Run\n"
    "```bash\n"
    "streamlit run app.py\n"
    "```\n\n"
    "The app expects the canonical dataset at:\n\n"
    "```text\n"
    "data/nyc311_noise_brooklyn_2023_with_weather_canonical.csv\n"
    "```\n\n"
    "If the file is missing or invalid, the app will fail fast with a clear error message.\n"
    "This is intentional and part of the data contract.\n\n"
    "### Notes on reproducibility\n"
    "- Only **CSV** is used as a data artifact (no pickle/parquet).\n"
    "- Time alignment and merge validity are documented in `checks/README.md`.\n"
    "- No ML models or training steps are required.\n\n"
)

def main() -> None:
    if not README_PATH.exists():
        raise FileNotFoundError(f"README.md not found at: {README_PATH}")

    text = README_PATH.read_text(encoding="utf-8")

    start_i = text.find(START_MARK)
    if start_i == -1:
        raise ValueError(f"Start marker not found: {START_MARK!r}")

    end_i = text.find(END_MARK, start_i)
    if end_i == -1:
        raise ValueError(f"End marker not found after start: {END_MARK!r}")

    before = text[:start_i].rstrip() + "\n\n"
    after = "\n\n" + text[end_i:].lstrip()

    fixed = before + CANON_BLOCK + after

    if fixed.count("```") % 2 != 0:
        raise ValueError("Unbalanced markdown code fences after fix")

    README_PATH.write_text(fixed, encoding="utf-8")

    print("OK: README.md fixed successfully.")
    print(f"README_PATH: {README_PATH}")

if __name__ == "__main__":
    main()
