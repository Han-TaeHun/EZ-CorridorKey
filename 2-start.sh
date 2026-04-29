#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    echo "[ERROR] .venv not found. Run 1-install.sh first!"
    exit 1
fi

# Cache torch.compile Triton kernels locally — prevents 2~5 min recompile each run
export TORCHINDUCTOR_CACHE_DIR="${TORCHINDUCTOR_CACHE_DIR:-$HOME/.cache/EZ-CorridorKey/torch_cache}"
# Cache Python bytecode locally — speeds up import on subsequent runs
export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-$HOME/.cache/EZ-CorridorKey/pycache}"

source .venv/bin/activate
python main.py "$@"
