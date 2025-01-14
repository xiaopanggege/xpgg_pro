from rest_framework import serializers
from xpgg_oms.models import RuiJieUserInfo
import logging
logger = logging.getLogger('xpgg_oms.views')

# 序列号ruijie用户表
class RuiJieUserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuiJieUserInfo
        fields = '__all__'