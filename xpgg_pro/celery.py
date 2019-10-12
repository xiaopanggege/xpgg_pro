from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# 这里我们的项目名称为xpgg_pro,所以为xpgg_pro.settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xpgg_pro.settings")

# 创建celery应用
app = Celery('celery_app')


app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
