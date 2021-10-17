import json
import os
import time

from lxml import html
from progress.bar import IncrementalBar

from helper import http_request
from src.html_parser import HtmlParser

CONFIG = json.load(open('config.json'))


def init_dir():
    os.makedirs(f'{os.getcwd()}/data/log', exist_ok=True)


init_dir()


class Parser:
    without_img: list = []
    all_comics: list = []


def run():
    # print(d,s)
    # exit()
    print('START BUILD URLS')
    html_parser = HtmlParser(CONFIG['site_url'], CONFIG['ignore_publishers'])
    publishers = html_parser.get_publisher_list()
    parser = Parser()
    for publisher in publishers:
        list_one_publisher = html_parser.get_publisher_comics(publisher['url'])
        parser.all_comics += list_one_publisher['all_comics']
        parser.without_img += list_one_publisher['without_img']

        # 'comics_url': Parser()
        print('COMPLETE ONE PUBLISHER - ', publisher['name'].upper())


start_time = time.time()
run()

running_time = time.time() - start_time
print("--- %s seconds ---" % running_time)
if running_time / 60 > 1:
    print("--- %s min ---" % (running_time / 60))
