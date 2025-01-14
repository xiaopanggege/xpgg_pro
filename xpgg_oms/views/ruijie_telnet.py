from xpgg_oms.models import RuiJieUserInfo
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework.response import Response
from rest_framework import filters
import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from telnetlib import Telnet
import time
from xpgg_oms.serializers import ruijietelnet_serializers
import logging
logger = logging.getLogger('xpgg_oms.views')

# 双子星放通外网
class RuiJieSZXAddIntnet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    双子星放通外网IP操作

    """
    serializer_class = ruijietelnet_serializers.RuiJieSZXAddIntnetSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            response_data = {'results': serializer.errors, 'status': False}
            return Response(response_data)
        try:
            username = serializer.validated_data.get('username')
            ip = serializer.validated_data.get('ip')
            host = '10.96.11.2'
            user = 'jiangxianfu'
            password = '123@jxf@123'
            tn = Telnet(host, port=23)
            tn.read_until(b'Username:', timeout=3)
            tn.write(user.encode('utf-8') + b'\n')
            tn.read_until(b'Password:', timeout=3)
            tn.write(password.encode('utf-8') + b'\n')
            tn.read_until(b'chukou_zhu#', timeout=3)
            # 特权模式
            tn.write(('configure t').encode('utf-8') + b'\n')
            tn.read_until(b'(config)#', timeout=3)
            # 开通外网要两条一条是开通，一条是取消vpn用的,如果是python2要先解码在编码.decode('utf8').encode('gbk')
            tn.write(('''subscriber static name "%s" parent "/系统自助放行组" ip-host %s''' % (username, ip)).encode(
                'gbk') + b'\n')
            results = tn.read_until(b'ip conflict with', timeout=3)
            if b"ip conflict with" in results:
                return Response({'results': 'IP已存在无法添加', 'status': False})
            elif b"Invalid input detected" in results:
                return Response({'results': '输入有错误，添加失败', 'status': False})
            time.sleep(1)
            tn.write(('''subscriber allow %s privilege none''' % username).encode('gbk') + b'\n')
            tn.read_until(b'(config)#', timeout=3)
            time.sleep(1)

            # 删除
            # tn.write(('''no subscriber static name "江贤福10.104.20.14"''' ).encode('gbk') + b'\n')
            # time.sleep(1)

            tn.close()
            return Response({'results': '添加成功', 'status': True})
        except Exception as e:
            return Response({'results': '双子星放通外网异常：'+str(e), 'status': False})

