from django.db.models.functions import ExtractMonth
from rest_framework import viewsets
from rest_framework import mixins
from xpgg_oms.serializers import dashboard_serializers
from rest_framework.response import Response
from django.db.models import Count
from xpgg_oms.models import AppReleaseLog, SaltKeyList, MinionList
from django_celery_results.models import TaskResult
import datetime
import psutil

import logging
logger = logging.getLogger('xpgg_oms.views')


class DashboardViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    create:
        首页各种信息集中返回

    """
    serializer_class = dashboard_serializers.DashboardSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            response_data = {'results': {}, 'status': False}
            # 统计saltkey的状态
            response_data['results']['saltkey_certification_count'] = SaltKeyList.objects.values(
                'certification_status').order_by('certification_status').annotate(Count('certification_status'))
            # 统计minion的状态
            response_data['results']['minion_status_count'] = MinionList.objects.values('minion_status').order_by(
                'minion_status').annotate(Count('minion_status'))
            # 获取最后6条应用发布日志
            response_data['results']['release_log'] = AppReleaseLog.objects.values('app_name', 'create_time',
                                                                                   'release_result').order_by('-id')[:6]
            # 获取最后6条任务调度执行日志
            response_data['results']['task_log'] = TaskResult.objects.values('task_name', 'date_done',
                                                                             'status').order_by('-id')[:6]
            # 统计今年每月发布数量
            now_year = datetime.datetime.now().year
            first_day = str(now_year) + '-01-01 00:00:00'
            date_time = datetime.datetime.strptime(first_day, '%Y-%m-%d %X')
            response_data['results']['release_log_count'] = AppReleaseLog.objects.filter(
                create_time__gte=date_time).annotate(month=ExtractMonth('create_time')).values('month').order_by(
                'month').annotate(count=Count('id'))
            # 本机性能监控
            sys_status = []
            cpu_use = str(100 - int(psutil.cpu_times_percent(interval=1, percpu=False).idle)) + '%'
            mem_use = str(psutil.virtual_memory().used//1024//1024) + '/' + str(psutil.virtual_memory().total//1024//1024) + 'M'
            sys_status.append({'name': 'CPU使用率', 'value': cpu_use})
            sys_status.append({'name': '内存使用率', 'value': mem_use})
            disk = psutil.disk_partitions()
            for i in disk:
                disk_use = psutil.disk_usage(i.mountpoint)
                # 判断一下磁盘是否已经存在列表中了，因为有时候一个磁盘挂载了好几个目录，disk里包含每个目录但其实都是同一个磁盘
                # 所以加过一次以后，如果一样的就不要加了
                if {'name': '磁盘 %s 使用率' % i.device, 'value': '%.1f%%' % disk_use.percent} not in sys_status:
                    sys_status.append({'name': '磁盘 %s 使用率' % i.device, 'value': '%.1f%%' % disk_use.percent})
            response_data['results']['sys_status'] = sys_status
        else:
            response_data = {'results': serializer.errors, 'status': False}
        return Response(response_data)

