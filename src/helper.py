import datetime
import json
import logging
import os
from json import JSONDecodeError

import telebot
from lxml import html
from lxml.html import HtmlElement
from typing import List, Optional
import requests

CONFIG = json.load(open('config.json'))
bot = telebot.TeleBot(CONFIG['tel_bot_token'])


class Comic(object):
    """
    The Comic object contains information about parsed ad
    """
    id: str
    url: str
    title: str
    publisher: str
    description: str = None
    image_url: str = None
    writer: str = None
    artist: str = None
    price_grn: float = None
    price_usd: float = None
    expected_ship_at: str = None
    created_at: str = datetime.datetime.now().__str__()

    def __init__(self, dictionary: dict):
        """Constructor"""
        for key in dictionary:
            setattr(self, key, dictionary[key])

    def __repr__(self):
        """"""
        attrs = str([x for x in self.__dict__])
        return "<comic: %s >" % attrs

    def scanned_full_file_path(self) -> Optional[str]:
        return f'{get_comic_dir(self)}/full/{self.id}.json'

    def scanned_w_img_file_path(self) -> Optional[str]:
        return f'{get_comic_dir(self)}/w_img/{self.id}.json'

    def scanned_souvenirs_file_path(self) -> Optional[str]:
        return f'{get_comic_dir(self)}/souvenirs/{self.id}.json'


class HtmlParser(object):
    root_html: HtmlElement

    def __init__(self, url: str, cookies: dict = None):
        html_page = http_request(url, cookies)
        self.root_html = html.fromstring(html_page)

    def find_one_by_xpath(self, xpath: str) -> HtmlElement:
        return self.root_html.xpath(xpath)[0]

    def find_by_xpath(self, xpath: str) -> List[HtmlElement]:
        return self.root_html.xpath(xpath)


class ComicsEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Comic):
            return obj.__dict__
        return json.JSONEncoder.default(self, obj)


def init_log_and_dir():
    os.makedirs(f'{os.getcwd()}/var/log', exist_ok=True)
    os.makedirs(f'{os.getcwd()}/var/comics/scanned', exist_ok=True)
    os.makedirs(f'{os.getcwd()}/var/comics/done', exist_ok=True)
    logging.basicConfig(filename='var/log/{:%Y-%m}.log'.format(datetime.datetime.now()),
                        filemode='a',
                        format='%(asctime)s %(name)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.INFO)
    logging.info("Running Logging!!!")


def http_request(url: str, cookies: dict = None):
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
    return f'{os.getcwd()}/var/comics/scanned/{period}/{publisher}'


def save_json(data, file_path: str):
    file_dir = os.path.dirname(file_path)
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    with open(file_path, 'w+', encoding='utf-8') as file:
        json.dump(data, file, cls=ComicsEncoder)


def send_telegram_msg(msg: str, img_url=None):
    bot.send_message(CONFIG['telegram_group_id'], msg, parse_mode='HTML')
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
        msg += comic.description if len(comic.description) < 800 else f'{comic.description[0:800]}...\n'
    if comic.writer:
        msg += f'Writer: {comic.writer}\n'
    if comic.artist:
        msg += f'Artist: {comic.artist}\n'
    msg += f'Expected Ship Date: <b>{comic.expected_ship_at}</b>\n'
    msg += f'Вартість: <b>{comic.price_grn}</b> грн'
    return bot.send_photo(CONFIG['telegram_group_id'], caption=msg, photo=get_img(comic.image_url), parse_mode='HTML')


def get_img(url: str):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        response.raw.decode_content = True
        return response.raw.read()
    return None


def update_price(comic: Comic, exchange_usd: float):
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


def update_comic(comic: Comic, parser: HtmlParser = None):
    if parser is None:
        parser = HtmlParser(comic.url)
    description = parser.find_one_by_xpath('//div[@class="detaildatacol"]/p').text
    if description:
        comic.description = description.strip()
    comic.price_usd = float(parser.find_one_by_xpath('//li[@class="dcbsprice"]').text.split('DCBS Price: $')[1])
    comic.image_url = parser.find_one_by_xpath('//div[@class="detailimagecol"]/img').get('src')
    for li in parser.find_by_xpath('//ul[@class="meta"]/li'):
        line = li.text.split(': ')
        key = line[0].strip().lower().replace(' ', '_')
        value = line[1].strip()
        if key == 'writer':
            comic.writer = value
        if key == 'artist':
            comic.artist = value
        if key == 'expected_ship_date':
            comic.expected_ship_at = datetime.datetime.strptime(value, '%m/%d/%Y').strftime('%Y-%m-%d')


def is_scanned_comic(comic: Comic) -> bool:
    path_comic_dir = get_comic_dir(comic)
    if os.path.exists(comic.scanned_full_file_path()):
        return True
    if os.path.exists(comic.scanned_w_img_file_path()):
        return True
    if os.path.exists(f'{path_comic_dir}/souvenirs/{comic.id}.json'):
        return True
    if os.path.exists(f'{os.getcwd()}/var/comics/done/{comic.id}.json'):
        return True
    return False


def read_scanned_comics(sub_dir: str = 'full'):
    period = datetime.datetime.now().strftime('%Y-%m')
    root_dir = f'{os.getcwd()}/var/comics/scanned/{period}'
    for publisher_dir_name in os.listdir(root_dir):
        publisher_dir = os.path.join(root_dir, publisher_dir_name)
        if not os.path.isdir(publisher_dir):
            continue
        publisher_dir_w_img = f'{publisher_dir}/{sub_dir}'
        file_list = os.listdir(publisher_dir_w_img)
        for file in file_list:
            file_path = f'{publisher_dir_w_img}/{file}'
            if not os.path.isfile(file_path) | (not file.endswith('.json')):
                continue
            comic = Comic(json.load(open(file_path)))
            yield comic
