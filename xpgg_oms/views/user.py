from django.shortcuts import render
from rest_framework import status
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from xpgg_oms.serializers import user_serializers
from xpgg_oms.models import MyUser
from django.contrib.auth.models import Group
from django.contrib.auth import authenticate
import django_filters
from drf_yasg.utils import swagger_auto_schema

import logging
logger = logging.getLogger('xpgg_oms.views')

class MyUserViewSetFilter(django_filters.rest_framework.FilterSet):
    username = django_filters.CharFilter(field_name="username", lookup_expr='icontains')
    source = django_filters.CharFilter(field_name="source", lookup_expr='icontains')

    class Meta:
        model = MyUser
        fields = ['username', 'is_active', 'source']

# 用户信息增删改查
class MyUserViewSet(viewsets.ModelViewSet):
    """
    list:
    用户列表

    retrieve:
    用户详细信息

    create:
    创建用户

    update:
    更新当前id用户

    partial_update:
    更新当前id用户部分记录

    delete:
    删除用户

    """
    queryset = MyUser.objects.all()
    # 指定查询字段默认是pk
    # lookup_field = 'username'
    serializer_class = user_serializers.MyUserDetailSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend)
    filter_class = MyUserViewSetFilter
    # 搜索框
    search_fields = ('username',)
    # 默认排序规则
    ordering = ('id',)
    ordering_fields = ('id', 'username', 'is_active')

    # 查询操作会调用get_object方法，他是是获取路由传递过来的字段来查找对象，默认获取详细信息是路由是{prefix}/{lookup}/而{lookup}默认
    # 是主键，这里强制返回了当前用户的对象，所以不管{lookup}设置什么都是返回当前用户信息，这样前端只要随便传任意就行
    # def get_object(self):
    #     return self.request.user

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

# 登录用户对自己的信息查询更新，单独和上面整体用户分开，主要也是为了把权限区分开来
class PersonalViewSet(mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """

    retrieve:
    登录用户详细信息，后台获取{id}随意填

    create:
    登录用户修改密码时候的旧密码查询验证

    update:
    更新当前id用户

    partial_update:
    更新当前id用户部分记录


    """
    queryset = MyUser.objects.all()
    # 指定查询字段默认是pk
    # lookup_field = 'username'
    filter_backends = (filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend)
    filter_class = MyUserViewSetFilter
    # 搜索框
    search_fields = ('username',)
    # 默认排序规则
    ordering = ('id',)
    ordering_fields = ('id', 'username', 'is_active')

    def get_serializer_class(self):
        if self.action == "create":
            return user_serializers.PasswordAuthSerializer
        return user_serializers.MyUserDetailSerializer

    # 查询操作会调用get_object方法，他是是获取路由传递过来的字段来查找对象，默认获取详细信息是路由是{prefix}/{lookup}/而{lookup}默认
    # 是主键，这里强制返回了当前用户的对象，所以不管{lookup}设置什么都是返回当前用户信息，这样前端只要随便传任意就行
    def get_object(self):
        return self.request.user

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
    # 旧密码验证
    def create(self, request, *args, **kwargs):
        username = self.request.user.username
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            return Response({'status': True})
        else:
            return Response({'results': '旧密码错误', 'status': False})

# 个人中心修改密码时候判断旧密码 APIVIEW方式  已经融到上面个人用户操作里了，留着当做swagger案例
# class PassAuth(APIView):
#     """
#     判断旧密码
#
#     """
#     # 默认APIView在swagger里面无法测试填入参数，必须加下面的这个才可以
#     @swagger_auto_schema(request_body=user_serializers.PasswordAuthSerializer)
#     def post(self, request, format=None):
#         username = self.request.user.username
#         password = request.data.get('password')
#         user = authenticate(username=username, password=password)
#         if user is not None:
#             return Response({'status': True})
#         else:
#             return Response({'results': '旧密码错误','status': False})

