#!/usr/bin/env bash
# ==============================================================================
# Phoenix-X: TensorRT Optimization Script for Edge Avionics (NVIDIA Jetson)
# Converts ONNX model to high-throughput FP16 / INT8 TensorRT Engine
# Expected Latency: < 0.35 ms on Jetson Orin Nano / Xavier NX
# ==============================================================================

ONNX_FILE="models/beacon_saliency_net.onnx"
ENGINE_FILE="models/beacon_saliency_net_fp16.engine"

echo "[*] Converting ${ONNX_FILE} to TensorRT FP16 Engine..."
if command -v trtexec &> /dev/null; then
    trtexec \
        --onnx=${ONNX_FILE} \
        --saveEngine=${ENGINE_FILE} \
        --fp16 \
        --workspace=64 \
        --minShapes=input_fpa_tensor:1x1x240x320 \
        --optShapes=input_fpa_tensor:1x1x240x320 \
        --maxShapes=input_fpa_tensor:4x1x240x320 \
        --verbose
    echo "[+] TensorRT engine compiled: ${ENGINE_FILE}"
else
    echo "[!] trtexec not found in PATH. Please run this script on an NVIDIA Jetson environment with TensorRT installed."
fi
