from xpgg_oms.models import ViewApi
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import filters
from xpgg_oms.serializers import viewapi_serializers
import logging
logger = logging.getLogger('xpgg_oms.views')

# viwe api表增删改查
class ViewApiViewSet(viewsets.ModelViewSet):
    """
    list:
    View API列表

    retrieve:
    View API详细信息

    create:
    创建View API

    update:
    更新当前id View API信息

    partial_update:
    更新当前id View API部分记录

    delete:
    删除View API

    """
    queryset = ViewApi.objects.all()
    # 指定查询字段默认是pk
    # lookup_field = 'username'
    serializer_class = viewapi_serializers.ViewApiSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    # 搜索框
    search_fields = ('name', 'view_name')
    # 因为前端直接获取api全表，所以这里不做分页，这里放心api数据量很小
    # pagination_class = None
    # 默认排序规则
    ordering = ('name',)
    ordering_fields = ('id', 'name')

# viwe api表不分页查询所有，给授权使用的
class ViewApiAllViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    list:
        不分页，获取所有view api信息

    """
    queryset = ViewApi.objects.all()
    serializer_class = viewapi_serializers.ViewApiSerializer
    pagination_class = None