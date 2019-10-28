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


# 时钟定时器 增删改查
class ClockedScheduleModelViewSet(viewsets.ModelViewSet):
    """
        时钟定时器，增删改查操作

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


# 计划任务定时器 增删改查
class CrontabScheduleModelViewSet(viewsets.ModelViewSet):
    """
        计划任务定时器，增删改查操作

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


# 时间间隔定时器 增删改查
class IntervalScheduleModelViewSet(viewsets.ModelViewSet):
    """
        时间间隔定时器，增删改查操作

    """
    queryset = models.IntervalSchedule.objects.all()
    serializer_class = periodic_task_serializers.IntervalScheduleModelSerializer
    pagination_class = StandardPagination
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filter_fields = ('id',)
    # 可选的排序规则
    ordering_fields = ('id',)
    # 默认排序规则
    ordering = ('id',)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        # 因为interval的格式验证太麻烦了，我在直接使用serializer.is_valid()时候发现会500错误，原因是没有做验证哈，但是他的model有带验证
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
            response_data = {'results': '提交数据格式不符合interval语法格式，请检查', 'status': False}
            return Response(response_data)


# 任务调度 增删改查
class PeriodicTaskModelViewSet(viewsets.ModelViewSet):
    """
        任务调度，增删改查操作

    """
    queryset = models.PeriodicTask.objects.all()
    serializer_class = periodic_task_serializers.PeriodicTaskModelSerializer
    pagination_class = StandardPagination
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filter_fields = ('id',)
    # 可选的排序规则
    ordering_fields = ('id', 'name')
    # 默认排序规则
    ordering = ('id',)


# 获取日期列表，任务调度表新增的时候需要显示所有可选日期
class ClockedListModelViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    list:
        任务调度 获取日期列表

    """

    def list(self, request, *args, **kwargs):
        data = models.ClockedSchedule.objects.values()
        return Response(data)


# 获取Crontab列表，任务调度表新增的时候需要显示所有可选Crontab
class CrontabListModelViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    list:
        任务调度 获取Crontab列表

    """

    # crontab表的timezone字段比较特殊无法直接查询出来用Response返回会报错，所以要调用序列化，序列化里有手动做了处理我
    queryset = models.CrontabSchedule.objects.all()
    serializer_class = periodic_task_serializers.CrontabScheduleModelSerializer


# 获取Interval列表，任务调度表新增的时候需要显示所有可选Interval
class IntervalListModelViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    list:
        任务调度 获取Interval列表

    """

    def list(self, request, *args, **kwargs):
        data = models.IntervalSchedule.objects.values()
        return Response(data)