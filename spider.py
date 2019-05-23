import redis
import time
import asyncio
import aiohttp
import csv
import json
import requests
from pyquery import PyQuery as pq
from random import choice
from flask import Flask, g
from multiprocessing import Process
from settings import *

class RedisClient(object):
    __instance = None

    def __new__(cls, *args, **kwargs):

        if not cls.__instance:
            obj = object.__new__(cls, *args, **kwargs)
            cls.__instance = obj
        return cls.__instance

    def __init__(self, host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD):
        """
            初始化
        """
        pool = redis.ConnectionPool(host=host, port=port)
        self.db = redis.StrictRedis(
            connection_pool=pool, decode_responses=True)

    def add(self, proxy, score=INITIAL_SCORE):
        """
        添加代理，设置分数为最高
        :param proxy:代理
        :param score:分数
        :return:添加结果
        """
        if not self.db.zscore(REDIS_KEY, proxy):
            return self.db.zadd(REDIS_KEY, {proxy: score})

    def random(self):
        """
        随机获取有效代理，首先尝试获取最高分数代理，如果最高分数不存在，则按照排名获取，否则异常
        :return :随机代理
        """
        result = self.db.zrangebyscore(REDIS_KEY, MAX_SCORE, MAX_SCORE)
        if len(result):
            return choice(result)
        else:
            result = self.db.zrevrange(REDIS_KEY, 0, 100)
            if len(result):
                return choice(result)
            else:
                raise PoolEmptyError

    def decrease(self, proxy):
        """
        代理值减一分，分数小于最小值，则代理删除
        :param proxy:代理
        :return:修改后的代理分数
        """
        score = self.db.zscore(REDIS_KEY, proxy)
        if score and score > MIN_SCORE:
            print("代理", proxy, "当前分数", score, "减一")
            return self.db.zincrby(REDIS_KEY, -1, proxy)
        else:
            print("代理", proxy, "当前分数", score, "移除")
            return self.db.zrem(REDIS_KEY, proxy)

    def exists(self, proxy):
        """
        判断是否存在
        :param proxy:代理
        :return: 是否存在
        """
        return not self.db.zscore(REDIS_KEY, proxy) == None

    def max(self, proxy):
        """
        将代理设置为MAX_SCORE
        :param proxy:代理
        :return:设置结果
        """
        print("代理", proxy, "可用", '设置为', MAX_SCORE)
        return self.db.zadd(REDIS_KEY, {proxy: MAX_SCORE})

    def count(self):
        """
        获取数量
        :return :数量
        """
        return self.db.zcard(REDIS_KEY)

    def all(self):
        """
        获取全部代理
        ：return :全部代理列表

        """
        return self.db.zrangebyscore(REDIS_KEY, MIN_SCORE, MAX_SCORE)


class ProxyMetaclass(type):
    def __new__(cls, name, bases, attrs):
        count = 0
        attrs["__CrawlFunc__"] = []
        for k, v in attrs.items():
            if 'crawl_' in k:
                attrs["__CrawlFunc__"].append(k)
                count += 1
        attrs["__CrawlFuncCount__"] = count
        return type.__new__(cls, name, bases, attrs)


class Crawler(object, metaclass=ProxyMetaclass):
    def get_proxies(self, callback):
        proxies = []
        for proxy in eval("self.{}()".format(callback)):
            print("成功获取到代理", proxy)
            proxies.append(proxy)
        return proxies

    def crawl_kuaidaili(self, page_count=200):
        start_url = "https://www.kuaidaili.com/free/inha/{}/"
        urls = [start_url.format(page) for page in range(1, page_count+1)]
        for url in urls:
            print("Crawling", url)
            html = requests.get(url).text
            if html:
                doc = pq(html)
                trs = doc("table tr:gt(0)").items()
                for tr in trs:
                    ip = tr.find("td:nth-child(1)").text()
                    port = tr.find("td:nth-child(2)").text()
                    yield ":".join([ip, port])

    def crawl_daili66(self, page_count=10):
        start_url = "http://www.66ip.cn/{}.html"
        urls = [start_url.format(page) for page in range(1, page_count+1)]
        for url in urls:
            print("Crawling", url)
            html = requests.get(url).text
            if html:
                doc = pq(html)
                trs = doc(".containerbox table tr:gt(0)").items()
                for tr in trs:
                    ip = tr.find("td:nth-child(1)").text()
                    port = tr.find("td:nth-child(2)").text()
                    yield ":".join([ip, port])

    def crawl_xiladaili(self, page_count=100):
        start_url = "http://www.xiladaili.com/http/{}/"
        urls = [start_url.format(page) for page in range(1, page_count+1)]
        for url in urls:
            print("Crawling", url)
            html = requests.get(url).text
            if html:
                doc = pq(html)
                trs = doc("table  tr:gt(0)").items()
                for tr in trs:
                    ip = tr.find("td:nth-child(1)").text()
                    print(ip)
                    yield ip


