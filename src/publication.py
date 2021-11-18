import datetime
import logging
import os
import time
from typing import Generator

import traceback
from googleapiclient.errors import HttpError
from progress.bar import IncrementalBar

import helper
from spreadsheets import create_sheet, insert_in_sheet

helper.init_log_and_dir('publication')


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
        new_path = create_full_comic(comic, parser, exchange_usd)
        logging.info(f'Uploaded image for comic with id {comic.id} and json move to {new_path}.')
        helper.insert_in_sheet(f'{datetime.datetime.now().strftime("%Y-%m")}_upload_img', [helper.prepare_comic(comic)])
        os.remove(comic.scanned_w_img_file_path())
        yield comic


def run(limit: int = 10):
    count = 0
    bar = IncrementalBar('Send comic in telegram group.', max=limit)
    sheet_title = f'{datetime.datetime.now().strftime("%Y-%m")}_posted'
    try:
        create_sheet(sheet_title)
    except HttpError:
        print(f'Sheet with title {sheet_title} exists.')
    published_comics = []
    try:
        while True:
            for comic in helper.read_scanned_comics('full'):
                if count == limit:
                    bar.finish()
                    break
                helper.posted_comic(comic)
                published_comics.append(helper.prepare_comic(comic))
                count = count + 1
                bar.next()
            if count >= limit:
                bar.finish()
                insert_in_sheet(f'{datetime.datetime.now().strftime("%Y-%m")}_posted', published_comics)
                break
            print('PARSED WITHOUT IMG')
            for comic_with_upload_img in read_comics_without_images():
                helper.posted_comic(comic_with_upload_img)
                count = count + 1
                bar.next()
                if count == limit:
                    break
            bar.finish()
            break
    except (Exception, KeyboardInterrupt, TypeError) as e:
        print('Exception:', e)
        logging.error(traceback.format_exc())
    if len(published_comics):
        insert_in_sheet(f'{datetime.datetime.now().strftime("%Y-%m")}_posted', published_comics)


start_time = time.time()
run()

running_time = time.time() - start_time
print("--- %s seconds ---" % running_time)
if running_time / 60 > 1:
    print("--- %s min ---" % (running_time / 60))
print(f'Date:{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
