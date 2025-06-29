#!/usr/bin/env python3

import time
import subprocess
import hashlib
import shutil
from pathlib import Path
from urllib.parse import urlparse

DOWNLOADS_DIR = Path.home() / "Downloads"
TARGET_DIRS = {
    "novelai.net": Path.home() / "Downloads" / "AI",
    "iwara.tv": Path.home() / "Downloads" / "Iwara",
    "gelbooru.com": Path.home() / "Downloads" / "Illustration", 
    "pixiv.net": Path.home() / "Downloads" / "Illustration"
}

DOWNLOADING_EXTENSIONS = {'.download', '.tmp', '.part', '.crdownload', '.partial'}

def get_file_download_source(file_path) -> list[str]:
    """Get file download source by mdls"""
    try:
        result = subprocess.run([
            'mdls', "-raw", '-attr', 'kMDItemWhereFroms', str(file_path)
        ], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to get download source for {file_path}: {e}")
        print(e.stdout)
        return []

    if not result.stdout or not result.stdout.startswith('('):
        return []

    urls = []
    for url in result.stdout.strip('()').split(','):
        url = url.strip().strip('"')
        if not url:
            continue
        if url.startswith('blob:'):
            url = url[5:]
        if url.startswith('http://') or url.startswith('https://'):
            urls.append(url)

    return urls


def get_domain_from_url(url) -> str:
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return ""

def move_file_by_domain(file_path, source_url):
    domain = get_domain_from_url(source_url)
    if not domain:
        return False
    
    target_dir = None
    for rule_domain, rule_dir in TARGET_DIRS.items():
        if domain.endswith(rule_domain):
            target_dir = rule_dir
            break
    
    if not target_dir:
        return False
    
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        target_file = target_dir / file_path.name
        
        while target_file.exists():
            # Compare file content hash
            file_hash = hashlib.md5(file_path.read_bytes()).hexdigest()
            target_hash = hashlib.md5(target_file.read_bytes()).hexdigest()
            if file_hash == target_hash:
                break
            target_file = target_dir / f"{file_path.stem}_{file_hash}{file_path.suffix}"
        
        shutil.move(str(file_path), str(target_file))
        print(f"Moved file {file_path.name} to {target_file}")
        return True
        
    except Exception as e:
        print(f"Failed to move file {file_path}: {e}")
        return False

def remove_empty_target_dirs():
    for dir_path in TARGET_DIRS.values():
        if not dir_path.exists():
            continue
        if not any(dir_path.iterdir()):
            dir_path.rmdir()

def is_file_downloading(file_path) -> bool:
    if file_path.suffix.lower() in DOWNLOADING_EXTENSIONS:
        return True

    # Check if file was modified in the last 30 seconds
    try:
        file_stat = file_path.stat()
        current_time = time.time()
        if current_time - file_stat.st_mtime < 30:
            return True
    except OSError:
        return True
    
    # Check if file can be exclusively opened
    try:
        with open(file_path, 'rb+') as f:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return False
    except (OSError, IOError, ImportError):
        return True
    
    return False

def scan_downloads():
    if not DOWNLOADS_DIR.exists():
        print(f"Downloads directory does not exist: {DOWNLOADS_DIR}")
        return
    
    files_processed = 0
    files_moved = 0
    files_skipped = 0
    
    for file_path in DOWNLOADS_DIR.iterdir():
        if not file_path.is_file():
            continue
        
        if file_path.name.startswith('.'):
            continue
        
        if is_file_downloading(file_path):
            files_skipped += 1
            continue
            
        files_processed += 1
        
        source_urls = get_file_download_source(file_path)
        for source_url in source_urls:
            if move_file_by_domain(file_path, source_url):
                files_moved += 1
                break
        else:
            pass
    
    if files_processed > 0 or files_skipped > 0:
        print(f"Scanned {files_processed} files, moved {files_moved} files, skipped {files_skipped} files")

def main():
    try:
        while True:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{current_time}] Scanning...")
            
            scan_downloads()
            remove_empty_target_dirs()
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("User interrupted")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
