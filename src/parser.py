import datetime
import json
import os
import time
from lxml import html
import logging

from progress.bar import IncrementalBar

from helper import http_request, Comic, get_comic_dir, save_json, get_currency, is_scanned_comic, init

init()

CONFIG = json.load(open('config.json'))


class Parser:
    without_img: list = []
    all_comics: list = []

    def add_and_save_comic(self, comic: Comic):
        if comic.image_url is None:
            sub_dir = 'w_img'
            self.without_img.append(comic)
        else:
            sub_dir = 'full'
            self.all_comics.append(comic)
        save_json(comic, f'{get_comic_dir(comic)}/{sub_dir}/{comic.id}.json')


def update_price(comic: Comic, exchange_usd):
    extra = 150.00
    comic.price_grn = round(comic.price_usd * exchange_usd + extra)


def update_comic_detail(comic: Comic):
    html_page = http_request(comic.url)
    root = html.fromstring(html_page)
    description = root.xpath('//div[@class="detaildatacol"]/p')[0].text
    if description:
        comic.description = root.xpath('//div[@class="detaildatacol"]/p')[0].text.strip()
    comic.price_usd = float(root.xpath('//li[@class="dcbsprice"]')[0].text.split('DCBS Price: $')[1])
    list_li = root.xpath('//ul[@class="meta"]/li')
    for li in list_li:
        row = li.text.split(': ')
        key = row[0].strip().lower().replace(' ', '_')
        value = row[1].strip()
        if key == 'writer':
            comic.writer = value
        if key == 'artist':
            comic.artist = value
        if key == 'product_code':
            comic.id = value.lower()
        if key == 'expected_ship_date':
            comic.expected_ship_at = datetime.datetime.strptime(value, '%m/%d/%Y').strftime('%Y-%m-%d')


def get_comic(comic_block, publisher: str) -> Comic:
    img_block = comic_block.findall('div')
    img_div = img_block[0]
    if img_div.get('class') != 'thumbnailborder':
        msg = f'DOM changed on list of comic.'
        logging.error(msg)
        raise Exception(msg)
    detail_div = img_block[1]
    if detail_div.get('class') != 'detail':
        msg = f'DOM changed on list of comic.'
        logging.error(msg)
        raise Exception(msg)
    tag_a = img_div.find('div').find('div').find('a')
    img_url = str(tag_a.find('img').get('src')).replace('/small/', '/xlarge/', 1)
    if 'noimagethumb' in img_url:
        img_url = None
    return Comic(tag_a.get('href').split('/')[2], CONFIG['site_url'] + tag_a.get('href'),
                 detail_div.find('div').find('h5').find('a').text.strip(),
                 publisher, img_url)


def handler_publisher_comics(params: dict, parser_result: Parser, exchange_usd, page=1):
    page_path = params["url"]
    if page != 1: page_path += f'/{page}'
    html_page = http_request(page_path, {'ProductsPerPage': '100'})
    root = html.fromstring(html_page)

    if root.xpath('//div[@id="body"]//div[@class="message-info"]'):
        print('END PUBLISHER COMICS')
        return parser_result
    comic_blocks = root.xpath('//ul[@class="thumblist"]/li')
    bar = IncrementalBar(f"{params['name'].upper()} page - {page}", max=len(comic_blocks))
    for comic_block in comic_blocks:
        comic = get_comic(comic_block, params['name'])
        bar.next()
        if ' Copy ' in comic.title:
            logging.info(f'`Copy` not ignored. title:{comic.title}')
            continue
        if is_scanned_comic(comic) is True:
            logging.info(f'This comic has already been scanned.Id={comic.id}')
            continue
        update_comic_detail(comic)
        if comic.publisher == 'Marvel Comics':
            pass
        elif not comic.writer and not comic.artist:
            logging.info(f'Souvenir not ignored.writer:{comic.writer},artist:{comic.artist}')
            continue
        update_price(comic, exchange_usd)
        parser_result.add_and_save_comic(comic)
    page = page + 1
    bar.finish()
    return handler_publisher_comics(params, parser_result, exchange_usd, page)


def get_publisher_list():
    publishers = []
    html_home_page = http_request(CONFIG['site_url'])
    root = html.fromstring(html_home_page)
    tmp_list_products_links = root.xpath("//div[@class='navblock']/ul/li/a[@href]")
    for el_publisher in tmp_list_products_links[0:9]:
        name = el_publisher.text.strip()
        if name in CONFIG['ignore_publishers']:
            print('ignore_publishers=' + name)
            continue
        publishers.append({'url': CONFIG['site_url'] + el_publisher.get('href'), 'name': name,
                           'key': name.lower().replace('!', '').replace(' ', '_'), 'comics_url': []})
    return publishers


def run():
    # print('_get_bank_api', get_currency())
    # send_telegram_msg('SAV', 'https://media.dcbservice.com/xlarge/OCT210674.jpg')
    # file = '/app/data/comics/scanned/2021-10/boom_studios/full/oct210728.json'
    # d = os.path.dirname(file)  ## directory of file
    # s = os.path.dirname(os.path.dirname(file))
    # print(d,s)
    # exit()
    print('START PARSE')
    # msg = 'TEST msg with IMG'
    publishers = get_publisher_list()
    save_json(publishers, f'{os.getcwd()}/data/comics/publishers-{datetime.datetime.now().strftime("%Y-%m")}.json')
    result = Parser()
    exchange_usd = get_currency()
    for publisher in publishers:
        handler_publisher_comics(publisher, result, exchange_usd)
        print('COMPLETE ONE PUBLISHER - ', publisher['name'].upper())


start_time = time.time()
run()

running_time = time.time() - start_time
print("--- %s seconds ---" % running_time)
if running_time / 60 > 1:
    print("--- %s min ---" % (running_time / 60))
