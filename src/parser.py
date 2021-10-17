import datetime
import json
import os
import time
from json import JSONDecodeError
import requests
from lxml import html
import logging

import telebot
from progress.bar import IncrementalBar


def init_dir():
    os.makedirs(f'{os.getcwd()}/data/log', exist_ok=True)
    os.makedirs(f'{os.getcwd()}/data/comics/scanned', exist_ok=True)
    os.makedirs(f'{os.getcwd()}/data/comics/done', exist_ok=True)


init_dir()
logging.basicConfig(filename='data/log/{:%Y-%m}.log'.format(datetime.datetime.now()),
                    filemode='a',
                    format='%(asctime)s %(name)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logging.info("Running Logging!!!")
CONFIG = json.load(open('config.json'))
bot = telebot.TeleBot(CONFIG['tel_bot_token'])


class ComicsEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Comic):
            return obj.__dict__
        return json.JSONEncoder.default(self, obj)


class Comic(object):
    """
    The Comic object contains information about parsed ad
    """

    def __init__(self, _id: str = None, url: str = None, title: str = None, publisher: str = None,
                 image_url: str = None, description: str = None):
        self.id = _id
        self.url = url
        self.title = title
        self.publisher = publisher
        self.description = description
        self.image_url = image_url
        self.writer = None
        self.artist = None
        self.price_grn = None
        self.price_usd = None
        self.expected_ship_at = None
        self.created_at = datetime.datetime.now().__str__()


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


def http_request(url: str, cookies=None):
    if cookies is not None:
        response_inst = requests.session().get(url=url, cookies=cookies)
    else:
        response_inst = requests.get(url=url)
    response_inst.encoding = 'UTF-8'
    try:
        response = response_inst.json()
    except JSONDecodeError:
        response = response_inst.text
    log_msg = {
        'url': url,
        'status_code': response_inst.status_code,
        # 'headers': response_inst.headers,
        # 'content': response,
    }
    # print(log_msg)
    logging.info(log_msg)
    return response


def get_currency():
    api_url = 'https://api.privatbank.ua/p24api/pubinfo?json&exchange&coursid=5'
    for currency in http_request(api_url):
        if currency['ccy'] == 'USD':
            return float(currency['sale'])
    return None


def get_comic_dir(comic: Comic):
    period = datetime.datetime.now().strftime('%Y-%m')
    publisher = comic.publisher.lower().replace('!', '').replace(' ', '_')
    return f'{os.getcwd()}/data/comics/scanned/{period}/{publisher}'


def save_json(data, file_path: str):
    file_dir = os.path.dirname(file_path)
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    with open(file_path, 'w+', encoding='utf-8') as file:
        json.dump(data, file, cls=ComicsEncoder)


def send_telegram_msg(msg: str, img_url=None):
    # bot.send_message(CONFIG['telegram_group_id'], msg,parse_mode=ParseMode.HTML)
    if img_url is not None:
        bot.send_photo(
            CONFIG['telegram_group_id'],
            caption=msg,
            photo=get_img(img_url),
            parse_mode='HTML'
        )
    logging.info(f'In Telegram send message: {msg}.')


def send_comic_in_group(comic: Comic):
    msg = f'<b>{comic.title}</b>\n'
    if comic.description:
        msg += f'{comic.description}\n'
    if comic.writer:
        msg += f'Writer: {comic.writer}\n'
    if comic.artist:
        msg += f'Artist: {comic.artist}\n'
    msg += f'Expected Ship Date: <b>{comic.expected_ship_at}</b>\n'
    msg += f'Вартість: <b>{comic.price_grn}</b> грн'
    send_telegram_msg(msg, comic.image_url)


