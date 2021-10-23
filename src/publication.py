import datetime
import logging
import os
import time

from googleapiclient.errors import HttpError
from progress.bar import IncrementalBar

from helper import read_scanned_comics, save_json, send_comic_in_group, init_log_and_dir
from spreadsheets import create_sheet, insert_in_sheet

init_log_and_dir()


def run(limit: int = 10):
    count = 0
    bar = IncrementalBar('Send comic in telegram group.', max=limit)
    sheet_title = datetime.datetime.now().strftime('%Y-%m')
    try:
        create_sheet(sheet_title)
    except HttpError:
        print(f'Sheet with title {sheet_title} exists.')
    for comic in read_scanned_comics('full'):
        if count == limit:
            return
        send_comic_in_group(comic)
        logging.info(f'Send in telegram comic with title:{comic.title} and id:{comic.id}')
        one_row = [comic.publisher, comic.title, comic.id, comic.expected_ship_at, comic.price_usd, comic.price_grn,
                   comic.url, comic.description, comic.writer, comic.artist, comic.image_url, comic.created_at]
        insert_in_sheet(datetime.datetime.now().strftime('%Y-%m'), [one_row])
        save_json(comic, f'{os.getcwd()}/var/comics/done/{comic.id}.json')
        logging.info(
            f'Insert in google sheet and save in folder `done` comic with title:{comic.title} and id:{comic.id}'
        )
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
