from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import filters
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from django_celery_beat import models
from django_celery_results.models import TaskResult
from django.db.models import Q
from celery import current_app
from django.template.defaultfilters import pluralize
from django.utils.translation import ugettext_lazy as _
from kombu.utils.json import loads
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
    # 只需要给前端显示任务模板是命令或者脚本的任务即可
    queryset = models.PeriodicTask.objects.filter(Q(task='命令') | Q(task='脚本'))
    serializer_class = periodic_task_serializers.PeriodicTaskModelSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    # 搜索框
    search_fields = ('name',)
    # 可选的排序规则
    ordering_fields = ('id', 'name')
    # 默认排序规则
    ordering = ('id',)

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

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            # 下面都是源码内容
            self.perform_update(serializer)
            if getattr(instance, '_prefetched_objects_cache', None):
                # If 'prefetch_related' has been applied to a queryset, we need to
                # forcibly invalidate the prefetch cache on the instance.
                instance._prefetched_objects_cache = {}
            response_data = {'results': '更新成功', 'status': True}
            return Response(response_data)
        else:
            response_data = {'results': serializer.errors, 'status': False}
            return Response(response_data)


# 获取日期列表，任务调度表新增的时候需要显示所有可选日期
class ClockedListModelViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    list:
        任务调度 获取日期列表

    """
    queryset = models.ClockedSchedule.objects.all()
    serializer_class = periodic_task_serializers.ClockedScheduleModelSerializer
    pagination_class = None


# 获取Crontab列表，任务调度表新增的时候需要显示所有可选Crontab
class CrontabListModelViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    list:
        任务调度 获取Crontab列表

    """

    # crontab表的timezone字段比较特殊无法直接查询出来用Response返回会报错，所以要调用序列化，序列化里有手动做了处理我
    queryset = models.CrontabSchedule.objects.all()
    serializer_class = periodic_task_serializers.CrontabScheduleModelSerializer
    pagination_class = None


# 获取Interval列表，任务调度表新增的时候需要显示所有可选Interval
class IntervalListModelViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    list:
        任务调度 获取Interval列表

    """

    queryset = models.IntervalSchedule.objects.all()
    serializer_class = periodic_task_serializers.IntervalScheduleModelSerializer
    pagination_class = None


# 手动立即执行一次任务
class RunTaskModelViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
        create:
            手动立即执行选中的任务一次

        """
    queryset = models.PeriodicTask.objects.all()
    serializer_class = periodic_task_serializers.RunTaskSerializer
    celery_app = current_app

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # 从django_celery_beat的admin.py中拷贝过来的代码
            queryset = models.PeriodicTask.objects.filter(id__in=request.data.get('id_list'))
            self.celery_app.loader.import_default_modules()
            tasks = [(self.celery_app.tasks.get(task.task),
                      loads(task.args),
                      loads(task.kwargs),
                      task.queue)
                     for task in queryset]

            if any(t[0] is None for t in tasks):
                for i, t in enumerate(tasks):
                    if t[0] is None:
                        break

                # variable "i" will be set because list "tasks" is not empty
                not_found_task_name = queryset[i].task
                response_data = {'results': 'task "{0}" not found'.format(not_found_task_name), 'status': False}
                return Response(response_data)

            task_ids = [task.apply_async(args=args, kwargs=kwargs, queue=queue)
                        if queue and len(queue)
                        else task.apply_async(args=args, kwargs=kwargs)
                        for task, args, kwargs, queue in tasks]
            tasks_run = len(task_ids)
            response_data = {'results': '{0} task{1} {2} successfully run'.format(tasks_run, pluralize(tasks_run),
                                                                                  pluralize(tasks_run, _('was,were'))), 'status': True}
            return Response(response_data)
        else:
            response_data = {'results': serializer.errors, 'status': False}
            return Response(response_data)


# 任务结果表 增删改查
class TaskResultScheduleModelViewSet(viewsets.ModelViewSet):
    """
        任务结果表 增删改查

    """
    queryset = TaskResult.objects.all()
    serializer_class = periodic_task_serializers.TaskResultScheduleModelSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    # 搜索框
    search_fields = ('task_name',)
    # 可选的排序规则
    ordering_fields = ('id', 'task_name')
    # 默认排序规则,这个要倒叙看结果
    ordering = ('-id',)

    # 自定义批量删除方法，action装饰器使得multiple_delete方法可以接受delete操作，detail=False是url不需要传pk
    @action(methods=['delete'], detail=False)
    def multiple_delete(self, request, *args, **kwargs):
        try:
            id_list = request.query_params.getlist('id_list', None)
            TaskResult.objects.filter(id__in=id_list).delete()
            return Response({'results': '删除成功', 'status': True})
        except Exception as e:
            response_data = {'results': '提交数据格式不符合规范，请检查', 'status': False}
            return Response(response_data)

