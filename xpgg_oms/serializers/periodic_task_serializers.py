from django_celery_beat import models
from rest_framework import serializers
import logging
logger = logging.getLogger('xpgg_oms.views')


# 时钟定时器序列化类
class ClockedScheduleModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ClockedSchedule
        fields = '__all__'


# 计划任务定时器序列化类
class CrontabScheduleModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CrontabSchedule
        # fields = '__all__'
        # 不开放timezone这个字段，因为celery_beat的这个字段是用了第三方库的，在drf里面无法直接序列化奶奶的
        exclude = ['timezone']


# 时间间隔定时器序列化类
class IntervalScheduleModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.IntervalSchedule
        fields = '__all__'


# 任务调度序列化类
class PeriodicTaskModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PeriodicTask
        fields = '__all__'