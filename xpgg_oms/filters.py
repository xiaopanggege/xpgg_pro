# drf的过滤器，由于不多，所以统一写在一个文件里,后面懒得写一起，都直接写各自的view里去了哈哈
import django_filters
from xpgg_oms.models import *


# minion管理页面过滤
class MinionListFilter(django_filters.rest_framework.FilterSet):
    minion_id = django_filters.CharFilter(field_name="minion_id", lookup_expr='icontains')
    ip = django_filters.CharFilter(field_name="ip", lookup_expr='icontains')

    class Meta:
        model = MinionList
        fields = ['minion_id', 'ip', 'sys', 'minion_status']
