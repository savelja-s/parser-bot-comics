import logging

from lxml import html
from progress.bar import IncrementalBar

from src.helper import http_request, Comic, is_scanned_comic


class HtmlParser(object):
    ignore_publishers: list
    site_url: str

    def __init__(self, site_url: str, ignore_publishers: list = None):
        self.ignore_publishers = ignore_publishers
        self.site_url = site_url

    def get_publisher_list(self):
        publishers = []
        html_home_page = http_request(self.site_url)
        root = html.fromstring(html_home_page)
        tmp_list_products_links = root.xpath("//div[@class='navblock']/ul/li/a[@href]")
        for el_publisher in tmp_list_products_links[0:9]:
            name = el_publisher.text.strip()
            if self.ignore_publishers and name in self.ignore_publishers:
                print('ignore_publishers=' + name)
                continue
            publishers.append({'url': self.site_url + el_publisher.get('href'), 'name': name,
                               'key': name.lower().replace('!', '').replace(' ', '_')})
        return publishers

    def get_comic(self, comic_block) -> Comic:
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
        img_url = tag_a.find('img').get('src')
        if 'noimagethumb' in img_url:
            img_url = None
        else:
            img_url = img_url.replace('/small/', '/xlarge/', 1)
        return Comic(tag_a.get('href').split('/')[2], self.site_url + tag_a.get('href'),
                     detail_div.find('div').find('h5').find('a').text.strip(), img_url)

    def get_publisher_comics(self, url: str, result={'without_img': [], 'all_comics': []}, page=1):
        page_path = url
        if page != 1: page_path += f'/{page}'
        html_page = http_request(page_path, {'ProductsPerPage': '100'})
        root = html.fromstring(html_page)
        if root.xpath('//div[@id="body"]//div[@class="message-info"]'):
            return result
        comic_blocks = root.xpath('//ul[@class="thumblist"]/li')
        bar = IncrementalBar(f"{url.split('/')[2]} - page {page}", max=len(comic_blocks))
        for comic_block in comic_blocks:
            comic = self.get_comic(comic_block)
            if ' Copy ' in comic.title:
                logging.info(f'`Copy` not ignored. title:{comic.title}')
                continue
            if is_scanned_comic(comic) is True:
                logging.info(f'This comic has already been scanned.Id={comic.id}')
                continue
            bar.next()
            if comic.image_url is None:
                result['without_img'].append(comic)
            else:
                result['all_comics'].append(comic)
        page = page + 1
        bar.finish()
        return self.get_publisher_comics(url, result, page)
