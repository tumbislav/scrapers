# coding: utf-8

"""
File: main.py

Main driver file of the scrapers package.
"""
__author__ = 'Marko Čibej'


import argparse
import os
import logging
import time
from config import Configuration
from spiders import PixivSpider
from helper import SimpleCrypt


logger = logging.getLogger('scr')


def parse_args():
    """
    Parse the command line arguments.

    :return: ArgumentParser object containing the command line values
    """
    parser = argparse.ArgumentParser(description='Retrieve a set of resources from the web')
    parser.add_argument('-c', '--config', help='the name of the configuration file', default='config.yaml')
    parser.add_argument('-v', '--verbosity', help='increase output verbosity', action='count', default=1)
    parser.add_argument('-l', '--log', help='the name of the log file', default='output.log')
    parser.add_argument('-g', '--log-verbosity', help='increase verbosity of file log', action='count', default=1)
    parser.add_argument('-w', '--working-dir', help='the path to the working directory', default=os.getcwd())
    return parser.parse_args()



def set_logging(working_dir, args: argparse.Namespace):
    """
    Set up the two loggers. The main log is used to track programm execution messages. The edits log is
    where all the changes made to input data are recorded.

    :param args: the arguments from the command line
    :param working_dir: path to the log file
    """
    log_levels = (logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)

    # we always write at least WARNINGs to file; console output by default is ERROR
    # edits records are always INFO
    max_verbosity = min(max(args.verbosity, args.log_verbosity, 4 if args.edits is not None else 0), len(log_levels))
    logger.setLevel(log_levels[max_verbosity-1])

    # set up the file output
    lf = logging.FileHandler(os.path.join(working_dir, args.log), mode='w', encoding='utf_8')
    lf.setLevel(log_levels[min(args.log_verbosity, len(log_levels)-1)])
    lf.setFormatter(logging.Formatter('{levelname}:{funcName} {message}', style='{'))
    logger.addHandler(lf)

    # and the console output
    lc = logging.StreamHandler()
    lc.setLevel(log_levels[min(args.verbosity, len(log_levels)-1)])
    lc.setFormatter(logging.Formatter('{levelname}:{funcName} {message}', style='{'))
    logger.addHandler(lc)


def start():
    """
    This function is the starting point of the package. Start by setting up the environment,
    initialize the appropriate spider and target, then download a set of resources.
    """
    args = parse_args()
    set_logging(os.getcwd(), args)
    config = Configuration(args.config)
    config.set_global('working-dir', args.working_dir)
    start_time = time.time()

    site_name = 'pixiv'
    spider = PixivSpider(config.get_site(site_name))

    if not spider.check_login():
        master_password = input('Enter master password\n')
        spider.login(SimpleCrypt(master_password))
    else:
        logger.info(f'already logged into site {site_name}')

    logger.info(time.strftime('finished in %H:%M:%S', time.gmtime(time.time() - start_time)))



    count = 0
    multi_count = 0
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




