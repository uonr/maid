#!/usr/bin/env python3

import time
import subprocess
import hashlib
import shutil
import re
from pathlib import Path
from urllib.parse import urlparse

DOWNLOADS_DIR = Path.home() / "Downloads"
TARGET_DIRS = {
    "novelai.net": Path.home() / "Downloads" / "AI",
    "iwara.tv": Path.home() / "Downloads" / "Iwara",
    "gelbooru.com": Path.home() / "Downloads" / "Illustration", 
    "pixiv.net": Path.home() / "Downloads" / "Illustration",
    "twimg.com": Path.home() / "Downloads" / "Twitter",
    "x.com": Path.home() / "Downloads" / "Twitter"
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

def parse_twitter_url(url: str) -> tuple[str, str, str] | None:
    """Parse Twitter/X.com URL and extract username, status ID, and photo number
    
    Args:
        url: Twitter URL like https://x.com/username/status/1234567890/photo/1
        
    Returns:
        Tuple of (username, status_id, photo_number) or None if not a valid Twitter URL
    """
    pattern = r'https?://(?:twitter\.com|x\.com)/([^/]+)/status/(\d+)(?:/photo/(\d+))?'
    match = re.match(pattern, url)
    
    if match:
        username = match.group(1)
        status_id = match.group(2)
        photo_number = match.group(3) or "1"  # Default to 1 if photo number not specified
        return username, status_id, photo_number
    
    return None

def generate_twitter_filename(original_filename: str, username: str, status_id: str, photo_number: str) -> str:
    file_path = Path(original_filename)
    extension = file_path.suffix
    return f"[{username}][{status_id}][{photo_number}]{extension}"

def move_file_by_domain(file_path, source_urls: list[str]):
    domains = list(set(get_domain_from_url(url) for url in source_urls))
    if not domains:
        return False
    
    target_dir = None
    for domain in domains:
        for rule_domain, rule_dir in TARGET_DIRS.items():
            if domain.endswith(rule_domain):
                target_dir = rule_dir
                break
    
    if not target_dir:
        return False
    
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Check if this is a Twitter/X.com URL that needs special filename handling
        twitter_info = None
        if target_dir.name == "Twitter":
            for source_url in source_urls:
                twitter_info = parse_twitter_url(source_url)
                if twitter_info:
                    break
        
        # Determine the target filename
        if twitter_info:
            username, status_id, photo_number = twitter_info
            new_filename = generate_twitter_filename(file_path.name, username, status_id, photo_number)
            target_file = target_dir / new_filename
            print(f"Renaming Twitter file to: {new_filename}")
        else:
            target_file = target_dir / file_path.name
        
        # Handle file conflicts by comparing content hash
        while target_file.exists():
            file_hash = hashlib.md5(file_path.read_bytes()).hexdigest()
            target_hash = hashlib.md5(target_file.read_bytes()).hexdigest()
            if file_hash == target_hash:
                # Files are identical, remove the source file
                file_path.unlink()
                print(f"Removed duplicate file {file_path.name}")
                return True
            
            # Files are different, append hash to filename
            if twitter_info:
                username, status_id, photo_number = twitter_info
                base_name = f"[{username}][{status_id}][{photo_number}]_{file_hash}"
                extension = Path(file_path.name).suffix
                target_file = target_dir / f"{base_name}{extension}"
            else:
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
        if move_file_by_domain(file_path, source_urls):
            files_moved += 1
    
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
