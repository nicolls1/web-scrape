import json
import os

from lxml import html
import redis
import requests
from urllib.parse import urlparse

import tornado.ioloop
import tornado.web

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = os.environ.get('REDIS_PORT', '6379')
REDIS_PREFIX = 'scrape-url'

html_versions = {
    '<!doctype html>': 'HTML 5',
    '<!doctype html public "-//w3c//dtd html 4.01//en" "http://www.w3.org/tr/html4/strict.dtd">': 'HTML 4.01 Strict',
    '<!doctype html public "-//w3c//dtd html 4.01 transitional//en" "http://www.w3.org/tr/html4/loose.dtd">': 'HTML 4.01 Transitional',
    '<!doctype html public "-//w3c//dtd html 4.01 frameset//en" "http://www.w3.org/tr/html4/frameset.dtd">': 'HTML 4.01 Frameset',
    '<!doctype html public "-//w3c//dtd xhtml 1.0 strict//en" "http://www.w3.org/tr/xhtml1/dtd/xhtml1-strict.dtd">': 'XHTML 1.0 Strict',
    '<!doctype html public "-//w3c//dtd xhtml 1.0 transitional//en" "http://www.w3.org/tr/xhtml1/dtd/xhtml1-transitional.dtd">': 'XHTML 1.0 Transitional',
    '<!doctype html public "-//w3c//dtd xhtml 1.0 frameset//en" "http://www.w3.org/tr/xhtml1/dtd/xhtml1-frameset.dtd">': 'XHTML 1.0 Frameset',
    '<!doctype html public "-//w3c//dtd xhtml 1.1//en" "http://www.w3.org/tr/xhtml11/dtd/xhtml11.dtd">': 'XHTML 1.1',
}


def get_page_info(url):
    try:
        page = requests.get(url)
    except requests.exceptions.RequestException as e:
        return {
            'status': 'failure',
            'error': f'Failed to reach URL. {e}'
        }
    tree = html.fromstring(page.content)

    # What HTML version has the document?
    version_string = page.text[:page.text.find('>') + 1].lower().strip()
    print(f'version_string: {version_string}')
    html_version = html_versions.get(version_string, 'unknown')

    # What is the page title?
    title = tree.xpath('//title')[0].text

    # How many headings of what level are in the document?
    heading_counts = {}
    for idx in range(1,7):
        heading_counts[f'h{idx}'] = len(tree.xpath(f'//h{idx}'))

    # How many internal and external links are in the document? Are there any inaccessible links and how many?
    # I will define "inaccessible" as invalid links.
    links = tree.xpath('//a')
    link_info = {
        'internal': 0,
        'external': 0,
        'inaccessible': 0,
    }
    for link in links:
        href = link.get('href')
        scheme = urlparse(href).scheme
        netloc = urlparse(href).netloc
        path = urlparse(href).path
        if href.startswith('#'):
            link_info['internal'] += 1
        elif scheme is '' and netloc is '' and path is '':
            link_info['inaccessible'] += 1
        elif scheme not in ['javascript', '']:
            link_info['external'] += 1
        else:
            link_info['internal'] += 1

    # Did the page contain a login-form?
    # Hard to tell, just say if form with password input then it login form, could be signup also
    login = len(tree.xpath('//form//input[@type="password"]')) > 0

    return {
        'status': 'success',
        'version': html_version,
        'title': title,
        'heading_counts': heading_counts,
        'link_info': link_info,
        'login_form': login,
    }


class MainHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", 'application/json')

    def get(self):
        url = self.get_argument("url")

        # check url in redis cache
        r = redis.StrictRedis(host=REDIS_HOST, port=int(REDIS_PORT), db=0)
        redis_key = f'{REDIS_PREFIX}-{url}'
        redis_value = r.get(redis_key)
        if redis_value:
            return self.write(redis_value)

        # not cached, compute
        page_info = get_page_info(url)
        r.set(redis_key, json.dumps(page_info), ex=60*60*24)
        return self.write(json.dumps(page_info))


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
    ])


if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
