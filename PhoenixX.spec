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
]

a = Analysis(
    ['launch_unified_app.py'],
    pathex=['.'],
    binaries=[],
    datas=added_datas,
    hiddenimports=[
        'cv2',
        'numpy',
        'src.core.coordinates',
        'src.core.network',
        'src.optics.atmosphere_and_noise',
        'src.vision.tracker',
        'src.control.gimbal_controller',
        'src.camera.ptz_camera',
        'distributed_demo.ground_tracker',
        'distributed_demo.atmospheric_channel',
        'distributed_demo.target_satellite',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'torch', 'scipy', 'IPython', 'pandas', 'streamlit'],
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
            'NSHumanReadableCopyright': 'Phoenix-X Team © 2026 (SIH 26169)',
        },
    )
