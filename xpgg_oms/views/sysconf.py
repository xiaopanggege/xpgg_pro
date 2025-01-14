from xpgg_oms.models import *
from .utils import MailSend
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import filters
from xpgg_oms.serializers import sysconf_serializers
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
import logging
logger = logging.getLogger('xpgg_oms.views')




# 系统配置 增删改查
class SysConfViewSet(viewsets.ModelViewSet):
    """
    list:
        系统配置列表信息

    create:
        系统配置参数创建

    retrieve:
        查询详细

    update:
        更新系统配置
    """
    queryset = SystemConf.objects.all()
    serializer_class = sysconf_serializers.SysConfSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filter_fields = ('name',)

    # 自定义每页个数
    # pagination_class.page_size = 1

    # 搜索框
    search_fields = ('name',)
    # 可选的排序规则
    ordering_fields = ('name')


    # 默认create、update方法全部套下面模板，主要是统一返回内容
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



# 系统配置 邮件发送测试
class EmailTestViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    create:
        邮件发送测试

    """
    serializer_class = sysconf_serializers.EmailTestSerializer


    # 默认create、update方法全部套下面模板，主要是统一返回内容
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            data = serializer.data
            # 收件人可以是多个，公共类接收的是列表
            data['tmail_name'] = [data['tmail_name']]
            send_mail = MailSend(data)
            results = send_mail.send_mail()
            response_data = {'results': results, 'status': True}
            return Response(response_data)
        else:
            response_data = {'results': serializer.errors, 'status': False}
            return Response(response_data)


