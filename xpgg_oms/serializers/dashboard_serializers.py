from rest_framework import serializers
import logging
logger = logging.getLogger('xpgg_oms.views')


# 首页请求参数序列化验证
class DashboardSerializer(serializers.Serializer):
    opt_cmd = serializers.CharField(max_length=50, help_text='操作指令')

    def validate_opt_cmd(self, value):
        if value != 'dashboard_search':
            raise serializers.ValidationError("操作指令不正确")
        return value
