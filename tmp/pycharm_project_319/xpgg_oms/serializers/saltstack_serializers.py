from rest_framework import serializers
from xpgg_oms.models import SaltKeyList
import logging
logger = logging.getLogger('xpgg_oms.views')


# SaltKeyList序列化类
class SaltKeySerializer(serializers.ModelSerializer):
    class Meta:
        # 设置继承的数据库
        model = SaltKeyList
        # 设置显示的字段
        fields = "__all__"

