import datetime
import logging
import os
import time
from typing import Generator

from googleapiclient.errors import HttpError
from progress.bar import IncrementalBar

import helper
from spreadsheets import create_sheet

helper.init_log_and_dir()


def create_full_comic(comic: helper.Comic, parser: helper.HtmlParser, exchange_usd: float) -> str:
    helper.update_comic(comic, parser)
    helper.update_price(comic, exchange_usd)
    path = comic.scanned_full_file_path()
    helper.save_json(comic, path)
    return path


def read_comics_without_images() -> Generator[helper.Comic, None, None]:
    exchange_usd = helper.get_currency()
    for comic in helper.read_scanned_comics('w_img'):
        parser = helper.HtmlParser(comic.url)
        img_src = parser.find_one_by_xpath('//div[@class="detailimagecol"]/img').get('src')
        if img_src.endswith('noimage.jpg'):
            logging.info(f'Not upload image for comic with id {comic.id} and url {comic.url}.')
            continue
        # remove in google spreadsheets with title f'{datetime.datetime.now().strftime("%Y-%m")}_w_img'
        new_path = create_full_comic(comic, parser, exchange_usd)
        logging.info(f'Uploaded image for comic with id {comic.id} and json move to {new_path}.')
        os.remove(comic.scanned_w_img_file_path())
        yield comic


def run(limit: int = 10):
    count = 0
    bar = IncrementalBar('Send comic in telegram group.', max=limit)
    sheet_title = datetime.datetime.now().strftime('%Y-%m')
    try:
        create_sheet(sheet_title)
    except HttpError:
        print(f'Sheet with title {sheet_title} exists.')
    for comic in helper.read_scanned_comics('full'):
        if count == limit:
            bar.finish()
            return
        helper.posted_comic(comic)
        count = count + 1
        bar.next()

    if count >= limit:
        bar.finish()
        return
    print('PARSED WITHOUT IMG')
    for comic_with_upload_img in read_comics_without_images():
        helper.posted_comic(comic_with_upload_img)
        count = count + 1
        bar.next()
        if count == limit:
            break
    bar.finish()


start_time = time.time()
run()

running_time = time.time() - start_time
print("--- %s seconds ---" % running_time)
if running_time / 60 > 1:
    print("--- %s min ---" % (running_time / 60))
