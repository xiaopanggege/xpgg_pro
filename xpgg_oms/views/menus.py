from xpgg_oms.models import Roles, Routes, MyUser
from xpgg_oms.views.utils import StandardPagination
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import filters
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from xpgg_oms.serializers import menus_serializers
# 下面这个是py3解决requests请求https误报问题
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import logging
logger = logging.getLogger('xpgg_oms.views')


# 应用发布搜索过滤器 直接写在这里因为每个功能基本就一个
class RolesFilter(django_filters.rest_framework.FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = Roles
        fields = ['name']


# 完整动态菜单获取路由表
def create_route(queryset):
    data_list = []
    for data in queryset:
        tmp = dict()
        tmp['id'] = data.id
        tmp['path'] = data.path
        tmp['component'] = data.component
        if data.name:
            tmp['name'] = data.name
        if data.redirect:
            tmp['redirect'] = data.redirect
        if data.alwaysShow:
            tmp['alwaysShow'] = data.alwaysShow
        tmp['meta'] = {}
        tmp['meta']['title'] = data.title
        if data.icon:
            tmp['meta']['icon'] = data.icon
        if data.noCache:
            tmp['meta']['noCache'] = data.noCache
        tmp['meta']['roles'] = [role.name for role in data.roles.all()]
        if data.activeMenu:
            tmp['meta']['activeMenu'] = data.activeMenu
        tmp['meta']['roles'] = [role.name for role in data.roles.all()]
        if data.hidden:
            tmp['hidden'] = data.hidden
        children = data.pid.all()
        if len(children) > 0:
            tmp['children'] = create_route(data.pid.all())
            data_list.append(tmp)
        else:
            data_list.append(tmp)

    return data_list


# 动态菜单栏 路由：查询 APIView方式
class RoutesModel(APIView):
    """
    动态菜单路由列表

    """
    def get(self, request, format=None):
        queryset = Routes.objects.filter(parentId=None).order_by('route_id')
        data = create_route(queryset)
        return Response(data)


# 角色路由表获取
def create_route_role(queryset, role):
    data_list = []
    for data in queryset:
        if role in [role.name for role in data.roles.all()]:
            tmp = dict()
            tmp['id'] = data.id
            tmp['path'] = data.path
            tmp['component'] = data.component
            if data.name:
                tmp['name'] = data.name
            if data.redirect:
                tmp['redirect'] = data.redirect
            if data.alwaysShow:
                tmp['alwaysShow'] = data.alwaysShow
            tmp['meta'] = {}
            tmp['meta']['title'] = data.title
            if data.icon:
                tmp['meta']['icon'] = data.icon
            if data.noCache:
                tmp['meta']['noCache'] = data.noCache
            tmp['meta']['roles'] = [role.name for role in data.roles.all()]
            if data.activeMenu:
                tmp['meta']['activeMenu'] = data.activeMenu
            tmp['meta']['roles'] = [role.name for role in data.roles.all()]
            if data.hidden:
                tmp['hidden'] = data.hidden
            children = data.pid.all()
            if len(children) > 0:
                tmp['children'] = create_route_role(data.pid.all(), role)
                data_list.append(tmp)
            else:
                data_list.append(tmp)

    return data_list


# 动态菜单栏角色：增删改查
class RolesModelViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """
    list:
    动态菜单角色列表

    create:
    创建角色

    update:
    更新当前id角色

    partial_update:
    更新当前id角色部分记录

    destroy:
    删除角色

    """
    queryset = Roles.objects.all()
    serializer_class = menus_serializers.RolesSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filter_class = RolesFilter
    pagination_class = StandardPagination
    # 默认排序规则
    ordering = ('id',)
    ordering_fields = ('id', 'name')
    # 动态菜单修改量比较大所以自己写所有逻辑

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        response_data = []
        for data in queryset:
            tmp = dict()
            tmp['id'] = data.id
            tmp['name'] = data.name
            tmp['user_list'] = data.username.all().values_list('id', flat=True)
            tmp['description'] = data.description
            tmp['routes'] = create_route_role(data.routes_set.filter(parentId=None).order_by('route_id'), data.name)
            response_data.append(tmp)
        page = self.paginate_queryset(response_data)
        if page is not None:
            return self.get_paginated_response(page)
        return Response(queryset)

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


# 动态菜单栏用户角色关联表：查询用户名列表 APIVIEW方式
class UserList(APIView):
    """
    获取用户名列表

    """

    def get(self, request, format=None):
        data = MyUser.objects.values('id', 'username')
        return Response(data)
