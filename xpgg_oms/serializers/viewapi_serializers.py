from rest_framework import serializers
from xpgg_oms.models import ViewApi
import logging
logger = logging.getLogger('xpgg_oms.views')

# API表 增删改查序列化类
class ViewApiSerializer(serializers.ModelSerializer):


    class Meta:
        # 设置继承的数据库
        model = ViewApi
        # 设置显示的字段
        fields = "__all__"
