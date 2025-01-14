from rest_framework import serializers
import logging
logger = logging.getLogger('xpgg_oms.views')

# 双子星外网放通IP序列号
class RuiJieSZXAddIntnetSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=100, help_text='用户')
    ip = serializers.CharField(max_length=100, help_text='IP')

