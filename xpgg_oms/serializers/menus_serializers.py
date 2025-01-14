from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from xpgg_oms.models import Routes, Roles, MyUser
from django.shortcuts import get_object_or_404
import json
import logging
logger = logging.getLogger('xpgg_oms.views')


# 动态菜单 角色增删改序列化类
class RolesSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, help_text='角色名称', validators=[UniqueValidator(queryset=Roles.objects.all(), message='角色已存在')])
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=20, help_text='描述')
    # 取消这里用户ID列表的create和update，单独一个序列化处理，因为用户量太大后前端一次性返回会很卡
    # user_list = serializers.ListField(required=False, help_text='用户ID列表')
    routes = serializers.ListField(required=False, help_text='路由ID列表')
    view_api = serializers.ListField(required=False, help_text='view-api权限ID列表')

    def create(self, validated_data):
        data = dict()
        data['name'] = validated_data.get('name').strip()
        data['description'] = validated_data.get('description').strip()
        role = Roles.objects.create(**data)
        # 取消用户的新增和更新操作，单独做
        # if validated_data.get('user_list'):
        #     role.username.add(*validated_data.get('user_list'))
        if validated_data.get('routes'):
            role.routes_set.add(*validated_data.get('routes'))
        if validated_data.get('view_api'):
            role.viewapi_set.add(*validated_data.get('view_api'))
        return role

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.save()
        # 取消用户的新增和更新操作，单独做
        # if validated_data.get('user_list'):
        #     instance.username.set(validated_data.get('user_list'))
        # else:
        #     instance.username.clear()
        if validated_data.get('routes'):
            instance.routes_set.set(validated_data.get('routes'))
        else:
            instance.routes_set.clear()
        if validated_data.get('view_api'):
            instance.viewapi_set.set(validated_data.get('view_api'))
        else:
            instance.viewapi_set.clear()
        return instance

# 动态菜单 角色包含的用户增删改序列化类
class RolesUserSerializer(serializers.ModelSerializer):
    role_id = serializers.IntegerField(required=False, help_text='角色ID', write_only=True)
    user_list = serializers.ListField(required=False, help_text='用户ID列表', write_only=True)

    def create(self, validated_data):
        # 传回参数包含role的id和要添加的用户id
        role_id = validated_data.get('role_id')
        user_list = validated_data.get('user_list')
        role = get_object_or_404(Roles, pk=role_id)
        # add方法重复添加不会报错
        role.username.add(*user_list)
        return role

    # def update(self, instance, validated_data):
    #     # 删除或者清空
    #     if validated_data.get('user_list'):
    #         instance.username.remove(*validated_data.get('user_list'))
    #     else:
    #         instance.username.clear()
    #     return instance


    class Meta:
        # 设置继承的数据库
        model = MyUser
        # 设置显示的字段
        fields = ('id', 'username', 'is_active', 'role_id', 'user_list')
        # 扩展字段属性，他妈的感觉还不如不用model序列化，查询和创建都要写
        extra_kwargs = {'id': {'read_only': True},'username': {'read_only': True},'is_active': {'read_only': True}}
        # fields = "__all__" 取所有字段

