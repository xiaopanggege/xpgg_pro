# 并行工作进程数
workers = 2

# 指定每个工作者的线程数
threads = 2

# 监听内网端口8005
bind = '0.0.0.0:8005'

# 设置守护进程(linux有效)
daemon = 'false'

# 设置进程文件目录
pidfile = '/var/run/gunicorn.pid'

# 工作模式协程
worker_class = 'gevent'

# 代码变更自动重启项目,生产环境最好是false禁用
reload = 'true'

# 设置最大并发量
worker_connections = 2000

# 设置访问日志和错误信息日志路径
accesslog = 'logs/gunicorn_access.log'
errorlog = 'logs/gunicorn_error.log'
# 日志格式 添加真实ip获取
access_log_format = '"%({X-Forwarded-For}i)s" %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# 设置日志记录水平
loglevel = 'info'