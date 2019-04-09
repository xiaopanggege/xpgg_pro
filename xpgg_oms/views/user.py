from django.shortcuts import render
from rest_framework import status
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework.views import APIView
from rest_framework.response import Response
from xpgg_oms.serializers import user_serializers
from xpgg_oms.models import MyUser
from django.contrib.auth.models import Group

import logging
logger = logging.getLogger('xpgg_oms.views')


class MyUserViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    用户详细信息，后台获取{id}随意填
    """
    queryset = MyUser.objects.all()
    # 指定查询字段默认是pk
    # lookup_field = 'username'
    serializer_class = user_serializers.MyUserDetailSerializer

    # 查询操作会调用get_object方法，他是是获取路由传递过来的字段来查找对象，默认获取详细信息是路由是{prefix}/{lookup}/而{lookup}默认
    # 是主键，这里强制返回了当前用户的对象，所以不管{lookup}设置什么都是返回当前用户信息，这样前端只要随便传任意就行
    def get_object(self):
        return self.request.user



