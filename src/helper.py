import datetime
import json
import logging
import os
from json import JSONDecodeError
from lxml import html
from lxml.html import HtmlElement
from typing import List
import requests


class Comic(object):
    """
    The Comic object contains information about parsed ad
    """

    def __init__(self, _id: str, url: str, title: str, publisher: str = None,
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


class HtmlParser(object):
    root_html: HtmlElement

    def __init__(self, url: str):
        html_page = http_request(url)
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
    return f'{os.getcwd()}/var/comics/scanned/{period}/{publisher}'


def save_json(data, file_path: str):
    file_dir = os.path.dirname(file_path)
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    with open(file_path, 'w+', encoding='utf-8') as file:
        json.dump(data, file, cls=ComicsEncoder)


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


def update_comic(comic: Comic, parser: HtmlParser):
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
