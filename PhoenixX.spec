# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

# Determine platform icon
if sys.platform == 'darwin':
    app_icon = 'assets/PhoenixX.icns' if os.path.exists('assets/PhoenixX.icns') else None
else:
    app_icon = 'assets/PhoenixX.ico' if os.path.exists('assets/PhoenixX.ico') else None

added_datas = [
    ('web_demo', 'web_demo'),
    ('distributed_demo', 'distributed_demo'),
    ('src', 'src'),
    ('assets', 'assets'),
    ('models', 'models'),  # AI model weights (ONNX / PTH / MLX)
]

a = Analysis(
    ['launch_unified_app.py'],
    pathex=['.'],
    binaries=[],
    datas=added_datas,
    hiddenimports=[
        'cv2',
        'numpy',
        # Core
        'src.core.coordinates',
        'src.core.network',
        # Optics & Atmosphere
        'src.optics.atmosphere_and_noise',
        # Vision pipeline
        'src.vision.tracker',
        'src.vision.deep_saliency_net',
        'src.vision.beacon_onnx_model',
        'src.vision.beacon_mlx_model',
        # Control
        'src.control.gimbal_controller',
        # Camera
        'src.camera.ptz_camera',
        # Simulation
        'src.simulation.trajectories',
        'src.simulation.orbital_propagator',
        # Benchmarking & Experiments
        'src.benchmarking.mp4_bypass',
        'src.experiments.scientific_benchmark',
        # Distributed demo nodes
        'distributed_demo.ground_tracker',
        'distributed_demo.atmospheric_channel',
        'distributed_demo.target_satellite',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'torch', 'torchvision', 'torchaudio',
        'scipy', 'IPython', 'pandas', 'streamlit',
        'tensorflow', 'keras', 'sklearn', 'onnxruntime',
        'PIL', 'Pillow', 'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Phoenix-X',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=app_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Phoenix-X',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='Phoenix-X.app',
        icon='assets/PhoenixX.icns',
        bundle_identifier='com.phoenixx.fsoc.tracker',
        info_plist={
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '11.0',
            'NSHumanReadableCopyright': 'Phoenix-X Team \u00a9 2026 (SIH 26169)',
            # macOS privacy strings (required for OpenCV camera/display access)
            'NSCameraUsageDescription': 'Phoenix-X requires camera access for live optical beacon tracking via the virtual PTZ sensor pipeline.',
            'NSMicrophoneUsageDescription': 'Not used by Phoenix-X.',
        },
    )
