"""
Django settings for xpgg_pro project.

Generated by 'django-admin startproject' using Django 2.1.5.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os
import pymysql
from datetime import timedelta
pymysql.install_as_MySQLdb()
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '9qq==sbw+$ztjo#=@exop#o@q=lbeg02n@i40$*(%%m_1y4d$y'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# 全局配置
# salt-api地址
SITE_SALT_API_URL = 'http://172.16.0.7:8080'
# salt-api用户
SITE_SALT_API_NAME = 'saltapi'
# salt-api密码
SITE_SALT_API_PWD = '123456'
# salt-api的token
SITE_SALT_API_TOKEN = ''
# salt服务端安装的minion的id，服务端也要安装一下minion，有很多用到的时候
SITE_SALT_MASTER = '172.16.0.7-master'
# salt服务端IP，salt-ssh等调用
SITE_SALT_MASTER_IP = '172.16.0.7'
# web端宿主机的minion id
SITE_WEB_MINION = '172.16.0.7-master'
# rsync服务端的宿主机minion id，发布系统的检出文件存放在rsync服务器里，如rsync服务是在master机子上salt自带的同步才能用，为了
# 解耦发布系统取消salt同步只保留rsync同步
SITE_RSYNC_MINION = '172.16.0.7-master'
# 发布系统中随机生成svn/git目录的路径和名字前缀，这里是xiaopgg作为前缀嘿嘿
# 在views.py里后面加上当前时间来组成完整的目录路径，千万别出现中文因为py2版salt中文支持不好，出现中文后同步文件时目录可以同步文件不同步过去反而全被删除！！
SITE_BASE_CO_PATH = '/data/xpgg_co/xpgg'
# 在用salt同步文件过程中发如果salt的master配置文件中的file_roots定义的svn目录内文件太多会非常的慢
# 所以使用的软连接的方式同步完删除软连接来保持file_roots目录的整洁，这个目录要在master配置文件中也定义名称为xpgg指定目录和下面一样。弃用！！
SITE_BASE_CO_SYMLINK_PATH = '/data/xpgg_symlink/'
# 文件服务使用的临时目录
SITE_BASE_TMP_PATH = '/data/xpgg_tmp/'
# 文件服务器rsync的内网ip和端口
SITE_RSYNC_IP = '172.16.0.7'
SITE_RSYNC_PORT = '873'
# web服务器rsync的内网ip和端口,如果rsync服务器和web服务器不是同一台，则web服务器也需要开启rsync的daemon用来给文件服务的上传更新使用
SITE_WEB_RSYNC_IP = '172.16.0.7'
SITE_WEB_RSYNC_PORT = '873'


# celery调用参数设置
CELERY_BROKER_URL = 'redis://:123456@localhost:6379/0'  # 使用redis做为消息队列格式：redis://:password@hostname:port/db_number
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = 'Asia/Shanghai'
CELERY_RESULT_BACKEND = 'django-db'
# 每个进程执行10个任务就销毁，默认100个会导致内存泄漏听说
CELERYD_MAX_TASKS_PER_CHILD = 10
# 官方用来修复CELERY_ENABLE_UTC=False and USE_TZ = False 时时间比较错误的问题；
# 详情见：https://github.com/celery/django-celery-beat/pull/216/files
DJANGO_CELERY_BEAT_TZ_AWARE = False
# 使用django_celery_beat插件用来动态配置任务！其实我在启动的命令里也添加了
# CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
# 启动任务跟踪，加了这个admin后台的计划任务结果才会显示任务开始状态，不然只有等任务完成才显示成功或者失败
CELERY_TASK_TRACK_STARTED = True
# 任务结果存储的过期时间，默认是1天，改成0不删除，不然每天4点运行的celery.backend_cleanup任务会删除掉我的任务结果奶奶的，当然你也可也停止这个清理任务
# 后面发现还是停止清理任务靠谱点。。哈
CELERY_TASK_RESULT_EXPIRES = 0


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'xpgg_oms',
    'django_filters',
    'crispy_forms',
    'rest_framework',
    'corsheaders',  # 跨域白名单设置
    'drf_yasg',  # swagger
    'django_celery_results',
    'django_celery_beat',
    'django_cleanup.apps.CleanupConfig',  # 清理通过model上传的图片或者文件的旧文件，因为默认不会自动删除旧文件
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',  # csrf请求post的时候会报错，测试暂时先关闭
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ORIGIN_ALLOW_ALL = True

ROOT_URLCONF = 'xpgg_pro.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'xpgg_pro.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'xpgg_pro',    # 你的数据库名称
        'USER': 'xiaopgg',   # 你的数据库用户名
        'PASSWORD': '123456',  # 你的数据库密码
        'HOST': '',  # 你的数据库主机，留空默认为localhost
        'PORT': '3306',  # 你的数据库端口,

        'OPTIONS': {
        # 在mysql5.7以前需要加下面的来使得同步数据库时候不会出现严格模式的警告，5.7开始默认是严格模式了就可以省略
        #     'init_command': "SET sql_mode= 'STRICT_TRANS_TABLES'",
        # 如果InnoDB Strict Mode也是严格模式也需要加下面的
        #     'init_command': 'SET innodb_strict_mode=1',
        #     之前是通过utf8创建的数据库，所以下面的这个注释掉，如果用utf8mb4可以试着打开这个
        #     'charset': 'utf8mb4',
        },
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# rest freamework配置
REST_FRAMEWORK = {
    # 认证配置
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',

    ),
    # 全局权限设置IsAuthenticated为全局都必须登录才能访问，还有其他比如AllowAny就是不限制访问，http://drf.jiuyou.info详细介绍
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
        # 不限制访问用下面这个,默认不设置就是这个了
        # 'rest_framework.permissions.AllowAny',
    ),
    # 自定义异常
    'EXCEPTION_HANDLER': 'xpgg_oms.views.utils.custom_exception_handler',
    # filter过滤配置
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=1440),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

SWAGGER_SETTINGS = {
    # 基础样式
    'SECURITY_DEFINITIONS': {
        "basic": {
            'type': 'basic'
        }
    },
    # 如果需要登录才能够查看接口文档, 登录的链接使用restframework自带的.
    'LOGIN_URL': 'rest_framework:login',
    'LOGOUT_URL': 'rest_framework:logout',
    # 'SHOW_REQUEST_HEADERS':True,
    # 'USE_SESSION_AUTH': True,
    'DOC_EXPANSION': 'None',
    # 接口文档中方法列表以首字母升序排列
    'APIS_SORTER': 'alpha',
    # 如果支持json提交, 则接口文档中包含json输入框
    'JSON_EDITOR': True,
    # 列表排序 按字母
    'OPERATIONS_SORTER': 'alpha',
    # 标签排序 按字母
    'TAGS_SORTER': 'alpha',
    'VALIDATOR_URL': None,
}

# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

# 配置上传文件路径
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 自定义用户model
AUTH_USER_MODEL = 'xpgg_oms.MyUser'

# 自定义日志输出信息
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s  [%(levelname)s]- %(message)s'},  # 日志格式
    },
    'filters': {
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
            },

        'default': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',  # 这个类是写入文件使用的
            'filename': os.path.join(BASE_DIR, 'logs/accecss.log'),     # 日志输出文件，根目录下需要手动新建
            'maxBytes': 1024*1024*5,                  # 文件大小5M
            'backupCount': 5,                         # 备份份数
            'formatter': 'standard',                   # 使用哪种formatters日志格式上面定义了standard
        },

        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',  # 这个类是输出到控制台使用的stream
            'formatter': 'standard'
        },

        'request_handler': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/error.log'),
            'maxBytes': 1024*1024*5,
            'backupCount': 5,
            'formatter': 'standard',
            },
    },
    # 下面是定义日志器
    'loggers': {
        # django自带父日志器
        'django': {
            'handlers': ['default', 'console'],
            'propagate': True
        },
        # django自带的5xx或者4xx错误记录在script.log里
        'django.request': {
            'handlers': ['request_handler'],
            'level': 'ERROR',
            'propagate': False,  # 是否继承父类即上面这个django
            },

        # 下面是给views调用使用的
        'xpgg_oms.views': {
            'handlers': ['default', 'console'],
            'level': 'INFO',
        },
    }
}
