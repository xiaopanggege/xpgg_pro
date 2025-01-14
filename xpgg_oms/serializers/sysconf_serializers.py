from rest_framework import serializers
from xpgg_oms.models import SystemConf
import logging
logger = logging.getLogger('xpgg_oms.views')



# 用户详细信息序列化类
class SysConfSerializer(serializers.ModelSerializer):

    class Meta:
        # 设置继承的数据库
        model = SystemConf
        # 设置显示的字段
        fields = "__all__"   # 取所有字段


class EmailTestSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text='邮箱账号')
    password = serializers.CharField(max_length=100, help_text='邮箱密码')
    smtp_addr = serializers.CharField(max_length=100, help_text='smtp地址')
    smtp_port = serializers.CharField(max_length=100, help_text='smtp端口')
    security = serializers.ListField(required=False, help_text='安全设置')
    email_name = serializers.CharField(required=False, max_length=100, help_text='邮箱前缀名称')
    tmail_name = serializers.EmailField(help_text='收件邮箱')

