#!/usr/bin/env python3
"""
Phoenix-X: BeaconNet-Nano Training & Benchmark Pipeline
Optimized for Apple Silicon (M1/M2/M3/M4/M5) via MPS & Embedded Edge (CUDA / CPU)
Problem Statement ID: SIH 26169 (ISRO / SAC)

Trains the ultra-lightweight BeaconNet-Nano on synthetic optical beacon datasets
and exports the trained graph to ONNX for edge runtime.
"""

import os
import sys
import time
import argparse
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.vision.beacon_onnx_model import MODEL_CONFIG, BeaconNetNanoNumPy

def get_optimal_device(force_cpu=False):
    """Detects and returns optimal PyTorch device (MPS for Apple Silicon, CUDA, or CPU)."""
    try:
        import torch
    except ImportError:
        return "numpy"

    if force_cpu:
        return torch.device("cpu")
    
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    else:
        return torch.device("cpu")

def generate_gaussian_target(height, width, center_u, center_v, sigma=2.5):
    """Generates ground truth 2D Gaussian heatmap centered at beacon spot."""
    y = np.arange(0, height, dtype=np.float32)
    x = np.arange(0, width, dtype=np.float32)
    xx, yy = np.meshgrid(x, y)
    dist_sq = (xx - center_u)**2 + (yy - center_v)**2
    heatmap = np.exp(-dist_sq / (2.0 * sigma**2))
    return heatmap

def load_or_create_dataset(num_samples=120, height=240, width=320):
    """Loads dataset from data/synthetic_dataset or synthesizes in-memory batches."""
    csv_path = "data/synthetic_dataset/ground_truth.csv"
    img_dir = "data/synthetic_dataset/images"
    
    inputs = []
    targets = []
    
    if os.path.exists(csv_path) and os.path.exists(img_dir):
        import cv2
        import pandas as pd
        df = pd.read_csv(csv_path)
        print(f"[*] Loading {len(df)} frames from synthetic dataset...")
        for _, row in df.iterrows():
            img_path = os.path.join("data/synthetic_dataset", row['file_path'])
            if os.path.exists(img_path):
                img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    # Resize to network input shape (240, 320)
                    h_orig, w_orig = img.shape
                    scale_x = width / w_orig
                    scale_y = height / h_orig
                    
                    img_resized = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)
                    norm_img = img_resized.astype(np.float32) / 255.0
                    
                    u_scaled = row['beacon_u_px'] * scale_x
                    v_scaled = row['beacon_v_px'] * scale_y
                    
                    target_heatmap = generate_gaussian_target(height, width, u_scaled, v_scaled, sigma=2.0)
                    
                    inputs.append(norm_img[np.newaxis, :, :])
                    targets.append(target_heatmap[np.newaxis, :, :])

    # If dataset has fewer than target samples, augment with on-the-fly synthetic samples
    current_count = len(inputs)
    if current_count < num_samples:
        needed = num_samples - current_count
        print(f"[*] Synthesizing {needed} additional synthetic training frames...")
        rng = np.random.RandomState(42)
        for _ in range(needed):
            bg = rng.normal(loc=0.08, scale=0.03, size=(height, width)).astype(np.float32)
            bg = np.clip(bg, 0.0, 1.0)
            
            # Random beacon position
            u = rng.uniform(width * 0.15, width * 0.85)
            v = rng.uniform(height * 0.15, height * 0.85)
            
            # Gaussian spot
            spot = generate_gaussian_target(height, width, u, v, sigma=1.8) * rng.uniform(0.7, 1.0)
            frame = np.clip(bg + spot, 0.0, 1.0)
            
            target_heatmap = generate_gaussian_target(height, width, u, v, sigma=2.0)
            inputs.append(frame[np.newaxis, :, :])
            targets.append(target_heatmap[np.newaxis, :, :])

    return np.array(inputs, dtype=np.float32), np.array(targets, dtype=np.float32)

