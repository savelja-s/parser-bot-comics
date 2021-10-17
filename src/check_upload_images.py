import logging
import os
import time

from progress.bar import IncrementalBar

from helper import init_log_and_dir, Comic, save_json, update_comic, get_currency, update_price, HtmlParser, \
    read_scanned_comics

init_log_and_dir()


def create_full_comic(comic: Comic, parser: HtmlParser, exchange_usd: float) -> str:
    update_comic(comic, parser)
    update_price(comic, exchange_usd)
    path = comic.scanned_full_file_path()
    save_json(comic, path)
    return path


def run():
    exchange_usd = get_currency()
    updated_count = 0
    file_list = [i for i in read_scanned_comics('w_img')]
    bar = IncrementalBar('Check if upload images for comics.', max=len(file_list))
    for comic in file_list:
        parser = HtmlParser(comic.url)
        img_src = parser.find_one_by_xpath('//div[@class="detailimagecol"]/img').get('src')
        if img_src.endswith('noimage.jpg'):
            bar.next()
            logging.info(f'Not upload image for comic with id {comic.id} and url {comic.url}.')
            continue
        else:
            updated_count = updated_count + 1
            new_path = create_full_comic(comic, parser, exchange_usd)
            logging.info(f'Uploaded image for comic with id {comic.id} and json move to {new_path}.')
            os.remove(comic.scanned_w_img_file_path())
        bar.next()
    bar.finish()
    print(f'INFO : Upload image {updated_count}.')


start_time = time.time()
run()

running_time = time.time() - start_time
print("--- %s seconds ---" % round(running_time, 2))
if running_time / 60 > 1:
    print("--- %s min ---" % round((running_time / 60), 2))
