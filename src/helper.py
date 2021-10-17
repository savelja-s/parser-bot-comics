import datetime
import json
import logging
import os
from json import JSONDecodeError

import requests
import telebot

CONFIG = json.load(open('config.json'))
bot = telebot.TeleBot(CONFIG['tel_bot_token'])


class Comic(object):
    """
    The Comic object contains information about parsed ad
    """

    def set_publisher(self, publisher_name: str):
        self.publisher_name = publisher_name
        self.publisher = publisher_name.lower().replace('!', '').replace(' ', '_')

    def __init__(self, _id: str, url: str, title: str, image_url: str):
        self.id = _id
        self.url = url
        self.title = title
        self.publisher_name = None
        self.publisher = None
        self.publisher_name = None
        self.image_url = image_url
        self.description = None
        self.writer = None
        self.artist = None
        self.price_grn = None
        self.price_usd = None
        self.expected_ship_at = None
        self.created_at = datetime.datetime.now().__str__()


class ComicsEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Comic):
            return obj.__dict__
        return json.JSONEncoder.default(self, obj)


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


def save_json(data, file_path: str):
    file_dir = os.path.dirname(file_path)
    os.makedirs(file_dir, exist_ok=True)
    with open(file_path, 'w+', encoding='utf-8') as file:
        json.dump(data, file, cls=ComicsEncoder)


def get_img(url: str):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        response.raw.decode_content = True
        return response.raw.read()
    return None


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


def get_comic_dir(comic: Comic):
    period = datetime.datetime.now().strftime('%Y-%m')
    return f'{os.getcwd()}/data/comics/scanned/{period}/{comic.publisher}'


def is_scanned_comic(comic: Comic) -> bool:
    path_comic_dir = get_comic_dir(comic)
    if os.path.exists(f'{path_comic_dir}/full/{comic.id}.json'):
        return True
    if os.path.exists(f'{path_comic_dir}/w_img/{comic.id}.json'):
        return True
    if os.path.exists(f'{os.getcwd()}/data/comics/done/{comic.id}.json'):
        return True
    return False


def init():
    os.makedirs(f'{os.getcwd()}/data/log', exist_ok=True)
    os.makedirs(f'{os.getcwd()}/data/comics/scanned', exist_ok=True)
    os.makedirs(f'{os.getcwd()}/data/comics/done', exist_ok=True)
    logging.basicConfig(filename='data/log/{:%Y-%m}.log'.format(datetime.datetime.now()),
                        filemode='a',
                        format='%(asctime)s %(name)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.INFO)
    logging.info("Running Logging!!!")
