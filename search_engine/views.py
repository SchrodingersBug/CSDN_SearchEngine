import collections
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils import timezone

from CSDN_SearchEngine.settings import BASE_DIR
from .models import *
from search_engine.searcher import whoosh_text
import jieba
from gensim.models import Word2Vec

# Create your views here.

# 启动searcher
searcher = whoosh_text()
searcher.create_searcher()
searcher.search_document('test')

model = Word2Vec.load(BASE_DIR + '\data\word2Vec\model')

pop_query_num = 5  # 显示的热门搜索个数
content_per_page = 10

def index(req):
    if req.method == 'GET':
        pop_query = topQuery(pop_query_num)
        data = dict()
        data['pop_query'] = pop_query
        return render(req,'index.html',data)

def results(req):
    if req.method == 'GET':
        query = req.GET.get('q')
        order = req.GET.get('order')
        if query is None:
            return HttpResponseRedirect('/index/')
        if order is None:
            order = 'sim'
    else:
        query = req.POST['query']
        order = 'sim'

    # 把当前query存入数据库
    query1 = Query.objects.create(query=query,date=timezone.now())
    query1.save()

    data = dict()
    data['query'] = query
    pop_query = topQuery(pop_query_num)  # 热门搜索
    data['pop_query'] = pop_query
    results = searcher.search_document(query)

    # 分词, highlightWords：高亮词汇
    seg_list = jieba.cut(query)
    highlightWords = " ".join(seg_list)
    data['highlightWords'] = highlightWords

    # 相关搜索
    try:
        seg_list = []
        for s in query.split(' '):
            seg_list += jieba.cut(s)
        similar_query = model.most_similar(seg_list, topn=8)  # 根据给定的条件推断相似词

        similar_query1 = []
        similar_query2 = []
        for q in similar_query[:4]:
            similar_query1.append(q[0])
        for q in similar_query[4:8]:
            similar_query2.append(q[0])
        data['has_similar'] = True
        data['similar_query1'] = similar_query1  # 第一行
        data['similar_query2'] = similar_query2
    except:
        data['has_similar'] = False

    data['costTime'] = '%.3f' % results.runtime

    # 排序
    data['order'] = order
    order_num = 300
    if len(results) > order_num:
        results1 = results[:order_num]
        results2 = results[order_num:]
    else:
        results1 = results
        results2 = []

    if (order == 'time'):
        results = sorted(results1, key=lambda x: x['time'], reverse=True) + results2
    elif (order == 'readcount'):
        results = sorted(results1,
                    key=lambda x: (int)(x['readcount']), reverse=True) + results2

    # 分页
    paginator = Paginator(results, content_per_page)
    page = req.GET.get('page')
    if page is None:  # POST method
        page = 1

    left = 3  # 当前页码左边显示几个页码号 -1，比如3就显示2个
    right = 3
    try:
        currentPage = paginator.page(page)
        pages = get_left(currentPage.number, left, paginator.num_pages) \
                + get_right(currentPage.number, right, paginator.num_pages)
        # 调用了两个辅助函数，根据当前页得到了左右的页码号
    except PageNotAnInteger:
        currentPage = paginator.page(1)
        pages = get_right(currentPage.number, right, paginator.num_pages)
    except EmptyPage:
        currentPage = paginator.page(paginator.num_pages)
        pages = get_left(currentPage.number, left, paginator.num_pages)

    data['currentPage'] = currentPage  # 当前内容页
    data['number'] = len(results) # 总搜索结果数

    data['pages'] = pages
    data['first_page'] = 1
    data['last_page'] = paginator.num_pages
    try:
        # 获取 pages 列表第一个值和最后一个值，主要用于在是否该插入省略号的判断，在模板文件中将会体会到它的用处。
        # 注意这里可能产生异常，因为pages可能是一个空列表，
        # 比如本身只有一个分页，那么pages就为空，因为我们永远不会获取页码为1的页码号（至少有1页）
        data['pages_first'] = pages[0]
        data['pages_last'] = pages[-1] + 1
        # +1的原因是为了方便判断
    except IndexError:
        data['pages_first'] = 1  # 发生异常说明只有1页
        data['pages_last'] = 2

    results_copy = []
    for result in currentPage:
        res = dict()
        res['url'] = result['url']
        res['title'] = result['title']
        res['nickname'] = result['nickname']
        res['readcount'] = result['readcount']
        res['score'] = '%.2f' % result.score  # 两位小数
        res['text'] = result['text']
        res['time'] = result['time']
        url = result['url']
        writer_home = 'https://blog.csdn.net/' + url.split('/')[-4]
        res['writer_home'] = writer_home
        results_copy.append(res)
    data['results'] = results_copy
    # results_copy_x = sorted(results_copy,key=lambda x: (int)(x['readcount']),reverse=True)
    # print(res['readcount'] for res in results_copy_x)
    # if(order == 'sim'):
    #     data['results'] = results_copy
    # elif(order == 'time'):
    #     data['results'] = sorted(results_copy, key=lambda x: x['time'], reverse=True)
    # else:
    #     data['results'] = sorted(results_copy,key=lambda x: (int)(x['readcount']),reverse=True)

    return render(req, 'result.html', data)


def get_left(current_page, left, num_pages):
    """
    辅助函数，获取当前页码的值得左边两个页码值，
    要注意一些细节，比如不够两个那么最左取到2，为了方便处理，包含当前页码值，
    比如当前页码值为5，那么pages = [3,4,5]
    """
    if current_page == 1:
        return []
    elif current_page == num_pages:
        l = [i - 1 for i in range(current_page, current_page - left, -1) if i - 1 > 1]
        l.sort()
        return l
    l = [i for i in range(current_page, current_page - left, -1) if i > 1]
    l.sort()
    return l


def get_right(current_page, right, num_pages):
    """
    辅助函数，获取当前页码的值得右边两个页码值，要注意一些细节，比如不够两个那么最右取到最大页码值。
    不包含当前页码值。比如当前页码值为5，那么pages = [6,7]
    """
    if current_page == num_pages:
        return []
    return [i + 1 for i in range(current_page, current_page + right - 1)
            if i < num_pages - 1]


# 返回数据库中记录的查询搜索次数最多的n个
def topQuery(n):
    queries = Query.objects.all().values_list('query', flat=True)
    c = collections.Counter(queries).most_common(n)
    list = [i[0] for i in c]
    # print(list)
    return list
