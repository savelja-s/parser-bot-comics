import datetime
import json
import logging
import time

import traceback
from googleapiclient.errors import HttpError
from progress.bar import IncrementalBar

import helper
from spreadsheets import insert_in_sheet, create_sheet

helper.init_log_and_dir('parser')
CONFIG = json.load(open('config/config.json'))


def get_comic(comic_block, publisher: str):
    tag_a = None
    title = None
    for div in comic_block.findall('div'):
        if div.get('class') == 'thumbnailborder':
            tag_a = div.find('div').find('div').find('a')
        if div.get('class') == 'detail':
            title = div.find('div').find('h5').find('a').text.strip()
    img_url = str(tag_a.find('img').get('src'))
    if 'noimagethumb' in img_url:
        img_url = None
    else:
        img_url = img_url.replace('/small/', '/xlarge/', 1)
    return helper.Comic({'id': tag_a.get('href').split('/')[2], 'url': CONFIG['site_url'] + tag_a.get('href'),
                         'title': title, 'publisher': publisher, 'image_url': img_url})


def handler_publisher_comics(params: dict, publisher_comics_without_img: list, exchange_usd, page=1):
    page_path = params["url"]
    if page != 1:
        page_path += f'/{page}'
    parser = helper.HtmlParser(page_path, {'ProductsPerPage': '100'})
    if parser.find_by_xpath('//div[@id="body"]//div[@class="message-info"]'):
        return
    comic_blocks = parser.find_by_xpath('//ul[@class="thumblist"]/li')
    bar = IncrementalBar(f"{params['name'].upper()} page - {page}", max=len(comic_blocks))
    for comic_block in comic_blocks:
        comic = get_comic(comic_block, params['name'])
        bar.next()
        if ' Copy ' in comic.title:
            logging.info(f'`Copy` not ignored. title:{comic.title}')
            continue
        if helper.is_scanned_comic(comic) is True:
            logging.info(f'This comic has already been scanned.Id={comic.id}')
            continue
        if comic.image_url is None:
            helper.save_json(comic, comic.scanned_w_img_file_path())
            one_row = [comic.publisher, comic.title, comic.id, comic.url, comic.created_at]
            publisher_comics_without_img.append(one_row)
            continue
        helper.update_comic(comic)
        helper.update_price(comic, exchange_usd)
        logging.info(f'Save comic with title:{comic.title} and id:{comic.id}')
        helper.save_json(comic, comic.scanned_full_file_path())
    bar.finish()
    handler_publisher_comics(params, publisher_comics_without_img, exchange_usd, (page + 1))


def get_list_publisher():
    publishers = []
    parser = helper.HtmlParser(CONFIG['site_url'])
    tmp_list_products_links = parser.find_by_xpath("//div[@class='navblock']/ul/li/a[@href]")
    for el_publisher in tmp_list_products_links[0:9]:
        name = el_publisher.text.strip()
        if name in CONFIG['ignore_publishers']:
            print('ignore_publishers=' + name)
            continue
        publishers.append({'url': CONFIG['site_url'] + el_publisher.get('href'), 'name': name})
    return publishers


def run():
    publishers = get_list_publisher()
    exchange_usd = helper.get_currency()
    sheet_title = f'{datetime.datetime.now().strftime("%Y-%m")}_w_img'
    try:
        create_sheet(sheet_title)
        print(f'CREATE {sheet_title}')
    except HttpError:
        print(f'Sheet with title {sheet_title} exists.')
    publisher_comics_without_img = []
    try:
        for publisher in publishers:
            start_time_parse = time.time()
            publisher_comics_without_img = []
            handler_publisher_comics(publisher, publisher_comics_without_img, exchange_usd)
            print(
                f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} Publisher:',
                publisher['name'].upper(),
                'Time(s):',
                round((time.time() - start_time_parse), 2)
            )
    except (Exception, KeyboardInterrupt, TypeError) as e:
        print('Exception:', e)
        logging.error(traceback.format_exc())
    if len(publisher_comics_without_img):
        insert_in_sheet(f'{datetime.datetime.now().strftime("%Y-%m")}_w_img', publisher_comics_without_img)


start_time = time.time()
run()

running_time = time.time() - start_time
print("--- %s seconds ---" % running_time)
if running_time / 60 > 1:
    print("--- %s min ---" % (running_time / 60))
