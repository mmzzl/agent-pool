# agent-pool
# 代理池
# 代理池主要有抓取--存储--检测--接口等几个模块构成
RedisClient
redis 连接
```
pool = redis.ConnectionPool(host=host, port=port)
self.db = redis.StrictRedis(
connection_pool=pool, decode_responses=True)
```
add方法主要是把抓取到的代理添加到redis的集合里面，zscore(REDIS_KEY,proxy) 检测ip的分数是否为0
zdd(REDIS_KEY, {proxy: score}) 添加代理,并设置分数
zincrby(REDIS_KEY, -1, proxy) 代理值减一
zrem(REDIS_KEY, proxy) 移除代理
zcard(REDIS_KEY) 获取集合里面的数量
元类的编写
```
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
```
继承 type,第四个参数是属性attrs,可以添加对类属性，type.__new__(cls,name,bases,attrs)
使用定义的元类，添加metaclass
```
class Crawler(object, metaclass=ProxyMetaclass):
    def get_proxies(self, callback):
        proxies = []
        for proxy in eval("self.{}()".format(callback)):
            print("成功获取到代理", proxy)
            proxies.append(proxy)
        return proxies
    def crawl_test(self,page_count=None):
        pass
for callback_label in range(self.crawler.__CrawlFuncCount__):
                callback = self.crawler.__CrawlFunc__[callback_label]
                proxies = self.crawler.get_proxies(callback)
                for proxy in proxies:
                    self.redis.add(proxy)
```



