from xpgg_oms.views.utils import StandardPagination
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from django_celery_beat import models
from xpgg_oms.serializers import periodic_task_serializers
import logging
logger = logging.getLogger('xpgg_oms.views')


# 时钟定时器 增删改
class ClockedScheduleModelViewSet(viewsets.ModelViewSet):
    """
        时钟定时器，增删改操作

    """
    queryset = models.ClockedSchedule.objects.all()
    serializer_class = periodic_task_serializers.ClockedScheduleModelSerializer
    pagination_class = StandardPagination
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    # 可选的排序规则
    ordering_fields = ('id', 'clocked_time')
    # 默认排序规则
    ordering = ('id',)
    # 搜索框
    search_fields = ('clocked_time',)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # 下面都是create源码内容
            self.perform_create(serializer)
            response_data = {'results': '添加成功', 'status': True}
            return Response(response_data)
        else:
            response_data = {'results': serializer.errors, 'status': False}
            return Response(response_data)


# 计划任务定时器 增删改
class CrontabScheduleModelViewSet(viewsets.ModelViewSet):
    """
        计划任务定时器，增删改操作

    """
    queryset = models.CrontabSchedule.objects.all()
    serializer_class = periodic_task_serializers.CrontabScheduleModelSerializer
    pagination_class = StandardPagination
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filter_fields = ('id',)
    # 可选的排序规则
    ordering_fields = ('id',)
    # 默认排序规则
    ordering = ('id',)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        # 因为crontab的格式验证太麻烦了，我在直接使用serializer.is_valid()时候发现会500错误，原因是没有做验证哈，但是他的model有带验证
        # 所以如果数据格式不对会抛出异常，但是没办法被drf捕获导致500，所以我自己用try来捕获
        try:
            if serializer.is_valid():
                # 下面都是create源码内容
                self.perform_create(serializer)
                response_data = {'results': '添加成功', 'status': True}
                return Response(response_data)
            else:
                response_data = {'results': serializer.errors, 'status': False}
                return Response(response_data)
        except Exception as e:
            response_data = {'results': '提交数据格式不符合crontab语法格式，请检查', 'status': False}
            return Response(response_data)


# 时间间隔定时器 增删改
class IntervalScheduleModelViewSet(viewsets.ModelViewSet):
    """
        时间间隔定时器，增删改操作

    """
    queryset = models.IntervalSchedule.objects.all()
    serializer_class = periodic_task_serializers.IntervalScheduleModelSerializer
    pagination_class = StandardPagination

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # 下面都是create源码内容
            self.perform_create(serializer)
            response_data = {'results': '添加成功', 'status': True}
            return Response(response_data)
        else:
            response_data = {'results': serializer.errors, 'status': False}
            return Response(response_data)


# 任务调度 增删改
class PeriodicTaskModelViewSet(viewsets.ModelViewSet):
    """
        任务调度，增删改操作

    """
    queryset = models.PeriodicTask.objects.all()
    serializer_class = periodic_task_serializers.PeriodicTaskModelSerializer
    pagination_class = StandardPagination