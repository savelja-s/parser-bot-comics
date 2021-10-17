import os
import time
from progress.bar import IncrementalBar

from helper import read_scanned_comics, save_json, send_comic_in_group


def run(limit: int = 5):
    count = 0
    bar = IncrementalBar('Check if upload images for comics.', max=limit)
    for comic in read_scanned_comics('full'):
        if count == limit:
            return
        send_comic_in_group(comic)
        save_json(comic, f'{os.getcwd()}/var/comics/done/{comic.id}.json')
        os.remove(comic.scanned_full_file_path())
        count = count + 1
        bar.next()
    bar.finish()


start_time = time.time()
run()

running_time = time.time() - start_time
print("--- %s seconds ---" % running_time)
if running_time / 60 > 1:
    print("--- %s min ---" % (running_time / 60))
