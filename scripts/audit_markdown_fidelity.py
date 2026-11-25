"""Report Markdown fidelity for a copied Anki collection without modifying it."""

import argparse
import sqlite3
import sys
from collections import Counter, defaultdict
from importlib import import_module
from pathlib import Path

sys.dont_write_bytecode = True

field_presentation = import_module("mindful.core.markdown_fields").field_presentation


def _copied_collection(value: str) -> Path:
    path = Path(value).expanduser().resolve(strict=True)
    if path.name == "collection.anki2" or (path.parent / "collection.media").exists():
        message = "Pass a renamed copy outside the Anki profile, not a live collection."
        raise ValueError(message)
    if Path(f"{path}-wal").exists():
        message = "The copy has a WAL file; create a consistent standalone copy first."
        raise ValueError(message)
    return path


def audit(path: Path) -> None:
    """Print per-note-type field counts and fallback reasons from an immutable copy."""
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    reasons: dict[str, Counter[str]] = defaultdict(Counter)
    with sqlite3.connect(f"{path.as_uri()}?mode=ro&immutable=1", uri=True) as db:
        rows = db.execute(
            "SELECT COALESCE(notetypes.name, '(unknown note type)'), notes.flds FROM notes LEFT JOIN notetypes ON notes.mid = notetypes.id"
        )
        for name, fields in rows:
            for html in fields.split("\x1f"):
                result = field_presentation(html)
                counts[name][result.mode] += 1
                if result.reason:
                    reasons[name][result.reason] += 1
    for name in sorted(counts, key=str.casefold):
        markdown_count = counts[name]["markdown"]
        html_count = counts[name]["html"]
        sys.stdout.write(f"{name}: {markdown_count} Markdown, {html_count} HTML ({markdown_count + html_count} fields)\n")
        for reason, count in reasons[name].most_common():
            sys.stdout.write(f"  {count}: {reason}\n")


def main() -> None:
    """Run the read-only collection audit."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("collection", help="Path to a renamed, standalone copy of collection.anki2")
    args = parser.parse_args()
    try:
        path = _copied_collection(args.collection)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    audit(path)


if __name__ == "__main__":
    main()
