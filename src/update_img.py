import datetime
import json
import logging
import os
import time

from progress.bar import IncrementalBar

from helper import init_log_and_dir, Comic, get_comic_dir, save_json, update_comic, get_currency, update_price, \
    HtmlParser

init_log_and_dir()


def update_and_move_comic(comic: Comic, parser: HtmlParser, exchange_usd: float) -> str:
    update_comic(comic, parser)
    update_price(comic, exchange_usd)
    path = f'{get_comic_dir(comic)}/full/{comic.id}.json'
    save_json(comic, path)
    return path


def scan_dirs():
    period = datetime.datetime.now().strftime('%Y-%m')
    root_dir = f'{os.getcwd()}/var/comics/scanned/{period}'
    exchange_usd = get_currency()
    for p_dir_n in os.listdir(root_dir):
        p_dir = os.path.join(root_dir, p_dir_n)
        if not os.path.isdir(p_dir):
            continue
        p_dir_w_img = p_dir + '/w_img'
        file_list = os.listdir(p_dir_w_img)
        bar = IncrementalBar(p_dir_n, max=len(file_list))
        updated_count = 0
        for file in file_list:
            file_path = f'{p_dir_w_img}/{file}'
            if not os.path.isfile(file_path) | (not file.endswith('.json')):
                continue
            attrs = json.load(open(file_path))
            comic = Comic(attrs['id'], attrs['url'], attrs['title'], attrs['publisher'])
            parser = HtmlParser(comic.url)
            img_src = parser.find_one_by_xpath('//div[@class="detailimagecol"]/img').get('src')
            if img_src.endswith('noimage.jpg'):
                bar.next()
                logging.info(f'Not upload image for comic with id {comic.id} and url {comic.url}.')
                continue
            else:
                updated_count = updated_count + 1
                new_path = update_and_move_comic(comic, parser, exchange_usd)
                logging.info(f'Uploaded image for comic with id {comic.id} and json move to {new_path}.')
                os.remove(file_path)
                bar.next()
        bar.finish()
        print(f'INFO : Upload image {updated_count}.')


start_time = time.time()
scan_dirs()

running_time = time.time() - start_time
print("--- %s seconds ---" % round(running_time, 2))
if running_time / 60 > 1:
    print("--- %s min ---" % round((running_time / 60), 2))
