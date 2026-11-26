#!/bin/bash

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
exec uv run python -m scripts.dev_install "$@"
