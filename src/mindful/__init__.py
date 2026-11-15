"""Mindful's Anki entry point and standalone command."""

import sys

if (aqt := sys.modules.get("aqt")) is not None and getattr(aqt, "mw", None) is not None:
    from .bootstrap import initialize

    initialize()


def main() -> None:
    """Run the standalone command."""
    sys.stdout.write("Hello from mindful!\n")
