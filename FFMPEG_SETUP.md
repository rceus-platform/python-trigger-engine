# FFmpeg Cross-Platform Setup

This project is configured to use ffmpeg binaries for both Windows and Linux platforms.

## Current Setup

### Windows

- Binary location: `tools/windows/ffmpeg.exe`
- Should be placed in the Windows tools directory

### Linux

- Binary location: `tools/linux/ffmpeg`
- Extracted from the `.tar.xz` archive

## How It Works

The `core/services/audio_extractor.py` automatically detects your platform using Python's `platform.system()` and uses the appropriate ffmpeg binary.

## Setup Instructions

### On Linux

1. **Place the archive**: Put `ffmpeg-master-latest-linux64-gpl.tar.xz` in the project root directory

2. **Run the setup script**:

   ```bash
   python setup_ffmpeg.py
   ```

   This will:

   - Extract the tar.xz archive to tools/linux/
   - Copy the ffmpeg binary to tools/linux/ffmpeg
   - Set executable permissions on the binary
   - Verify the installation

3. **Verify setup**:
   ```bash
   # Check if ffmpeg is accessible
   tools/linux/ffmpeg -version
   ```

### On Windows

1. **Extract ffmpeg**: Download the Windows ffmpeg build
2. **Place the binary**: Copy `ffmpeg.exe` to `tools/windows/`
3. **Verify**: The app will automatically use it

## How to Get FFmpeg Binaries

### Windows

- Download from: https://ffmpeg.org/download.html
- Or use: https://github.com/BtbN/FFmpeg-Builds

### Linux

- Download from: https://ffmpeg.org/download.html
- The version used here: `ffmpeg-master-latest-linux64-gpl.tar.xz`
- Alternatively, install via package manager: `sudo apt-get install ffmpeg` (Debian/Ubuntu)

## Directory Structure

```
tools/
├── windows/
│   └── ffmpeg.exe          (Windows binary)
└── linux/
    └── ffmpeg              (Linux binary)
```

## Troubleshooting

### Error: "ffmpeg binary not found"

- Verify the binary exists in the correct location for your platform:
  - Windows: `tools/windows/ffmpeg.exe`
  - Linux: `tools/linux/ffmpeg`
- Run `python setup_ffmpeg.py` to check the setup

### Permission Denied (Linux)

- The setup script automatically sets executable permissions
- If needed, manually run: `chmod +x tools/linux/ffmpeg`

### Platform Detection

The script shows which platform is detected. Check the error message for the actual path it's looking for.
