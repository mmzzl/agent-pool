#最高分
MAX_SCORE = 100

#最低分
MIN_SCORE = 0

#初始分数
INITIAL_SCORE = 10

#redis连接设置
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_PASSWORD = None
REDIS_KEY = "proxies"

#代理池IP数量
POOL_UPPER_THRESHOLD = 10000

#请求状态
VALID_STATUS_CODES = [200]

#检测地址
TEST_URL = "http://www.yznnw.com/"

#每次检查IP的数量
BATCH_TEST_SIZE = 100

TESTER_CYCLE = 2
GETTER_CYCLE = 20

#启动开关设置
TESTER_ENABLED = True
GETTER_ENABLED = False
API_ENABLED = True

#flask接口地址
API_HOST = "127.0.0.1"
API_PORT = 5555
