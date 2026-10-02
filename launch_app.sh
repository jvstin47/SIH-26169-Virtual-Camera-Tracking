#!/usr/bin/env bash
# ==============================================================================
# Phoenix-X: Single-Command All-in-One Launcher
# Problem Statement ID: SIH 26169 (ISRO / SAC)
# ==============================================================================

echo "======================================================================"
echo "  STARTING PHOENIX-X UNIFIED MISSION CONTROL APPLICATION"
echo "======================================================================"

# Activate virtual environment if present
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Launch Master Unified Orchestrator
python3 launch_unified_app.py "$@"
