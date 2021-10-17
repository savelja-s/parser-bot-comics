import json
import time
import logging

from progress.bar import IncrementalBar

from helper import http_request, init_log_and_dir, Comic, save_json, get_currency, update_price, is_scanned_comic, \
    update_comic, HtmlParser

init_log_and_dir()
CONFIG = json.load(open('config.json'))


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
    return Comic({'id': tag_a.get('href').split('/')[2], 'url': CONFIG['site_url'] + tag_a.get('href'),
                  'title': detail_div.find('div').find('h5').find('a').text.strip(),
                  'publisher': publisher, 'image_url': img_url})


def handler_publisher_comics(params: dict, exchange_usd, page=1):
    page_path = params["url"]
    if page != 1: page_path += f'/{page}'
    parser = HtmlParser(page_path, {'ProductsPerPage': '100'})
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
        if is_scanned_comic(comic) is True:
            logging.info(f'This comic has already been scanned.Id={comic.id}')
            continue
        if comic.image_url is None:
            save_json(comic, comic.scanned_w_img_file_path())
            continue
        update_comic(comic)
        if comic.publisher == 'Marvel Comics':
            pass
        elif not comic.writer and not comic.artist:
            save_json(comic, comic.scanned_souvenirs_file_path())
            logging.info(f'Souvenir not ignored.writer:{comic.writer},artist:{comic.artist}')
            continue
        update_price(comic, exchange_usd)
        save_json(comic, comic.scanned_full_file_path())
    bar.finish()
    handler_publisher_comics(params, exchange_usd, (page + 1))


def get_list_publisher():
    publishers = []
    parser = HtmlParser(CONFIG['site_url'])
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
    exchange_usd = get_currency()
    for publisher in publishers:
        start_time_parse = time.time()
        handler_publisher_comics(publisher, exchange_usd)
        print('PARSED PUBLISHER - ', publisher['name'].upper(), 'Time(s):', round((time.time() - start_time_parse), 2))


start_time = time.time()
run()

running_time = time.time() - start_time
print("--- %s seconds ---" % running_time)
if running_time / 60 > 1:
    print("--- %s min ---" % (running_time / 60))
