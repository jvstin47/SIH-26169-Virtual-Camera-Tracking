#!/usr/bin/env bash
# ==============================================================================
# Phoenix-X: Apple Silicon (M1/M2/M3/M4/M5) Setup & MPS Acceleration Script
# Problem Statement ID: SIH 26169 (ISRO / SAC)
# ==============================================================================

set -e

echo "======================================================================"
echo "  PHOENIX-X: APPLE SILICON (M-SERIES / M5) SETUP & VERIFICATION"
echo "======================================================================"

# 1. Architecture Verification
ARCH=$(uname -m)
echo "[*] Detected Hardware Architecture: ${ARCH}"
if [ "${ARCH}" != "arm64" ]; then
    echo "[!] Warning: You are not running on native ARM64 Apple Silicon."
    echo "    To get the most out of your hardware, ensure you run in ARM64 mode."
else
    echo "[+] Confirmed native ARM64 Apple Silicon platform."
fi

# 2. Check Python Environment
PYTHON_BIN=""
if command -v python3 &> /dev/null; then
    PYTHON_BIN="python3"
elif command -v python &> /dev/null; then
    PYTHON_BIN="python"
else
    echo "[-] Error: Python is not installed. Please install Miniforge or use Homebrew."
    exit 1
fi

PY_ARCH=$(${PYTHON_BIN} -c "import platform; print(platform.machine())")
echo "[*] Python interpreter architecture: ${PY_ARCH}"

# 3. Create or reuse virtual environment
VENV_DIR=".venv"
if [ ! -d "${VENV_DIR}" ]; then
    echo "[*] Creating Apple Silicon native virtual environment in ${VENV_DIR}..."
    ${PYTHON_BIN} -m venv ${VENV_DIR}
fi

source "${VENV_DIR}/bin/activate"
echo "[+] Virtual environment activated: $(which python)"

# 4. Install ARM64-optimized PyTorch and dependencies
echo "[*] Installing / Verifying PyTorch with Apple Silicon MPS support..."
pip install --upgrade pip
pip install torch torchvision numpy opencv-python-headless pandas matplotlib

# 5. Verify Apple GPU Acceleration (MPS)
echo ""
echo "[*] Running Hardware Acceleration Verification Test..."
python -c '
import torch
import platform

print("-" * 50)
print(f"Platform: {platform.platform()}")
print(f"PyTorch Version: {torch.__version__}")
print(f"MPS Built: {torch.backends.mps.is_built()}")
print(f"MPS Available: {torch.backends.mps.is_available()}")

if torch.backends.mps.is_available():
    device = torch.device("mps")
    print("M5 GPU Acceleration Active!")
    
    # Quick tensor allocation and matrix multiplication test
    x = torch.randn(1000, 1000, device=device)
    y = torch.matmul(x, x)
    torch.mps.synchronize()
    print("MPS Compute Tensor Benchmark: PASSED (1000x1000 MatMul OK)")
else:
    print("[-] MPS Acceleration is not available. Falling back to CPU.")
print("-" * 50)
'

echo ""
echo "[+] Setup completed successfully!"
echo "    To activate this environment in future terminals, run:"
echo "    source .venv/bin/activate"
echo "    To train BeaconNet-Nano on Apple Silicon GPU:"
echo "    python scripts/train_beacon_net.py --device mps"
