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


logger = logging.getLogger('scr')


class Spider:
    session: requests.Session

    def __init__(self):
        self.session = requests.session()

    def check_page(self, url):
        """
        Check if an url is available
        :param url: the url to check.
        :return: the HTTP status code
        """
        return self.session.get(url, allow_redirects=False).status_code


class PixivSpider(Spider):
    post_url = 'https://accounts.pixiv.net/login?lang=zh&source=pc&view_type=page&ref=wwwtop_accounts_index'

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                             '(KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36',
               'Referer': 'https://www.pixiv.net/'}

    start_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                                   '(KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36',
                     'Referer': ''}

    front_url = 'https://www.pixiv.net/'
    multi_front_url = 'https://www.pixiv.net'
    detail_url = 'https://www.pixiv.net/member_illust.php?mode=medium&illust_id='

    setDate = input('Enter date,format is YYYYMMDD, such as 20180101,last day is yesterday\n')
    setList = input('Enter list you want to crawl:0.daily  1.weekly  2.monthly  3.male\n')
    setMaxPage = input('Enter crawl page, max page is 10\n')

    rankList = ['daily', 'weekly', 'monthly', 'male'] 
    referInfo = ['day', 'week', 'month', 'male']
    setRankList = rankList[int(setList)] 
    setRef = referInfo[int(setList)] 

    listDate = f'&date={setDate}'
    begin_url = f'https://www.pixiv.net/ranking.php?mode={setRankList}&ref=rn-h-{setRef}-3' + listDate

    prepare_url = set()
    multipic_url = set()
    next_pages_url = []
    origin_url = {}
    really_multipic_url = {}

    def __init__(self, site_def: dict):
        self.site_def = site_def
        super().__init__()
        self.headers = Pixiv.headers
        self.session.headers = self.headers
        self.session.cookies = cookiejar.LWPCookieJar(filename = 'pixiv_cookies')
        try:
            self.session.cookies.load(filename = 'pixiv_cookies', ignore_discard = True)
            print('Load cookies successfully')
        except Exception as e:
            print('Can not load cookies')

        self.params = {
            'lang':'en',
            'source':'pc',
            'view_type':'page',
            'ref':'wwwtop_accounts_index'
        }

        self.datas = {
            'pixiv_id': '',
            'password': '',
            'captcha': '',
            'g_recaptcha_response': '',
            'post_key': '',
            'source': 'pc',
            'ref': 'wwwtop_accounts_index',
            'return_to': 'http://www.pixiv.net/',
        }

    def get_postkey(self):
        r = self.session.get(Pixiv.post_url, params = self.params)
        soup = BeautifulSoup(r.content, 'lxml')
        post_key = soup.find_all('input')[0]['value']
        self.datas['post_key'] = post_key

    def check_login(self):
        """
        Test if we're logged in.
        :return: True or false
        """
        return self.check_page(self.site_def['url']['user-settings']) == HTTPStatus.OK

    def login(self, username, password):
        self.get_postkey()
        self.datas['pixiv_id'] = username
        self.datas['password'] = password
        post_data = self.session.post(Pixiv.post_url, data = self.datas)
        self.session.cookies.save(ignore_discard = True, ignore_expires = True)

    def start_spider(self, start_url, maxPage): 
        Pixiv.start_headers['Referer'] = 'https://www.pixiv.net'
        self.session.headers = Pixiv.start_headers
        rankListInfo = self.session.get(start_url)
        rankListObj = BeautifulSoup(rankListInfo.content, 'lxml')
        links = rankListObj.find_all('a','title')
        verified_key = rankListObj.find('input', attrs={'name':'tt'})['value']
        for link in links:
            Pixiv.prepare_url.add(Pixiv.front_url + link['href'])
        for page in range(2, maxPage): 
            Pixiv.next_pages_url.append(
                f'https://www.pixiv.net/ranking.php?mode={Pixiv.setRankList}&p={str(page)}&format=json&tt={verified_key}')

    def parse_json(self, pages_url):
        next_pages_info = self.session.get(pages_url)
        next_pages_json = json.loads(next_pages_info.text)
        for next_url in next_pages_json.get('contents'):
            Pixiv.prepare_url.add(Pixiv.detail_url + str(next_url.get('illust_id')))

    def on_spider(self, page_url):
        Pixiv.start_headers['Referer'] = Pixiv.begin_url
        self.session.headers = Pixiv.start_headers
        detail_info = self.session.get(page_url)
        detail_infoObj = BeautifulSoup(detail_info.content, 'lxml')
        check_url = detail_infoObj.find('img', 'original-image')
        if check_url != None:
            download_url = detail_infoObj.find('img', 'original-image')['data-src']
            Pixiv.origin_url[download_url] = page_url
        elif check_url == None:
            Pixiv.multipic_url.add(page_url)


    def parse_multipic(self, page_url):
        Pixiv.start_headers['Referer'] = Pixiv.begin_url
        self.session.headers = Pixiv.start_headers
        detail_info = self.session.get(page_url)
        detail_infoObj = BeautifulSoup(detail_info.content, 'lxml')
        really_url = Pixiv.multi_front_url + detail_infoObj.find('a', 'read-more js-click-trackable')['href']

        Pixiv.start_headers['Referer'] = page_url
        self.session.headers = Pixiv.start_headers
        multipic_detail_info = self.session.get(really_url)
        multipic_detail_infoObj = BeautifulSoup(multipic_detail_info.content, 'lxml')
        Pixiv.really_multipic_url[really_url] = []
        multipicUrlList = multipic_detail_infoObj.find_all('img', 'image')
        for multipicUrl in multipicUrlList:
            Pixiv.really_multipic_url[really_url].append(
                multipicUrl['data-src'])

    def download_pic(self, download_link, page_url, file_path = f'Picture/{setRankList}/{setDate}'):
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        file_format = os.path.splitext(download_link)[1]
        file_name = re.findall(r'\d{7,10}', page_url)[0]
        file_all_name = file_name + file_format
        file_final_name = os.path.join(file_path, file_all_name)
        Pixiv.start_headers['Referer'] = page_url
        self.session.headers = Pixiv.start_headers
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
        Pixiv.start_headers['Referer'] = page_url
        self.session.headers = Pixiv.start_headers
        try:
            download_pic = self.session.get(download_link)
            with open(file_final_name, 'wb') as f:
                f.write(download_pic.content)
        except Exception as e:
            print('Download Error!', e)


def main(multi=False):
    count = 0
    multi_count = 0
    spider = Pixiv()
    if spider.check_login():
        print('logged in')
    else:
        username = input('Enter your username\n')
        password = input('Enter your password\n')
        spider.login_in(username, password)
        print('logged in')

    spider.start_spider(Pixiv.begin_url, int(Pixiv.setMaxPage) + 1)

    for next_page in Pixiv.next_pages_url:
        spider.parse_json(next_page)

    for url in Pixiv.prepare_url:
        spider.on_spider(url)

    for downloadUrl, pageUrl in Pixiv.origin_url.items():
        count += 1
        spider.download_pic(downloadUrl, pageUrl)
        print(f'downloading {count} pictures')

    if multi:
        for multiUrl in Pixiv.multipic_url:
            spider.parse_multipic(multiUrl)

        for page_url, multipic_urlList in Pixiv.really_multipic_url.items():
            for multipicUrl in multipic_urlList:
                multi_count += 1
                spider.download_multipic(multipicUrl, page_url)
                print(f'downloading {multi_count} manga')


    print(f'downloaded {count} pictures,{multi_count} manga')


if __name__ == '__main__':
    main()
