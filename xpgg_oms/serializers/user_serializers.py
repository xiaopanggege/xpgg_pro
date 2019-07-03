from rest_framework import serializers
from django.contrib.auth.models import Group
from xpgg_oms.models import MyUser
import logging
logger = logging.getLogger('xpgg_oms.views')


# 用户详细信息序列化类
class MyUserDetailSerializer(serializers.ModelSerializer):
    # 无用，SlugRelatedField这个方法是取外键中的某个字段slug_field定义的值组成一个列表，注意是值，不是key:value这种格式
    groups = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    # 这种是自定义字段名字以及返回内容，参数是：get_库名，比如这里的get_roles_set就是多对多另一个库的roles字段因为是反向所以加_set，具体返回内容是在下面方法中
    roles = serializers.SerializerMethodField(method_name='get_roles_set')

    class Meta:
        # 设置继承的数据库
        model = MyUser
        # 设置显示的字段
        fields = ('id', 'username', 'avatar', 'groups', 'roles', 'is_superuser')
        # fields = "__all__" 取所有字段

    # 这个是上面自定义字段roles的具体返回内容，这里因为groups是一个多对多外键，所以用all来获取所有多个数据，然后返回一个列表
    def get_roles_set(self, obj):
        return [roles.name for roles in obj.roles_set.all()]
