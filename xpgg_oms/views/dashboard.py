from django.db.models.functions import ExtractMonth
from rest_framework import viewsets
from rest_framework import mixins
from xpgg_oms.serializers import dashboard_serializers
from rest_framework.response import Response
from django.db.models import Count
from xpgg_oms.models import AppReleaseLog, SaltKeyList, MinionList
from django_celery_results.models import TaskResult
import datetime

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
        else:
            response_data = {'results': serializer.errors, 'status': False}
        return Response(response_data)

