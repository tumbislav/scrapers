# coding: utf-8
"""
File: spiders.py
Inspired by pixiv spider by Alex

Part of the scrapers package.
"""
__author__ = 'Marko Čibej'


import requests
import re
import os
import json
import logging
from http import cookiejar, HTTPStatus
from bs4 import BeautifulSoup
from helper import SimpleCrypt, ScraperException
from config import Configuration

logger = logging.getLogger('scr')


class Spider:
    session: requests.Session

    def __init__(self):
        self.session = requests.session()

    def check_page(self, url):
        """
        Check if an url is available
        :param url: the url to check
        :return: the HTTP status code
        """
        return self.session.get(url, allow_redirects=False).status_code


class PixivSpider(Spider):

    prepare_url = set()
    multipic_url = set()
    next_pages_url = []
    origin_url = {}
    really_multipic_url = {}

    def __init__(self, site_def: dict):
        super().__init__()

        self.session.headers = site_def['headers']
        self.session.cookies = cookiejar.LWPCookieJar(site_def['cookie-file'])

        self.params = site_def['params']
        self.data = site_def['data']
        self.rank = site_def['rank']
        self.refer = site_def['refer']
        self.max_page = site_def['max-page'] + 1  # TODO: why +1?
        self.begin_url = site_def['begin-url'].format(self.rank, self.refer, self.date)
        self.site_def = site_def

    def get_postkey(self):
        r = self.session.get(self.site_def['url']['post-url'], params=self.params)
        soup = BeautifulSoup(r.content, 'lxml')
        post_key = soup.find_all('input')[0]['value']
        self.data['post_key'] = post_key

    def check_login(self):
        """
        Test if we're logged in.
        :return: True or false
        """
        return self.check_page(self.site_def['url']['user-settings']) == HTTPStatus.OK

    def login(self, crypt: SimpleCrypt, account_name='account') -> bool:
        """
        Log in using the named account in site_def. The username and password are encrypted.
        :param crypt: decryptor, already initialized with the appropriate key
        :param account_name: the name of the account in self.site_def
        :return: whether login succeeded
        """
        try:
            self.get_postkey()
            self.data['pixiv_id'] = crypt.decrypt(self.site_def[account_name]['username'])
            self.data['password'] = crypt.decrypt(self.site_def[account_name]['password'])
            post_data = self.session.post(self.site_def['post-url'], data=self.data)
            self.session.cookies.save(ignore_discard=True, ignore_expires=True)

            logger.info('logged into site {}'.format(self.site_def['slug']))
            return True
        finally:
            return False

    def start_spider(self):
        """
        Collect the initial page links for the spider to work on.
        """
        self.session.headers = self.site_def['headers']
        rank_list_info = self.session.get(self.begin_url)
        rank_list_obj = BeautifulSoup(rank_list_info.content, 'lxml')
        links = rank_list_obj.find_all('a','title')
        verified_key = rank_list_obj.find('input', attrs={'name': 'tt'})['value']
        for link in links:
            self.prepare_url.add(self.site_def['front-url'] + link['href'])
        for page in range(2, self.max_page):
            self.next_pages_url.append(self.site_def['ranking-url'].format(self.rank, str(page), verified_key))

    def parse_json(self, pages_url):
        next_pages_info = self.session.get(pages_url)
        next_pages_json = json.loads(next_pages_info.text)
        for next_url in next_pages_json.get('contents'):
            self.prepare_url.add(self.detail_url + str(next_url.get('illust_id')))

    def on_spider(self, page_url):
        self.start_headers['Referer'] = self.begin_url
        self.session.headers = self.start_headers
        detail_info = self.session.get(page_url)
        detail_infoObj = BeautifulSoup(detail_info.content, 'lxml')
        check_url = detail_infoObj.find('img', 'original-image')
        if check_url != None:
            download_url = detail_infoObj.find('img', 'original-image')['data-src']
            self.origin_url[download_url] = page_url
        elif check_url == None:
            self.multipic_url.add(page_url)


    def parse_multipic(self, page_url):
        self.start_headers['Referer'] = self.begin_url
        self.session.headers = self.start_headers
        detail_info = self.session.get(page_url)
        detail_infoObj = BeautifulSoup(detail_info.content, 'lxml')
        really_url = self.multi_front_url + detail_infoObj.find('a', 'read-more js-click-trackable')['href']

        self.start_headers['Referer'] = page_url
        self.session.headers = self.start_headers
        multipic_detail_info = self.session.get(really_url)
        multipic_detail_infoObj = BeautifulSoup(multipic_detail_info.content, 'lxml')
        self.really_multipic_url[really_url] = []
        multipicUrlList = multipic_detail_infoObj.find_all('img', 'image')
        for multipicUrl in multipicUrlList:
            self.really_multipic_url[really_url].append(
                multipicUrl['data-src'])

    def download_pic(self, download_link, page_url, file_path = f'Picture/{setRankList}/{setDate}'):
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        file_format = os.path.splitext(download_link)[1]
        file_name = re.findall(r'\d{7,10}', page_url)[0]
        file_all_name = file_name + file_format
        file_final_name = os.path.join(file_path, file_all_name)
        self.start_headers['Referer'] = page_url
        self.session.headers = self.start_headers
        try:
            download_pic = self.session.get(download_link)
            with open(file_final_name, 'wb') as f:
                f.write(download_pic.content)
        except Exception as e:
            print('Download Error!', e)

    def download_multipic(self, download_link, page_url , file_path = f'Picture/multipic/{setRankList}/{setDate}'):
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        file_format = os.path.splitext(download_link)[1]
        file_name = re.findall(r'\d{7,10}_\w\d{1,2}', download_link)[0]
        file_all_name = file_name + file_format
        file_final_name = os.path.join(file_path, file_all_name)
        self.start_headers['Referer'] = page_url
        self.session.headers = self.start_headers
        try:
            download_pic = self.session.get(download_link)
            with open(file_final_name, 'wb') as f:
                f.write(download_pic.content)
        except Exception as e:
            print('Download Error!', e)


    def main(self, multi=False):
        count = 0
        multi_count = 0

        self.start_spider()

        for next_page in self.next_pages_url:
            self.parse_json(next_page)

        for url in self.prepare_url:
            self.on_spider(url)

        for downloadUrl, pageUrl in self.origin_url.items():
            count += 1
            self.download_pic(downloadUrl, pageUrl)
            logger.info(f'downloading {count} pictures')

        if multi:
            for multiUrl in self.multipic_url:
                self.parse_multipic(multiUrl)

            for page_url, multipic_urlList in self.really_multipic_url.items():
                for multipicUrl in multipic_urlList:
                    multi_count += 1
                    self.download_multipic(multipicUrl, page_url)
                    logger.info(f'downloading {multi_count} manga')

        logger.info(f'downloaded {count} pictures,{multi_count} manga')


class OpenClipartSpider(Spider):
    """

    """
    def __init__(self, site_def: dict):
        super().__init__()

        self.session.headers = site_def['headers']
        self.session.cookies = cookiejar.LWPCookieJar(site_def['cookie-file'])

        self.params = site_def['params']
        self.data = site_def['data']
        self.site_def = site_def


def get_spider(conf: Configuration, site: str) -> Spider:
    """
    Return the appropriate spider for the site.
    :param conf: the Configuration object
    :param site: the slug name of the site
    :return: an instance of the appropriate spider, or None
    """
    site_def = conf.get_site(site)  # don't handle the exception, let it propagate
    if site == 'pixiv':
        return PixivSpider(site_def)
    elif site == 'openclipart':
        return OpenClipartSpider(site_def)
    else:
        raise ScraperException('get_spider', 'No spider for site {}'.format(site))