class Getter():
    def __init__(self):
        self.redis = RedisClient()
        self.crawler = Crawler()

    def is_over_threshold(self):
        """
        判断是否达到了代理池限制
        """
        if self.redis.count() >= POOL_UPPER_THRESHOLD:
            return True
        else:
            return False

    def run(self):
        print("获取器开始执行")
        if not self.is_over_threshold():
            for callback_label in range(self.crawler.__CrawlFuncCount__):
                callback = self.crawler.__CrawlFunc__[callback_label]
                proxies = self.crawler.get_proxies(callback)
                for proxy in proxies:
                    self.redis.add(proxy)


class Tester(object):
    def __init__(self):
        self.redis = RedisClient()

    async def test_single_proxy(self, proxy):
        """
        测试单个代理
        :param proxy:单个代理
        :return:None 

        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36"
        }
        conn = aiohttp.TCPConnector(verify_ssl=False)
        async with aiohttp.ClientSession(connector=conn) as session:
            try:
                if isinstance(proxy, bytes):
                    proxy = proxy.decode("utf-8")
                real_proxy = "http://" + proxy
                print("正在测试", proxy)
                async with session.get(TEST_URL, proxy=real_proxy, headers=headers, timeout=5) as response:
                    if response.status in VALID_STATUS_CODES:
                        self.redis.max(proxy)
                        print("代理可用", proxy)
                    else:
                        self.redis.decrease(proxy)
                        print("请求响应码不合法", proxy)
            except Exception as e:
                print(e.args)
                self.redis.decrease(proxy)
                print("代理请求失败", proxy)

    def run(self):
        print("测试器开始运行")
        try:
            proxies = self.redis.all()
            loop = asyncio.get_event_loop()
            # 批量测试
            for i in range(0, len(proxies), BATCH_TEST_SIZE):
                test_proxies = proxies[i:i+BATCH_TEST_SIZE]
                tasks = [self.test_single_proxy(proxy)
                         for proxy in test_proxies]
                loop.run_until_complete(asyncio.wait(tasks))
                # time.sleep(5)
        except Exception as e:
            print("测试器发生错误", e.args)


__all__ = ['app']
app = Flask(__name__)


def get_conn():
    if not hasattr(g, 'redis'):
        g.redis = RedisClient()
    return g.redis


@app.route("/")
def index():
    return "<h2>Welcome to Proxy Pool Systen</h2>"


@app.route("/random")
def get_proxy():
    """
    获取随机可用代理
    :return 随机代理
    """
    conn = get_conn()
    return conn.random()


@app.route("/count")
def get_counts():
    """
    获取代理池总量
    :return 代理池总量
    """
    conn = get_conn()
    return str(conn.count())


class Scheduler():
    def schedule_tester(self, cycle=TESTER_CYCLE):
        """
        定时测试代理

        """
        tester = Tester()
        while True:
            print("测试器开始运行")
            tester.run()
            time.sleep(cycle)

    def schedule_getter(self, cycle=GETTER_CYCLE):
        """
        定时获取代理
        """
        getter = Getter()
        while True:
            print("开始抓取代理")
            getter.run()
            time.sleep(cycle)

    def schedule_api(self):
        """
        开启api
        """
        app.run(API_HOST, API_PORT)

    def run(self):
        print("代理池开始运行")
        if TESTER_ENABLED:
            tester_process = Process(target=self.schedule_tester)
            tester_process.start()
        if GETTER_ENABLED:
            getter_process = Process(target=self.schedule_getter)
            getter_process.start()
        if API_ENABLED:
            api_process = Process(target=self.schedule_api)
            api_process.start()


Scheduler().run()
