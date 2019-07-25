from django.shortcuts import render
from rest_framework import status
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework import viewsets
from xpgg_oms.views.utils import StandardPagination, format_state
from rest_framework import mixins
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from xpgg_oms.serializers import user_serializers
from xpgg_oms.models import MyUser
from django.contrib.auth.models import Group

import logging
logger = logging.getLogger('xpgg_oms.views')


class MyUserViewSet(viewsets.ModelViewSet):
    """
    用户详细信息，后台获取{id}随意填
    """
    queryset = MyUser.objects.all()
    # 指定查询字段默认是pk
    # lookup_field = 'username'
    serializer_class = user_serializers.MyUserDetailSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    # 搜索框
    search_fields = ('username',)
    pagination_class = StandardPagination
    # 默认排序规则
    ordering = ('id',)
    ordering_fields = ('id', 'username')

    # 查询操作会调用get_object方法，他是是获取路由传递过来的字段来查找对象，默认获取详细信息是路由是{prefix}/{lookup}/而{lookup}默认
    # 是主键，这里强制返回了当前用户的对象，所以不管{lookup}设置什么都是返回当前用户信息，这样前端只要随便传任意就行
    # def get_object(self):
    #     return self.request.user

    def retrieve(self, request, *args, **kwargs):
        # 本来是在get_object方法里强制返回当前用户对象，但是后面因为更新也要用到get_object所以放回到这里来强制了
        instance = self.request.user
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

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


