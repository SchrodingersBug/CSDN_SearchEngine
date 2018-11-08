from __future__ import unicode_literals
import sys
# sys.path.append("../")
import os
from whoosh.index import create_in,open_dir
from whoosh.fields import *
from whoosh.qparser import QueryParser
from whoosh import scoring
from whoosh.qparser import MultifieldParser
from jieba.analyse.analyzer import ChineseAnalyzer
import pymysql
import datetime
from CSDN_SearchEngine.settings import BASE_DIR
from .DBsettings import *

def get_dbtext(db):
    cursor = db.cursor()
    sql = "select * from crawler_csdnblog"

    try:
        cursor.execute(sql)
        result = cursor.fetchall()
        if result is None:
            print('not found')
            return ' '
        else:
            return result
    except:
        db.rollback()
        print('查询失败')
    cursor.close()


# 定义索引模式
class whoosh_text():
    def __init__(self):
        self.schema= Schema(url=ID(stored=True), title=TEXT(stored=True),
                        nickname=TEXT(stored=True), readcount=TEXT(stored=True)
                        , text=TEXT(stored=True, analyzer=ChineseAnalyzer()), time=DATETIME(stored=True))


    # 创建索引
    def create_ix(self):
        analyzer = ChineseAnalyzer()
        schema = self.schema
        # 创建索引存储目录
        if not os.path.exists("index"):
            os.mkdir("index")
        # 创建新索引
        ix = create_in("index", schema, 'my_index')
        # 从数据库中取数据
        db = pymysql.connect(host, user, password, dbname)
        content = get_dbtext(db)
        # 新建writer
        writer = ix.writer()
        # 遍历数据库, 插入doc
        count = 0
        for blog in content:
            writer.add_document(url=u'%s' % blog[1], title=u'%s' % blog[2], nickname=u'%s' % blog[3],
                                readcount=u'%s' % blog[4], text=u'%s' % blog[5], time=u'%s' % blog[6])
            count += 1
            print('第', count, '篇blog添加成功...')
        writer.commit()

    def create_searcher(self):
        # 建立搜索对象
        ixr = open_dir(BASE_DIR + "\search_engine\index", 'my_indexing')
        # with ixr.searcher(weighting=scoring.BM25F()) as searcher:
        self.searcher = ixr.searcher(weighting=scoring.BM25F()) # 没有close，可能会内存泄露，记得关服务器。
        # 建立解析器(使用多字段查询解析器)
        self.parser = MultifieldParser(['title', 'text'], schema=self.schema)


    # 按照索引查询
    def search_document(self,query,limit_=10000):
        searcher = self.searcher
        parser = self.parser
        q = parser.parse(query)
        results = searcher.search(q,limit=limit_)
        # print(len(results))
        # if results is not None:
        #     for hit in results:
        #         print(hit['url'],hit.score,hit['title'])
        # else:
        #     print('未查询到结果')
        return results


if __name__ == '__main__':
    index = whoosh_text()
    # index.search_document()
    # index.create_ix()
    index.create_searcher()

    while(1):
        print('Please input the query:')
        query = input()
        time1 = datetime.datetime.now()
        results = index.search_document(query)
        time2 = datetime.datetime.now()

        # print(results[0]['url'],results[0].highlights('text'))
        if results is not None:
            for hit in results:
                # print(hit)
                print(hit['url'],hit.score,hit.highlights('text'))
            else:
                print('未查询到结果')
        print(time2-time1)






