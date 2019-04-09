from rest_framework import serializers
from xpgg_oms.models import MinionList
import logging
logger = logging.getLogger('xpgg_oms.views')


# Minion List操作序列化类
class MinionIdListSerializer(serializers.ModelSerializer):
    class Meta:
        # 设置继承的数据库
        model = MinionList
        # 设置显示的字段
        fields = ('minion_id')