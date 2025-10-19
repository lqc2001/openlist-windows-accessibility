import os
import sys
import zipfile
import requests
import shutil
from pathlib import Path

def download_vlc_components_for_development():
    """Download VLC components for development (core libraries and plugins only)"""
    project_root = Path(__file__).parent.parent
    vlc_dir = project_root / "vlc"

    print("Downloading VLC components...")

    # Choose appropriate VLC version based on Python architecture
    import platform
    if platform.machine() == 'AMD64' or '64' in platform.architecture()[0]:
        # 64-bit Python uses 64-bit VLC
        vlc_url = "https://download.videolan.org/pub/videolan/vlc/3.0.18/win64/vlc-3.0.18-win64.zip"
        vlc_arch = "64-bit"
    else:
        # 32-bit Python uses 32-bit VLC
        vlc_url = "https://download.videolan.org/pub/videolan/vlc/3.0.18/win32/vlc-3.0.18-win32.zip"
        vlc_arch = "32-bit"

    try:
        print(f"Downloading from {vlc_url}...")
        response = requests.get(vlc_url, stream=True, timeout=600)
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        temp_zip = project_root / "vlc_temp.zip"

        if total_size > 0:
            print(f"Download size: {total_size / (1024*1024):.1f} MB ({vlc_arch} version)")

        with open(temp_zip, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\rDownload progress: {progress:.1f}%", end="", flush=True)

        print("\nDownload complete, extracting components...")

        # Delete old VLC directory
        if vlc_dir.exists():
            print("Deleting old VLC directory...")
            shutil.rmtree(vlc_dir)

        # Create VLC directory
        vlc_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectory
        (vlc_dir / 'plugins').mkdir(parents=True, exist_ok=True)

        # Extract only needed files
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            print("Extracting core files...")
            vlc_folder_name = None
            for name in zip_ref.namelist():
                if name.endswith('/vlc.exe'):
                    vlc_folder_name = name.split('/')[0]
                    break

            if vlc_folder_name:
                print(f"Found VLC directory: {vlc_folder_name}")

                # Files to keep
                core_files = [
                    'libvlc.dll',
                    'libvlccore.dll'
                ]

                # Extract core library files
                extracted_files = 0
                for core_file in core_files:
                    full_path = f"{vlc_folder_name}/{core_file}"
                    if full_path in zip_ref.namelist():
                        source_file = zip_ref.open(full_path)
                        target_file = vlc_dir / core_file
                        with open(target_file, 'wb') as f:
                            f.write(source_file.read())
                        extracted_files += 1
                        print(f"  [OK] {core_file}")

                # Extract plugin files (all .dll files)
                print("Extracting plugin files...")
                plugin_count = 0
                for file_info in zip_ref.infolist():
                    if file_info.filename.startswith(f"{vlc_folder_name}/plugins/"):
                        if file_info.filename.endswith('.dll'):
                            # Modify path, remove VLC folder name prefix
                            relative_path = file_info.filename[len(vlc_folder_name) + 1:]
                            source_file = zip_ref.open(file_info.filename)
                            target_file = vlc_dir / relative_path
                            target_file.parent.mkdir(parents=True, exist_ok=True)
                            with open(target_file, 'wb') as f:
                                f.write(source_file.read())
                            plugin_count += 1
                            if plugin_count % 50 == 0:
                                print(f"  Extracted {plugin_count} plugins...")

                print(f"  [OK] Total extracted {plugin_count} plugin files")

        # Clean up temporary files
        temp_zip.unlink()

        print(f"\nVLC components extracted to: {vlc_dir}")
        print("Component check:")

        # Check core files
        core_files_check = ['libvlc.dll', 'libvlccore.dll']
        all_files_exist = True
        for file in core_files_check:
            file_path = vlc_dir / file
            if file_path.exists():
                size_mb = file_path.stat().st_size / (1024*1024)
                print(f"  [OK] {file} ({size_mb:.1f} MB)")
            else:
                print(f"  [FAIL] {file} missing!")
                all_files_exist = False

        # Check plugins directory
        plugins_dir = vlc_dir / 'plugins'
        if plugins_dir.exists():
            plugin_count = len(list(plugins_dir.rglob('*.dll')))
            print(f"  [OK] plugins directory ({plugin_count} plugin files)")
        else:
            print(f"  [FAIL] plugins directory missing!")
            all_files_exist = False

        # Calculate total size
        total_size = sum(f.stat().st_size for f in vlc_dir.rglob('*') if f.is_file()) / (1024*1024)
        print(f"Total size: {total_size:.1f} MB (significant space saving compared to full VLC)")

        if all_files_exist:
            print("\n[OK] VLC components download and configuration complete!")
            print("Note: Only core libraries and plugins included, no VLC executable")
            return True
        else:
            print("\n[WARN] VLC components incomplete, please check download!")
            return False

    except requests.exceptions.RequestException as e:
        print(f"\n[FAIL] Download failed: {e}")
        print("Please check network connection or try again later")
        return False
    except zipfile.BadZipFile as e:
        print(f"\n[FAIL] Extraction failed: {e}")
        print("Downloaded file may be corrupted, please re-download")
        return False
    except Exception as e:
        print(f"\n[FAIL] Unknown error: {e}")
        return False

def check_vlc_installation():
    """Check if VLC components are installed"""
    project_root = Path(__file__).parent.parent
    vlc_dir = project_root / "vlc"

    if not vlc_dir.exists():
        return False

    # 检查核心文件（新的组件结构）
    core_files = ['libvlc.dll', 'libvlccore.dll']
    for file in core_files:
        if not (vlc_dir / file).exists():
            return False

    # 检查插件目录
    plugins_dir = vlc_dir / 'plugins'
    if not plugins_dir.exists() or len(list(plugins_dir.rglob('*.dll'))) < 10:
        return False

    return True

def main():
    print("ForumAssist VLC Components Download Tool")
    print("=" * 40)

    # 检查是否已安装
    if check_vlc_installation():
        print("[OK] VLC components already exist, no need to re-download")
        response = input("Re-download? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            return

    # 开始下载
    if download_vlc_components_for_development():
        print("\n[SUCCESS] Successfully completed VLC components download!")
        print("Ready to start development or packaging applications.")
    else:
        print("\n[FAIL] Download failed!")
        print("Please check network connection or manually download VLC components")
        sys.exit(1)

if __name__ == "__main__":
    main()