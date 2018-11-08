import pymysql
import jieba
import re
from gensim.models import word2vec, Word2Vec
from CSDN_SearchEngine.settings import BASE_DIR
from .DBsettings import *

def get_dbtext(db):
    cursor = db.cursor()
    sql = "select title from search_engine_csdnblog"

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

def write_file():
    db = pymysql.connect(host,user,password,dbname)
    result = get_dbtext(db)
    with open('text.txt', 'wb') as f:
        for r in result:
            f.write(r[0].encode('utf-8'))

def cut_words():
    with open('text.txt', 'r', encoding='utf-8') as content:
        for line in content:
            # new_line = re.sub("[\s+\.\!\/_,$%^*(\"\']+|[+——！，。？、~@#￥%……&*（）,._，。/]+", "",line)
            seg_list = jieba.cut(line)
            with open('seg_text.txt', 'a', encoding='utf-8') as output:
                output.write(' '.join(seg_list))

def train():
    num_features = 300  # Word vector dimensionality
    min_word_count = 10  # Minimum word count
    num_workers = 16  # Number of threads to run in parallel
    context = 10  # Context window size
    downsampling = 1e-3  # Downsample setting for frequent words
    sentences = word2vec.Text8Corpus("seg_text.txt")

    model = word2vec.Word2Vec(sentences, workers=num_workers,
                              size=num_features, min_count=min_word_count,
                              window=context, sg=1, sample=downsampling)
    model.init_sims(replace=True)
    # 保存模型，供日后使用
    model.save("model")


if __name__ == '__main__':
    write_file()
    cut_words()
    train()
    model = Word2Vec.load('model')
    s = model.most_similar(['python','入门'],topn=10)  # 根据给定的条件推断相似词
    query = '将html模板文件 放在templates文件夹中'
    seg_list = []
    for s in query.split(' '):
        seg_list += jieba.cut(s)
    print(seg_list)

