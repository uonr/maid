#!/usr/bin/env python
import os
import logging
import hashlib
import time
import shutil
from PIL import Image
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def process_image(image_path):
    image = Image.open(image_path)
    image.load()
    if image.info.get('Software', '') == 'NovelAI' or image.info.get('parameters', None) is not None:
        destination_dir = os.path.expanduser('~/Desktop/AI')
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)
        destination_path = os.path.join(destination_dir, os.path.basename(image_path))
        if os.path.exists(destination_path):
            # check if the file is the same by hash
            with open(image_path, 'rb') as f:
                hash_source = hashlib.md5(f.read()).hexdigest()
            with open(destination_path, 'rb') as f:
                hash_destination = hashlib.md5(f.read()).hexdigest()
            if hash_source == hash_destination:
                logging.info("Duplicate file found: {}".format(image_path))
                os.remove(image_path)
                return
            else:
                # add a timestamp to the filename
                destination_path = os.path.join(destination_dir, "{}_{}".format(time.strftime("%Y%m%d-%H%M%S"), os.path.basename(image_path)))

        shutil.move(image_path, destination_path)
        logging.info("Moved {} to {}".format(image_path, destination_dir))

class DownloadsWatcher(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.png'):
            try:
                process_image(event.src_path)
            except FileNotFoundError:
                logging.error("File not found: {}".format(event.src_path))
                return

def main():
    event_handler = DownloadsWatcher()
    observer = Observer()
    observer.schedule(event_handler, os.path.expanduser('~/Downloads'), recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
