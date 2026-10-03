import os
import platform
import shutil
import sys
from pathlib import Path


def main():
    p = sys.platform
    a = platform.machine()
    os_name = 'darwin' if p == 'darwin' else 'win32' if p == 'win32' else 'linux'
    arch = 'arm64' if a == 'arm64' else 'x64'
    plat = f"{os_name}-{arch}"
    
    binary_name = "ktui.exe" if os_name == "win32" else "ktui"
    
    root = Path(__file__).parent.parent
    npm_pkg_dir = root / "npm-package" / "npm" / f"ktui-{plat}" / "bin"
    dist_bin = root / "dist" / binary_name
    
    npm_pkg_dir.mkdir(parents=True, exist_ok=True)
    
    if dist_bin.exists():
        dest = npm_pkg_dir / binary_name
        shutil.copy2(dist_bin, dest)
        if os_name != "win32":
            os.chmod(dest, 0o755)
        print(f"✓ Binary staged at {dest}")
    else:
        print(f"Error: {dist_bin} not found")
        sys.exit(1)

if __name__ == "__main__":
    main()
