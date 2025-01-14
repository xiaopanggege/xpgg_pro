from xpgg_oms.models import RuiJieUserInfo
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import filters
import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from xpgg_oms.serializers import ruijieuserinfo_serializers
import logging
logger = logging.getLogger('xpgg_oms.views')

# RuiJieUserInfo页面查询过滤器
class RuiJieUserInfoFilter(django_filters.rest_framework.FilterSet):
    UserName = django_filters.CharFilter(field_name="UserName", lookup_expr='icontains')
    UserID = django_filters.CharFilter(field_name="UserID", lookup_expr='icontains')
    department = django_filters.CharFilter(field_name="department", lookup_expr='icontains')

    class Meta:
        model = RuiJieUserInfo
        fields = ['UserName', 'UserID', 'disabled', 'department']

class RuiJieUserInfoViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    list:
        ruijie用户列表信息

    """
    queryset = RuiJieUserInfo.objects.all()
    serializer_class = ruijieuserinfo_serializers.RuiJieUserInfoSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filter_class = RuiJieUserInfoFilter
    # 引入公共分页类 全局定义了所以不需要了
    # pagination_class = StandardPagination
    # 自定义每页个数
    # pagination_class.page_size = 1

    # 可选的排序规则
    ordering_fields = ('id', 'UserName', 'UserID', 'disabled', 'IsLeader')

