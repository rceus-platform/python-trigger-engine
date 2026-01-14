"""
Setup script to extract and organize ffmpeg binaries for cross-platform support.
Handles both Windows and Linux ffmpeg binaries.
"""

import os
import platform
import shutil
import stat
import tarfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LINUX_TOOLS_DIR = BASE_DIR / "tools" / "linux"


def setup_linux_ffmpeg():
    """
    Extract Linux ffmpeg binary from tar.xz file and set executable permissions.
    """
    linux_tar = BASE_DIR / "ffmpeg-master-latest-linux64-gpl.tar.xz"

    if not linux_tar.exists():
        print(f"[ERROR] Linux ffmpeg archive not found: {linux_tar}")
        print(
            "Please download ffmpeg-master-latest-linux64-gpl.tar.xz and place it in the project root"
        )
        return False

    try:
        print(f"[INFO] Extracting {linux_tar.name}...")

        # Create tools/linux directory if it doesn't exist
        LINUX_TOOLS_DIR.mkdir(parents=True, exist_ok=True)

        # Extract tar.xz to temporary location first
        with tarfile.open(linux_tar, "r:xz") as tar:
            tar.extractall(path=LINUX_TOOLS_DIR)

        # Find the ffmpeg binary in the extracted folder
        # Usually it's in: ffmpeg-master-latest-linux64-gpl/bin/ffmpeg
        extracted_dir = LINUX_TOOLS_DIR / "ffmpeg-master-latest-linux64-gpl"
        ffmpeg_src = extracted_dir / "bin" / "ffmpeg"
        ffmpeg_dest = LINUX_TOOLS_DIR / "ffmpeg"

        if ffmpeg_src.exists():
            # Copy to tools/linux/ffmpeg
            shutil.copy2(ffmpeg_src, ffmpeg_dest)
            # Make it executable
            os.chmod(ffmpeg_dest, os.stat(ffmpeg_dest).st_mode | stat.S_IEXEC)
            print(f"[SUCCESS] Linux ffmpeg extracted and made executable")
            print(f"   Location: {ffmpeg_dest}")
            return True
        else:
            print(
                f"[ERROR] ffmpeg binary not found in extracted archive at {ffmpeg_src}"
            )
            return False

    except Exception as e:
        print(f"[ERROR] Error extracting Linux ffmpeg: {e}")
        return False


def verify_ffmpeg_setup():
    """
    Verify that ffmpeg binaries are available for the current platform.
    """
    system = platform.system()

    if system == "Windows":
        ffmpeg_path = BASE_DIR / "tools" / "windows" / "ffmpeg.exe"
    elif system == "Linux":
        ffmpeg_path = BASE_DIR / "tools" / "linux" / "ffmpeg"
    else:
        print(f"[WARNING] Unsupported platform: {system}")
        return False

    if ffmpeg_path.exists():
        print(f"[SUCCESS] ffmpeg found for {system}: {ffmpeg_path}")
        return True
    else:
        print(f"[ERROR] ffmpeg not found for {system}: {ffmpeg_path}")
        return False


if __name__ == "__main__":
    print("[INFO] Setting up ffmpeg for cross-platform support...\n")

    current_platform = platform.system()
    print(f"Current platform: {current_platform}\n")

    if current_platform == "Linux":
        print("[INFO] Setting up Linux ffmpeg...")
        if setup_linux_ffmpeg():
            print("\n[SUCCESS] Setup complete!\n")
            verify_ffmpeg_setup()
        else:
            print("\n[ERROR] Setup failed\n")
    else:
        print("[INFO] Windows ffmpeg should already be in tools/windows/")
        print(
            "[INFO] For Linux, run this script on a Linux machine or follow manual setup.\n"
        )

    print("\n" + "=" * 50)
    print("[INFO] Verifying ffmpeg setup:")
    verify_ffmpeg_setup()
