# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
import requests
import threading
import pymysql
import re
import urllib
import urllib.request
from selenium import webdriver
import time
import pickle
from .DBsettings import *

session = requests.Session()

# 模拟登陆
def loginPages():
    url = "https://passport.csdn.net/account/login"
    driver = webdriver.Chrome(executable_path='/home/qb-linux/chromedriver')
            # 要加chromedriver绝对路径 or 把chromedriver加到系统PATH里
    driver.get(url)
    switch = driver.find_element_by_xpath(
        '//a[@class="login-code__open js_login_trigger login-user__active"]')
    if switch.text == '账号登录':
        switch.click()
        time.sleep(1)


    username = driver.find_element_by_id('username')
    password = driver.find_element_by_id('password')
    username.send_keys("username")
    password.send_keys("password")
    click = driver.find_element_by_class_name("logging")
    click.click()
    time.sleep(1)

    cookies = driver.get_cookies()

    # driver.page_source ->get html
    # 将selenium形式的cookies转换为requests可用的cookies!!
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])

    return cookies

    # CSDN登录默认二维码登录,需要点击账号登录才可以. 下面方法没有点击.
    # html = session.get(url,headers=headers).text
    #
    # bs = BeautifulSoup(html,"lxml")
    # #获取lt值
    # lt = bs.find("input",attrs={"name":"lt"}).get("value")
    # print(lt)
    # #获取execution值
    # ex = bs.find("input",attrs={"name":"execution"}).get("value")
    # print(ex)
    #
    # #创建data表单数据
    # data = {
    #     "username":" ",
    #     "password":" ",
    #     "lt": lt,
    #     "execution" : ex,
    #     "_eventId":"submit",
    # }
    # #获取登录cookie值
    # session.post(url,data=data,headers=headers)
    # # 获取登录后页面
    # response = session.get("http://write.blog.csdn.net/postlist",headers=headers).text


class Page():
    def __init__(self,url):
        self.url = url
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
        }

        html = session.get(url,headers = headers).text
        bsobj = BeautifulSoup(html, "lxml")
        self.bsobj = bsobj

    def get_url(self):
        return self.url

    def get_title(self):
        title = self.bsobj.find_all('h1',class_='title-article')[0].text
        return title

    def get_writer(self):
        writer = self.bsobj.find('a',class_='follow-nickName').text
        return writer

    def get_writerId(self):
        writer_id = self.url.split('/')[-4]
        return writer_id

    def get_readCount(self):
        s = self.bsobj.find('span',class_='read-count').text
        count = s.split('：')[-1]
        count = int(count)
        return count

    def get_date(self):
        time = self.bsobj.find_all('span',class_='time')[0].text
        time = time.split('日')[0]
        time = time.replace('年','-')
        time = time.replace('月', '-')
        return time

    def get_content(self):
        article = self.bsobj.find_all('div', class_='article_content clearfix csdn-tracking-statistics')
        a_bf = BeautifulSoup(str(article[0]),"lxml")
        p = a_bf.find_all({'p', 'h1', 'h2', 'h3', 'h4','br'})
        content = ""
        for text in p:
            content = content + '\n' + text.text
        return content.encode('utf-8')

    def get_blogURLs(self):
        urls_bs = self.bsobj.find_all('a',
                href=re.compile("^(https://blog.csdn.net/).*\/article\/details\/[0-9]+$"))
        urls = []
        for link in urls_bs:
            urls.append(link.attrs['href'])
        return urls

    def get_data(self):
        url = self.get_url()
        title = self.get_title()
        writer = self.get_writer()
        read_count = self.get_readCount()
        content = self.get_content()
        date = self.get_date()
        writer_id = self.get_writerId()

        data = {}
        data['url'] = url
        data['title'] = title
        data['writer'] = writer
        data['read_count'] = read_count
        data['content'] = content
        data['date'] = date
        data['writer_id'] = writer_id
        return data


class CSDN_Spider(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        db = pymysql.connect(host, user, password, dbname)
        cur = conn.cursor()
        cur.execute("USE csdn_crawler")
        self.conn = conn
        self.cur = cur
        self.lock = threading.Lock()

    def get_nextURL(self):
        # self.lock.acquire()
        self.cur.execute("select url from url_queue")
        url = self.cur.fetchone()[0]
        return url

    def remove(self,url):
        # print('remove' + url)
        self.cur.execute("Delete from url_queue where url= %s",url)
        self.cur.execute("Insert into visited values (%s)",url)
        # print('remove ' + url)
        self.cur.connection.commit()


    def add_queue(self,url):

        self.cur.execute("Select url from visited where url= %s",url)
        t = self.cur.fetchall()
        self.cur.connection.commit()
        self.cur.execute("Select url from url_queue where url= %s",url)
        n = self.cur.fetchall()
        self.cur.connection.commit()
        # print(t,len(t))

        if(len(t) == 0 and len(n) == 0):
            # print('insert' + url)
            self.cur.execute("Insert into url_queue VALUES (%s)",url)
            self.cur.connection.commit()


    def save_data(self,data):
        url = data['url']
        title = data['title']
        writer = data['writer']
        writer_id = data['writer_id']
        read_count = data['read_count']
        date = data['date']
        content = data['content']

        self.cur.execute("Insert into crawler_csdnblog(url, title, writer, " +
                         "read_count, content, date, writer_id) Values (%s,%s,%s,%s,%s,%s,%s)",
                         (url,title,writer,read_count,content,date,writer_id))
        self.cur.connection.commit()

    def run(self):
        while(True):
            try:
                self.lock.acquire()
                url = self.get_nextURL()
                page = Page(url)
                print('正在抓取' + url)
                data = page.get_data()
                self.save_data(data)
                self.remove(url)
                urls = page.get_blogURLs()
                # print(urls)
                for url in urls:
                    self.add_queue(url)

            except Exception as e:
                if hasattr(e, 'reason'):
                    print('reason:', e.reason)
                elif hasattr(e, 'code'):
                    print('error code:', e.code)
                else:
                    print(e)
                self.remove(self.get_nextURL())  # 暴力删除,可能会一直删完queue.
                continue
            finally:
                self.lock.release()


if __name__ == '__main__':

    # init queue from index
    # url = 'https://blog.csdn.net/'
    # page = Page(url)
    # urls = page.get_blogURLs()
    # s = CSDN_Spider()
    # for url in urls:
    #     print(url)
    #     s.add_queue(url)

    loginPages()

    spider = CSDN_Spider()
    spider.start()

