from xpgg_oms.models import Roles, Routes, MyUser
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import filters
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from django.shortcuts import get_object_or_404
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
            tmp['children'] = create_route(data.pid.all().order_by('route_id'))
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
def create_route_role(queryset, user_role):
    data_list = []
    for data in queryset:
        if user_role in [role.name for role in data.roles.all()]:
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
                tmp['children'] = create_route_role(data.pid.all().order_by('route_id'), user_role)
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
    # 默认排序规则
    ordering = ('id',)
    ordering_fields = ('id', 'name')
    # 动态菜单修改量比较大所以自己写所有逻辑

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        response_data = []
        # 下面这个做法不是很好，因为如果数据量大有几十万几十亿那等于把所有数据处理一遍再去分页，而不是orm默认的懒加载分页方式
        for data in queryset:
            tmp = dict()
            tmp['id'] = data.id
            tmp['name'] = data.name
            # 这里有一个坑，就是如果这个角色的用户非常多，返回到前端用户列表就会非常大，前端响应会很卡，所以不在直接获取，单独做
            # tmp['user_list'] = data.username.all().values_list('id', flat=True)
            tmp['description'] = data.description
            tmp['view_api'] = list(data.viewapi_set.values_list('id', flat=True))
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

# 角色包含的用户搜索过滤器 直接写在这里因为每个功能基本就一个
class RolesUserFilter(django_filters.rest_framework.FilterSet):
    username = django_filters.CharFilter(field_name='username', lookup_expr='icontains')
    is_active = django_filters.CharFilter(field_name='is_active', lookup_expr='icontains')


    class Meta:
        model = MyUser
        fields = ['username', 'is_active']

# 角色包含的用户：增删改查
class RolesUserModelViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """
    list:
    角色包含的用户列表

    create:
    添加角色包含用户

    destroy:
    删除角色包含用户

    """
    queryset = MyUser.objects.all()
    serializer_class = menus_serializers.RolesUserSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filter_class = RolesUserFilter
    # 默认排序规则
    ordering = ('id',)
    ordering_fields = ('id', 'username', 'is_active')

    def get_queryset(self):
        role_id = self.request.query_params.get('role_id',None)
        if role_id is not None:
            queryset = Roles.objects.get(id=role_id).username.all()
        else:
            # 这个不能乱写，我原来写的是Roles.objects.none()前端测试等都没问题，
            # 但是swagger报错FilterSet model <class 'xpgg_oms.models.Roles'> does not match queryset model <class 'xpgg_oms.models.MyUser'>
            # 原因我研究了一下发现是因为上面if里虽然是Roles但结果实际是MyUser，所以else也要是MyUser，上面RolesUserFilter也必须是MyUser
            queryset = MyUser.objects.none()
        return queryset

    # def list(self, request, *args, **kwargs):
    #     role_id = request.query_params.get('role_id',None)
    #     if role_id is not None:
    #         queryset = Roles.objects.get(id=role_id).username.all()
    #     else:
    #         return Response(None)
    #     queryset = self.filter_queryset(queryset)
    #     page = self.paginate_queryset(queryset)
    #     if page is not None:
    #         serializer = self.get_serializer(page, many=True)
    #         return self.get_paginated_response(serializer.data)
    #
    #     serializer = self.get_serializer(queryset, many=True)
    #     return Response(serializer.data)

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

    # # 本来想用更新代替删除多对多表的用户关系，结果发现model不同会报错，不想去解决直接用下面删除了
    # def update(self, request, *args, **kwargs):
    #     partial = kwargs.pop('partial', False)
    #     instance = self.get_object()
    #     serializer = self.get_serializer(instance, data=request.data, partial=partial)
    #     if serializer.is_valid():
    #         # 下面都是源码内容
    #         self.perform_update(serializer)
    #         if getattr(instance, '_prefetched_objects_cache', None):
    #             # If 'prefetch_related' has been applied to a queryset, we need to
    #             # forcibly invalidate the prefetch cache on the instance.
    #             instance._prefetched_objects_cache = {}
    #         response_data = {'results': '更新成功', 'status': True}
    #         return Response(response_data)
    #     else:
    #         response_data = {'results': serializer.errors, 'status': False}
    #         return Response(response_data)

    def destroy(self, request, *args, **kwargs):
        role_id = request.data.get('role_id',None)
        user_list = request.data.get('user_list',None)
        logger.error(role_id)
        role = get_object_or_404(Roles, pk=role_id)
        # 有就删除，没有就清空，包含前端两个操作按钮
        if user_list:
            role.username.remove(*user_list)
        else:
            role.username.clear()
        response_data = {'results': '删除成功', 'status': True}
        return Response(response_data)


# 动态菜单栏用户角色关联表：查询用户名列表 APIVIEW方式
class UserList(APIView):
    """
    获取is_active为真的用户名列表

    """

    def get(self, request, format=None):
        data = MyUser.objects.filter(is_active=1).values('id', 'username')
        return Response(data)