def train_pipeline(epochs=10, batch_size=8, lr=0.003, force_cpu=False):
    print("=" * 70)
    print("  PHOENIX-X: BEACONNET-NANO ACCELERATED TRAINING & BENCHMARK")
    print("=" * 70)

    try:
        import torch
        import torch.nn as nn
        import torch.optim as optim
    except ImportError:
        print("[!] PyTorch is not installed in the active environment.")
        print("    Run: bash scripts/setup_apple_silicon_env.sh")
        print("    to install native PyTorch with Apple Silicon GPU acceleration.")
        return

    device = get_optimal_device(force_cpu=force_cpu)
    print(f"[*] Hardware Acceleration Device: {device}")
    if str(device) == "mps":
        print("    >>> M5 / Apple Silicon GPU Acceleration Active via Metal Performance Shaders (MPS)! <<<")
    elif str(device) == "cuda":
        print(f"    >>> NVIDIA CUDA GPU Active: {torch.cuda.get_device_name(0)} <<<")
    else:
        print("    >>> Running on CPU with SIMD acceleration <<<")

    from src.vision.beacon_onnx_model import BeaconNetNano
    model = BeaconNetNano().to(device)
    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"[*] Model: BeaconNet-Nano ({total_params:,} parameters | Footprint: {total_params*4/1024:.2f} KB)")

    # Load dataset
    x_data, y_data = load_or_create_dataset(num_samples=96)
    split_idx = int(0.8 * len(x_data))
    
    x_train, y_train = x_data[:split_idx], y_data[:split_idx]
    x_val, y_val = x_data[split_idx:], y_data[split_idx:]
    print(f"[*] Dataset split: {len(x_train)} train samples, {len(x_val)} validation samples")

    x_train_t = torch.from_numpy(x_train).to(device)
    y_train_t = torch.from_numpy(y_train).to(device)
    x_val_t = torch.from_numpy(x_val).to(device)
    y_val_t = torch.from_numpy(y_val).to(device)

    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    print(f"\n[*] Commencing training loop ({epochs} epochs, batch size {batch_size})...")
    start_time = time.time()
    
    for epoch in range(1, epochs + 1):
        model.train()
        permutation = torch.randperm(x_train_t.size(0))
        epoch_loss = 0.0
        num_batches = 0

        for i in range(0, x_train_t.size(0), batch_size):
            indices = permutation[i:i + batch_size]
            batch_x, batch_y = x_train_t[indices], y_train_t[indices]

            optimizer.zero_grad()
            pred_heatmap = model(batch_x)
            loss = criterion(pred_heatmap, batch_y)
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()
            num_batches += 1

        avg_train_loss = epoch_loss / max(1, num_batches)

        # Validation
        model.eval()
        with torch.no_grad():
            val_preds = model(x_val_t)
            val_loss = criterion(val_preds, y_val_t).item()

        if epoch % 2 == 0 or epoch == epochs:
            print(f"    Epoch [{epoch:02d}/{epochs:02d}] | Train Loss: {avg_train_loss:.6f} | Val Loss: {val_loss:.6f}")

    total_time = time.time() - start_time
    fps = (len(x_train) * epochs) / max(0.001, total_time)
    print(f"\n[+] Training completed in {total_time:.2f}s ({fps:.1f} frames/sec)")

    # Model save & ONNX export
    os.makedirs("models", exist_ok=True)
    pt_save_path = "models/beacon_net_nano_mps.pt"
    torch.save(model.state_dict(), pt_save_path)
    print(f"[+] Saved PyTorch weights to: {pt_save_path}")

    onnx_path = "models/beacon_saliency_net.onnx"
    dummy_input = torch.randn(1, 1, 240, 320, device=device)
    model.eval()
    
    # Export to ONNX on CPU for maximum cross-platform compatibility
    model_cpu = model.to("cpu")
    dummy_cpu = dummy_input.to("cpu")
    torch.onnx.export(
        model_cpu,
        dummy_cpu,
        onnx_path,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=['input_fpa_tensor'],
        output_names=['saliency_heatmap'],
        dynamic_axes={'input_fpa_tensor': {0: 'batch_size'}, 'saliency_heatmap': {0: 'batch_size'}}
    )
    print(f"[+] Successfully exported optimized ONNX model to: {onnx_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phoenix-X BeaconNet-Nano Training")
    parser.add_argument("--epochs", type=int, default=10, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size")
    parser.add_argument("--force-cpu", action="store_true", help="Force CPU training")
    args = parser.parse_args()

    train_pipeline(epochs=args.epochs, batch_size=args.batch_size, force_cpu=args.force_cpu)
