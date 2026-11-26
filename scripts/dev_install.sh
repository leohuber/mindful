#!/bin/bash

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
exec uv run python scripts/dev_install.py "$@"
