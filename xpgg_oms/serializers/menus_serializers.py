from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from xpgg_oms.models import Routes, Roles
import json
import logging
logger = logging.getLogger('xpgg_oms.views')


# 动态菜单 角色增删改序列化类
class RolesSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, help_text='角色名称', validators=[UniqueValidator(queryset=Roles.objects.all(), message='角色已存在')])
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=20, help_text='描述')
    user_list = serializers.ListField(required=False, help_text='用户ID列表')
    routes = serializers.ListField(required=False, help_text='路由ID列表')

    def create(self, validated_data):
        data = dict()
        data['name'] = validated_data.get('name').strip()
        data['description'] = validated_data.get('description').strip()
        role = Roles.objects.create(**data)
        if validated_data.get('user_list'):
            role.username.add(*validated_data.get('user_list'))
        if validated_data.get('routes'):
            role.routes_set.add(*validated_data.get('routes'))
        return role

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.save()
        if validated_data.get('user_list'):
            instance.username.set(validated_data.get('user_list'))
        if validated_data.get('routes'):
            instance.routes_set.set(validated_data.get('routes'))
        return instance


# # 动态菜单 用户角色关联表序列化类
# class UserToRolesSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = UserToRoles
#         fields = '__all__'