def update_price(comic: Comic, exchange_usd):
    if comic.price_usd <= 3:
        extra_percent = 95
    elif 3 < comic.price_usd < 5:
        extra_percent = 75
    elif 5 < comic.price_usd < 8:
        extra_percent = 55
    elif 8 < comic.price_usd < 10:
        extra_percent = 35
    else:
        extra_percent = 10
    extra_price = (comic.price_usd * extra_percent) / 100
    price_grn = (comic.price_usd + extra_price) * exchange_usd
    comic.price_grn = round(price_grn / 10) * 10


def get_img(url: str):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        response.raw.decode_content = True
        return response.raw.read()
    return None


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


def get_comic(comic_block, publisher: str):
    img_block = comic_block.findall('div')
    img_div = img_block[0]
    if img_div.get('class') != 'thumbnailborder':
        logging.error(f'DOM changed on list of comic.')
        return None
    detail_div = img_block[1]
    if detail_div.get('class') != 'detail':
        logging.error(f'DOM changed on list of comic.')
        return None
    tag_a = img_div.find('div').find('div').find('a')
    img_url = str(tag_a.find('img').get('src'))
    if 'noimagethumb' in img_url:
        img_url = None
    else:
        img_url = img_url.replace('/small/', '/xlarge/', 1)
    return Comic(tag_a.get('href').split('/')[2], CONFIG['site_url'] + tag_a.get('href'),
                 detail_div.find('div').find('h5').find('a').text.strip(),
                 publisher, img_url)


def is_scanned_comic(comic: Comic) -> bool:
    path_comic_dir = get_comic_dir(comic)
    if os.path.exists(f'{path_comic_dir}/full/{comic.id}.json'):
        return True
    if os.path.exists(f'{path_comic_dir}/w_img/{comic.id}.json'):
        return True
    if os.path.exists(f'{path_comic_dir}/souvenirs/{comic.id}.json'):
        return True
    if os.path.exists(f'{os.getcwd()}/data/comics/done/{comic.id}.json'):
        return True
    return False


def handler_publisher_comics(params: dict, parser_result: Parser, exchange_usd, page=1):
    page_path = params["url"]
    if page != 1: page_path += f'/{page}'
    html_page = http_request(page_path, {'ProductsPerPage': '100'})
    root = html.fromstring(html_page)
    if root.xpath('//div[@id="body"]//div[@class="message-info"]'):
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
        if comic.image_url is None:
            parser_result.add_and_save_comic(comic)
            continue
        update_comic_detail(comic)
        if comic.publisher == 'Marvel Comics':
            pass
        elif not comic.writer and not comic.artist:
            save_json(comic, f'{get_comic_dir(comic)}/souvenirs/{comic.id}.json')
            logging.info(f'Souvenir not ignored.writer:{comic.writer},artist:{comic.artist}')
            continue
        update_price(comic, exchange_usd)
        parser_result.add_and_save_comic(comic)
    page = page + 1
    bar.finish()
    return handler_publisher_comics(params, parser_result, exchange_usd, page)


def get_list_publisher():
    publishers = []
    html_home_page = http_request(CONFIG['site_url'])
    root = html.fromstring(html_home_page)
    tmp_list_products_links = root.xpath("//div[@class='navblock']/ul/li/a[@href]")
    for el_publisher in tmp_list_products_links[0:9]:
        name = el_publisher.text.strip()
        if name in CONFIG['ignore_publishers']:
            print('ignore_publishers=' + name)
            continue
        publishers.append({'url': CONFIG['site_url'] + el_publisher.get('href'), 'name': name})
    return publishers


def run():
    # print(d,s)
    # exit()
    publishers = get_list_publisher()
    result = Parser()
    exchange_usd = get_currency()
    for publisher in publishers:
        start_time_parse = time.time()
        handler_publisher_comics(publisher, result, exchange_usd)
        print('PARSED PUBLISHER - ', publisher['name'].upper(), 'Time(s):', round(time.time() - start_time_parse), 2)


start_time = time.time()
run()

running_time = time.time() - start_time
print("--- %s seconds ---" % running_time)
if running_time / 60 > 1:
    print("--- %s min ---" % (running_time / 60))
