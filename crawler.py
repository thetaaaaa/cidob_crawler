import logging
import os
import re

import pandas as pd
import requests
from lxml import html
from tqdm import tqdm, trange

logging.basicConfig(level=logging.INFO)
logging.StreamHandler()


class Crawler:
    def __init__(self, out_folder):
        self.header = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36"}
        # self.url = index_url
        # self.url_txt = url_txt
        # self.json_path = json_path
        self.out_folder = out_folder
        # self.xlsx_path = xlsx_path
        if not os.path.exists(self.out_folder):
            os.mkdir(self.out_folder)

    def get_maxpage(self):
        url = 'https://www.cidob.org/en/publications/search'
        r = requests.post(url,
                          headers=self.header,
                          data={'parameters[locationId]': '40870',
                                'parameters[filters][limit]': '10',
                                'parameters[filters][name]': '',
                                'parameters[page]': '1'})
        r.raise_for_status()
        maxpage = re.findall('<li class=""><a onclick="refreshResults\([0-9]+\)">([0-9]+) </a></li>', r.text)[3]
        logging.info('最大页数：{}'.format(maxpage))
        return int(maxpage)

    def get_lastpagenum(self):
        succeed_page_path = os.path.join(self.out_folder, 'succeed_pages.csv')
        if os.path.exists(succeed_page_path):
            last_page = pd.read_csv(succeed_page_path, index_col=[0]).values.tolist()[-1][0]
            logging.info('最后获得详情链接的页码：{}'.format(last_page))
            return int(last_page)
        else:
            return 0

    def get_urls(self):
        maxpage = self.get_maxpage()
        lastsucceedpage = self.get_lastpagenum()
        start_craw_page = 0.0
        if lastsucceedpage:
            start_craw_page = lastsucceedpage
        else:
            start_craw_page = maxpage

        url = 'https://www.cidob.org/en/publications/search'
        succeed_pages = []
        savepath4urls = os.path.join(self.out_folder, 'urls.csv')
        publication_urls = []

        for i in trange(int(start_craw_page), 0, -1):  # 逆向爬取
            try:
                r = requests.post(url,
                                  headers=self.header,
                                  data={'parameters[locationId]': '40870',
                                        'parameters[filters][limit]': '10',
                                        'parameters[filters][name]': '',
                                        'parameters[page]': '{}'.format(i)})
                r.raise_for_status()
                incomplete_publication_urls = re.findall(
                    '<a href="(/en/publications/publication_series.+)" title=".+">.+</a>',
                    r.text)
                publication_urls += ['https://www.cidob.org' + i for i in incomplete_publication_urls]
                pd.DataFrame(publication_urls, columns=['url']).to_csv(savepath4urls, sep='\t')
                succeed_pages.append(i)
                pd.DataFrame(succeed_pages, columns=['succeedpage_num']).to_csv(
                    os.path.join(self.out_folder, 'succeed_pages.csv'))
            except:
                pd.DataFrame(publication_urls, columns=['url']).to_csv(savepath4urls, sep='\t')

    def get_detail(self, urlsfilepath):
        htmlcachepath = os.path.join('cache', 'html')
        if not os.path.exists(htmlcachepath):
            os.makedirs(htmlcachepath)
        succeed_detailpageurlpath = os.path.join(self.out_folder, 'succeed_detail_url.csv')  # 已经被爬取过详情的url
        urls = pd.read_csv(urlsfilepath, sep='\t', index_col=[0]).values.tolist()
        logging.info('已获取的详情页url个数：{}'.format(len(urls)))
        if os.path.exists(succeed_detailpageurlpath):
            succeed_urls = pd.read_csv(succeed_detailpageurlpath, index_col=[0]).values.tolist()
            for i in succeed_urls:
                if i in urls:
                    urls.remove(i)
            logging.info('未获取详情的url个数：{}'.format(len(urls)))
        else:
            succeed_urls = []

        result = []
        for idx, i in tqdm(enumerate(urls)):
            try:
                r = requests.get(i[0], headers=self.header)
                r.raise_for_status()
                # 缓存网页
                with open(os.path.join(htmlcachepath, str(idx) + '.html'), 'w', encoding='utf-8') as hf:
                    hf.write(r.text)
                tree = html.fromstring(r.text)
                title = tree.xpath('/html/body/div[2]/div/div[1]/div/div/h1/text()')[0]  # 标题
                url = i[0]  # url
                content = ''  # 全文
                # 摘要
                # 正则方法
                # pattern = re.compile('<div class="ezxmltext-field"><p><strong>(.*?)<\/strong>')
                # summary = re.findall(pattern,r.text)
                # xpath方法
                summary = tree.xpath('/html//strong//text()')[0]
                author = tree.xpath('/html/body/div[2]/div/div[1]/div/div/dl/dd[2]/text()')[0]  # 作者
                time = tree.xpath('/html/body/div[2]/div/div[1]/div/div/dl/dd[1]/text()')[0]  # 发表时间
                resource = 'www.cidob.org'  # 来源智库
                pdf = 'https://www.cidob.org' + tree.xpath('/html/body/div[2]/div/div[1]/div/div/a/@href')[0]  # 附件
                result.append([title, url, content, summary, author, time, resource, pdf])
                pd.DataFrame(result,
                             columns=['title', 'url', 'content', 'summary', 'author', 'time', 'resource',
                                      'pdf']).to_csv(
                    os.path.join(self.out_folder, 'cidob.csv'), sep='\t')
                succeed_urls.append([url])
                pd.DataFrame(succeed_urls).to_csv(os.path.join(self.out_folder, 'succeed_detail_url.csv'))
                time.sleep(1)
            except:
                pd.DataFrame(result,
                             columns=['title', 'url', 'content', 'summary', 'author', 'time', 'resource',
                                      'pdf']).to_csv(
                    os.path.join(self.out_folder, 'cidob.csv'), sep='\t')


if __name__ == '__main__':
    cidobcrawler = Crawler(out_folder='cache')
    # 以下1和2函数可以分别运行。
    # cidobcrawler.get_urls()  # 1：获取全部智库报告页url
    cidobcrawler.get_detail('cache/urls.csv')  # 2：访问并解析获智库报告页url，提取目标数据
