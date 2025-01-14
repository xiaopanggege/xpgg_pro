from django.http import JsonResponse, HttpResponseRedirect
from xpgg_oms.salt_api import SaltAPI
from xpgg_oms.models import *
from xpgg_oms import tasks
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import filters
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from xpgg_oms.serializers import saltstack_serializers
from xpgg_oms.filters import MinionListFilter
import re
import os
import datetime
import requests
# 下面这个是py3解决requests请求https误报问题
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import logging
logger = logging.getLogger('xpgg_oms.views')


# --- saltkey管理 ---
# saltkey管理：公共类，saltkey接受拒绝删除操作代码区别不大，单独出来作为公共类继承比较省代码
class SaltKeyUtils(object):

    @staticmethod
    def salt_key_action(minions, action, message):
        with requests.Session() as s:
            saltapi = SaltAPI(session=s)
            action_method = getattr(saltapi, action)
            response_data = action_method(match=minions)
            if response_data['status']:
                if tasks.saltkey_list():
                    response_data = {'results': '%s成功' % message, 'status': True}
                    return response_data
                else:
                    logger.error('%s在执行刷新saltkey操作即tasks.py里的方法时候出错了' % message)
                    response_data = {'results': '%s失败' % message, 'status': False}
                    return response_data
            else:
                return response_data


# saltkey管理：saltkey列表显示，刷新，和test.pingt测试操作
class SaltKeyViewSet(SaltKeyUtils, mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    list:
        SaltKey列表信息

    create:
        刷新
            salt_key_tag值为global_flush_salt_key

    retrieve:
        输入minion_id测试test.ping操作
    """
    queryset = SaltKeyList.objects.all()
    serializer_class = saltstack_serializers.SaltKeySerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filter_fields = ('certification_status', 'id')
    lookup_field = 'minion_id'
    lookup_value_regex = '.+'  # 自定义上面匹配字段的正则模式，默认是[a-z0-9]+匹配不到个别minion id

    # 自定义每页个数
    # pagination_class.page_size = 1

    # 搜索框
    search_fields = ('minion_id',)
    # 可选的排序规则
    ordering_fields = ('id', 'create_date')

    # 调用list返回内容自定义
    def get_paginated_response(self, data):
        """
        动态的给自定义分页返回内容的msg字段添加数据
        """
        assert self.paginator is not None
        # 下面就是要添加的msg内容
        accepted_count = SaltKeyList.objects.filter(certification_status='accepted').count()
        unaccepted_count = SaltKeyList.objects.filter(certification_status='unaccepted').count()
        denied_count = SaltKeyList.objects.filter(certification_status='denied').count()
        rejected_count = SaltKeyList.objects.filter(certification_status='rejected').count()
        msg = {'accepted_count': accepted_count, 'unaccepted_count': unaccepted_count,
               'denied_count': denied_count, 'rejected_count': rejected_count}

        response_data = self.paginator.get_paginated_response(data)
        response_data.data['msg'] = msg
        return response_data

    # 动态选择serializer
    def get_serializer_class(self):
        if self.action == "list":
            return saltstack_serializers.SaltKeySerializer
        elif self.action == "create":
            return saltstack_serializers.SaltKeyFlushSerializer
        return saltstack_serializers.SaltKeySerializer

    # 调用测试test.ping操作自定义
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        minion_id = instance.minion_id
        with requests.Session() as s:
            saltapi = SaltAPI(session=s)
            response_data = saltapi.test_api(tgt=minion_id)
            # 失败或者成功都返回给前端，前端通过status判断执行是否完成，
            # 通过results内容{'192.168.68.51': False, '192.168.68.1': True}判断ping成功还是失败
            return Response(response_data)

    def create(self, request, *args, **kwargs):
        # 全局刷新key列表
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({'results': serializer.errors, 'status': False})
        if tasks.saltkey_list():
            return Response({'results': '刷新成功', 'status': True})
        else:
            return Response({'results': '刷新失败', 'status': False})


# saltkey管理：saltkey接受认证操作
class SaltKeyAcceptViewSet(SaltKeyUtils, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """

    create:
        接受key
            salt_key_tag值为accept_salt_key
            minion_id值为"minion_id1,minion_id2...." or "*"

    """
    serializer_class = saltstack_serializers.SaltKeyAcceptSerializer

    def create(self, request, *args, **kwargs):
        # 接受key操作
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({'results': serializer.errors, 'status': False})
        minions = request.data.get('minion_id')
        response_data = self.salt_key_action(minions, 'saltkey_accept_api', '接受认证key')
        return Response(response_data)


# saltkey管理：saltkey删除认证操作
class SaltKeyDeleteViewSet(SaltKeyUtils, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """

    create:
        删除key
            salt_key_tag值为delete_salt_key
            minion_id值为"minion_id1,minion_id2...." or "*"

    """
    serializer_class = saltstack_serializers.SaltKeyDeleteSerializer

    def create(self, request, *args, **kwargs):
        # 删除key操作
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({'results': serializer.errors, 'status': False})
        minions = request.data.get('minion_id')
        response_data = self.salt_key_action(minions, 'saltkey_delete_api', '删除key')
        return Response(response_data)


# saltkey管理：saltkey拒绝认证操作
class SaltKeyRejectViewSet(SaltKeyUtils, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """

    create:
        拒绝key
            salt_key_tag值为reject_salt_key
            minion_id值为"minion_id1,minion_id2...." or "*"

    """
    serializer_class = saltstack_serializers.SaltKeyRejectSerializer

    def create(self, request, *args, **kwargs):
        # 拒绝key操作
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({'results': serializer.errors, 'status': False})
        minions = request.data.get('minion_id')
        response_data = self.salt_key_action(minions, 'saltkey_reject_api', '拒绝key')
        return Response(response_data)


# saltkey管理：saltkey删除denied里的key操作
class SaltKeyDeleteDeniedViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """

    create:
        删除denied的key
            salt_key_tag值为delete_denied_salt_key
            minion_id值为"minion_id1,minion_id2...." or "*"

    """
    serializer_class = saltstack_serializers.SaltKeyDeleteDeniedSerializer

    def create(self, request, *args, **kwargs):
        # 删除denied里的key操作
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({'results': serializer.errors, 'status': False})
        minions = request.data.get('minion_id')
        # 删除denied里的key比较特殊无法通过saltkey_delete_api来删除因为denied的产生是在已接受key中已经存在了同名的minion_id，然后原来
        # 应该存在于未认证列表中的key就会被salt存放到denied里，而通过salt-key -d删除key会把已接受的key一起删除，官方没有提出解决办法，所以
        # 只能通过命令行cmd的方式用rm删除实际存放的文件来销毁denied里的key
        minions = ' '.join(minions)
        with requests.Session() as s:
            saltapi = SaltAPI(session=s)
            # 注意master的minion_id没有设置错误一般删除没都问题
            response_data = saltapi.cmd_run_api(tgt=settings.SITE_SALT_MASTER,
                                                arg='cd /etc/salt/pki/master/minions_denied/ && rm -rf %s' % minions)
            if response_data['status'] is False:
                response_data = {'results': '删除key失败', 'status': False}
                return Response(response_data)
            # 命令rm删除返回值为空，所以return值是[{}]这个值不是空哟所以没出现api失败就表示成功
            else:
                if tasks.saltkey_list():
                    response_data = {'results': '删除key成功', 'status': True}
                    return Response(response_data)
                else:
                    logger.error('删除denied的key在执行刷新saltkey操作即cron.py里的方法时候出错了')
                    response_data = {'results': '删除key失败', 'status': False}
                    return Response(response_data)


# --- minion管理 ---
# minion管理：列表显示，单独id字段列表显示，以及全局更新操作
class SaltMinionViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    list:
        SaltMinion列表信息

    retrieve:
        返回Minion_id字段列表,lookup字段随便输入,
        默认返回所有minion id列表，可以传递sys参数(windows或linux)来单独输出系统为windows的minion id列表或者linux的

    create:
        更新列表
            salt_minion_tag值为global_update_salt_minion_list

    """
    queryset = MinionList.objects.all()
    serializer_class = saltstack_serializers.SaltMinionSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filter_class = MinionListFilter

    # 自定义每页个数
    # pagination_class.page_size = 1

    # 可选的排序规则
    ordering_fields = ('minion_id', 'ip')

    # 动态选择serializer
    def get_serializer_class(self):
        if self.action == "list":
            return saltstack_serializers.SaltMinionSerializer
        elif self.action == "create":
            return saltstack_serializers.SaltMinionListUpdateSerializer
        return saltstack_serializers.SaltMinionSerializer

    def retrieve(self, request, *args, **kwargs):
        # 注意数据库sys字段首字母是大写的
        if request.query_params.get('sys') == 'windows':
            minion_id_list = MinionList.objects.filter(sys='Windows').order_by('create_date').values_list('minion_id', flat=True)
        elif request.query_params.get('sys') == 'linux':
            minion_id_list = MinionList.objects.filter(sys='Linux').order_by('create_date').values_list('minion_id', flat=True)
        else:
            minion_id_list = MinionList.objects.all().order_by('create_date').values_list('minion_id', flat=True)
        return Response({'results': list(minion_id_list), 'status': True})

    def create(self, request, *args, **kwargs):
        # 更新minion列表
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({'results': serializer.errors, 'status': False})
        if tasks.minion_list():
            return Response({'results': '更新成功', 'status': True})
        else:
            return Response({'results': '更新失败', 'status': False})


# minion管理：全局状态更新操作
class SaltMinionStateUpdateViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """

    create:
        更新状态
            salt_minion_tag值为global_update_salt_minion_status

    """
    serializer_class = saltstack_serializers.SaltMinionStateUpdateSerializer

    def create(self, request, *args, **kwargs):
        # 更新minion状态
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({'results': serializer.errors, 'status': False})
        minion_list = MinionList.objects.values_list('minion_id', flat=True)
        id_list = []
        with requests.Session() as s:
            saltapi = SaltAPI(session=s)
            # salt检测minion最准的方法salt-run manage.status
            response_data = saltapi.saltrun_manage_status_api()
            if response_data['status'] is False:
                logger.error(response_data)
                return Response(response_data)
            else:
                status_up = response_data['results']['return'][0]['up']
                for minion_id in status_up:
                    updated_values = {'minion_id': minion_id, 'minion_status': '在线',
                                      'update_time': datetime.datetime.now()}
                    MinionList.objects.update_or_create(minion_id=minion_id, defaults=updated_values)
                status_down = response_data['results']['return'][0]['down']
                for minion_id in status_down:
                    updated_values = {'minion_id': minion_id, 'minion_status': '离线',
                                      'update_time': datetime.datetime.now()}
                    MinionList.objects.update_or_create(minion_id=minion_id, defaults=updated_values)
                id_list.extend(status_up)
                id_list.extend(status_down)
                for minion_id in minion_list:
                    if minion_id not in id_list:
                        MinionList.objects.filter(minion_id=minion_id).delete()
                return Response({'results': '更新成功', 'status': True})


# minion管理单个minion更新操作
class SaltMinionUpdateViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """

    create:
        更新单个minion
            salt_minion_tag值为update_salt_minion
            minion_id值为单个minion_id

    """
    serializer_class = saltstack_serializers.SaltMinionUpdateSerializer

    def create(self, request, *args, **kwargs):
        # 单minion更新
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({'results': serializer.errors, 'status': False})
        minion_id = request.data.get('minion_id')
        with requests.Session() as s:
            saltapi = SaltAPI(session=s)
            response_data = saltapi.test_api(tgt=minion_id)
            if response_data['status'] is False:
                logger.error(response_data)
                return Response(response_data)
            else:
                # 结果类似：{'192.168.68.51': False, '192.168.68.1': True, '192.168.68.50-master': True}
                # 所以直接if判断true false
                if response_data['results'][minion_id]:
                    try:
                        grains_data = saltapi.grains_itmes_api(tgt=minion_id)
                        # 这里获取了所有minion的grains内容，如果以后表字段有增加就从这里取方便
                        value = grains_data['results']['return'][0][minion_id]
                        try:
                            value['ipv4'].remove('127.0.0.1')
                        except Exception as e:
                            pass
                        try:
                            MinionList.objects.filter(minion_id=minion_id).update(minion_status='在线',
                                                                                  ip=value.get('ipv4'),
                                                                                  sn=value.get('serialnumber'),
                                                                                  cpu_num=value.get('num_cpus'),
                                                                                  cpu_model=value.get('cpu_model'),
                                                                                  sys=value.get('kernel'),
                                                                                  kernel=value.get('kernelrelease'),
                                                                                  product_name=value.get('productname'),
                                                                                  ipv4_address=value.get(
                                                                                      'ip4_interfaces'),
                                                                                  mac_address=value.get(
                                                                                      'hwaddr_interfaces'),
                                                                                  localhost=value.get('localhost'),
                                                                                  mem_total=value.get('mem_total'),
                                                                                  minion_version=value.get(
                                                                                      'saltversion'),
                                                                                  system_issue=value.get(
                                                                                      'os') + value.get('osrelease'),
                                                                                  update_time=datetime.datetime.now())
                        except Exception as e:
                            # 有出现过某个minion的依赖文件被删除了但是minion进程还在，导致grains.items没有结果返回
                            # 这样就会出现vlaue不是一个字典而是是一个str正常value内容是{'ipv4':'xxxxx'}异常时候会是'grains.items is false'
                            # 具体是什么str没记住哈哈，不过由于不少字典而又用了get来获取字典值所以会触发try的错误，也就有了下面的操作
                            logger.error('单minion更新数据出错0，请检查'+ str(e))
                            MinionList.objects.filter(minion_id=minion_id).update(minion_status='异常',
                                                                                  update_time=datetime.datetime.now())
                    except Exception as e:
                        logger.error('单minion更新数据出错1，请检查' + str(e))
                        return Response({'results': '单minion更新数据出错1，请检查' + str(e), 'status': False})
                else:
                    try:
                        # minion离线
                        MinionList.objects.filter(minion_id=minion_id).update(minion_status='离线',
                                                                              update_time=datetime.datetime.now())
                    except Exception as e:
                        logger.error('单minion更新数据出错2，请检查' + str(e))
                        return Response({'results': '单minion更新数据出错2，请检查' + str(e), 'status': False})
                return Response({'results': '更新成功', 'status': True})


# --- salt命令集管理
# salt命令集管理：列表显示，命令收集操作
class SaltCmdViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    list:
        Salt命令集列表信息

    create:
        收集salt命令集操作
            salt_cmd_tag值为collection_info
            collection_style值为module、state、runner中的一个
            minions值为"minion_id1,minion_id2,....."

    """
    queryset = SaltCmdInfo.objects.all()
    serializer_class = saltstack_serializers.SaltCmdSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter)
    filter_fields = ('salt_cmd_type', 'salt_cmd_module', 'salt_cmd')

    # 搜索框
    search_fields = ('salt_cmd',)

    # 可选的排序规则
    ordering_fields = ('id', 'salt_cmd', 'salt_cmd_type')

    # 动态选择serializer
    def get_serializer_class(self):
        if self.action == "list":
            return saltstack_serializers.SaltCmdSerializer
        elif self.action == "create":
            return saltstack_serializers.SaltCmdPostSerializer
        return saltstack_serializers.SaltCmdSerializer

    def create(self, request, *args, **kwargs):
        # 收集salt命令集操作
        # 以前salt接受多个minion不是正常的列表['a','b','c']而是'a,b,c'，但是现在是了
        minions = request.data.get('minions')
        collection_style = request.data.get('collection_style')
        try:
            with requests.Session() as s:
                saltapi = SaltAPI(session=s)
                if collection_style == 'state':
                    response_data = saltapi.sys_state_doc_api(tgt=minions, tgt_type='list')
                elif collection_style == 'runner':
                    response_data = saltapi.sys_runner_doc_api(tgt=minions, tgt_type='list')
                else:
                    response_data = saltapi.sys_doc_api(tgt=minions, tgt_type='list')
                # 当调用api失败的时候会返回false
                if response_data['status'] is False:
                    logger.error(response_data)
                    return Response(response_data)
                else:
                    response_data = response_data['results']['return'][0]
                    try:
                        # 用来存放掉线或者访问不到的minion_id信息
                        info = ''
                        # state的使用帮助特殊，比如cmd.run会有一个头cmd的说明，所以要对cmd这样做一个处理把他加入到cmd.run的使用帮助中
                        if collection_style == 'state':
                            a = {}
                            b = {}
                            for minion_id, cmd_dict in response_data.items():
                                if isinstance(cmd_dict, dict):
                                    for salt_cmd, salt_cmd_doc in cmd_dict.items():
                                        if len(salt_cmd.split('.')) == 1:
                                            a[salt_cmd] = salt_cmd_doc
                                        else:
                                            b[salt_cmd] = salt_cmd_doc
                                    for salt_cmd in b.keys():
                                        try:
                                            b[salt_cmd] = salt_cmd.split('.')[0] + ':\n' + str(
                                                a[salt_cmd.split('.')[0]]).replace('\n',
                                                                                   '\n    ') + '\n\n' + salt_cmd + ':\n' + str(
                                                b[salt_cmd])
                                        except Exception as e:
                                            logger.error('state采集后台错误：' + str(e))
                                            return Response({'results': 'state采集后台错误：' + str(e), 'status': False})
                                        updated_values = {'salt_cmd': salt_cmd,
                                                          'salt_cmd_type': collection_style,
                                                          'salt_cmd_module': salt_cmd.split('.')[0],
                                                          'salt_cmd_source': minion_id,
                                                          'salt_cmd_doc': b[salt_cmd],
                                                          'update_time': datetime.datetime.now()}
                                        SaltCmdInfo.objects.update_or_create(salt_cmd=salt_cmd,
                                                                             salt_cmd_type=collection_style,
                                                                             defaults=updated_values)
                                elif isinstance(cmd_dict, bool):
                                    info += ' 不过minion_id:' + minion_id + '掉线了没有从它采集到数据'
                            return Response({'results': '采集完成' + info, 'status': True})
                        else:
                            for minion_id, cmd_dict in response_data.items():
                                if isinstance(cmd_dict, dict):
                                    for salt_cmd, salt_cmd_doc in cmd_dict.items():
                                        salt_cmd_doc = str(salt_cmd) + ':\n' + str(salt_cmd_doc)
                                        updated_values = {'salt_cmd': salt_cmd,
                                                          'salt_cmd_type': collection_style,
                                                          'salt_cmd_module': salt_cmd.split('.')[0],
                                                          'salt_cmd_source': minion_id,
                                                          'salt_cmd_doc': salt_cmd_doc,
                                                          'update_time': datetime.datetime.now()}
                                        SaltCmdInfo.objects.update_or_create(salt_cmd=salt_cmd,
                                                                             salt_cmd_type=collection_style,
                                                                             defaults=updated_values)
                                elif isinstance(cmd_dict, bool):
                                    info += ' 不过minion_id:' + minion_id + '掉线了没有从它采集到数据'
                            return Response({'results': '采集完成' + info, 'status': True})
                    except Exception as e:
                        logger.error('采集后台错误：' + str(e))
                        return Response({'results': '采集后台错误：' + str(e), 'status': False})
        except Exception as e:
            logger.error('采集信息出错：' + str(e))
            return Response({'results': '采集信息出错：' + str(e), 'status': False})


# salt命令集管理：删除操作
class SaltCmdDeleteViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """

    create:
        删除操作
            salt_cmd_tag值为salt_cmd_delete

    """
    serializer_class = saltstack_serializers.SaltCmdDeleteSerializer

    def create(self, request, *args, **kwargs):
        # 清空salt命令集表
        result = {'results': None, 'status': False}
        try:
            SaltCmdInfo.objects.all().delete()
            result['results'] = '清空成功'
            result['status'] = True
        except Exception as e:
            message = '清空失败', str(e)
            logger.error(message)
            result['results'] = message
        return Response(result)


# salt命令集管理：返回salt命令集不同类型下的所有模块module去重列表
class SaltCmdModuleListViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """

    list:
        返回salt命令集不同类型下的所有模块去重列表,必须带过滤条件

    """

    serializer_class = saltstack_serializers.SaltCmdModuleListSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('salt_cmd_type',)
    # 这个要取消分页，因为我需要返回所有
    pagination_class = None

    def get_queryset(self):
        salt_cmd_type = self.request.GET.get('salt_cmd_type')
        queryset = SaltCmdInfo.objects.filter(salt_cmd_type=salt_cmd_type).values('salt_cmd_module').distinct().order_by('salt_cmd_module')
        return queryset


# salt命令集管理：返回salt命令集不同类型不同模块下cmd命令的列表
class SaltCmdCmdleListViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """

    list:
        返回salt命令集不同类型不同模块下cmd命令的列表,必须带过滤条件

    """

    serializer_class = saltstack_serializers.SaltCmdCmdListSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('salt_cmd_type', 'salt_cmd_module')
    # 返回所有，所以取消分页
    pagination_class = None

    def get_queryset(self):
        salt_cmd_type = self.request.GET.get('salt_cmd_type')
        salt_cmd_module = self.request.GET.get('salt_cmd_module')
        queryset = SaltCmdInfo.objects.filter(salt_cmd_type=salt_cmd_type, salt_cmd_module=salt_cmd_module).values(
            'salt_cmd').order_by('salt_cmd')
        return queryset


# --- salt命令执行
# salt命令执行操作
class SaltExeViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """

    create:
        执行salt命令操作
            salt_exe_tag值为salt_exe

    """
    serializer_class = saltstack_serializers.SaltExeSerializer

    def create(self, request, *args, **kwargs):
        # 执行salt命令操作
        client = request.data.get('client')
        # drf的request.data.get可以直接获取到list类型
        arg = request.data.get('arg')
        tgt = request.data.get('tgt')
        tgt_type = request.data.get('tgt_type')
        fun = request.data.get('fun')

        try:
            if client != 'runner':
                data = {'client': client, 'tgt': tgt, 'tgt_type': tgt_type, 'fun': fun, 'arg': arg}
            else:
                data = {'client': client, 'fun': fun, 'arg': arg}
            with requests.Session() as s:
                saltapi = SaltAPI(session=s)
                response_data = saltapi.public(data=data)
                # 当调用api失败的时候会返回false
                if response_data is False:
                    return Response({'results': '\nsalt命令执行后台出错_error(1)，请联系管理员', 'status': False})
                else:
                    try:
                        response_data = response_data['return'][0]
                        return Response({'results': response_data, 'status': True})
                    except Exception as e:
                        return Response({'results': '\n' + 'salt命令执行失败_error(2):' + str(response_data), 'status': False})
        except Exception as e:
            logger.error('salt命令执行后台出错_error(2)：' + str(e))
            return Response({'results': 'salt命令执行后台出错_error(2)：' + str(e), 'status': False})


# --- salt快捷工具
# 任务查询 状态查询操作
class SaltToolJobStatusViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """

    create:
        任务查询 状态查询操作
            salt_tool_tag值为search_jid_status
            jid值为要查询的jid

    """
    serializer_class = saltstack_serializers.SaltToolJobStatusSerializer

    def create(self, request, *args, **kwargs):
        jid = request.data.get('jid')
        try:
            with requests.Session() as s:
                saltapi = SaltAPI(session=s)
                response_data = saltapi.job_exit_success_api(jid=jid)
                # 当调用api失败的时候会返回false
                if response_data['status'] is False:
                    logger.error(response_data)
                    return Response(response_data)
                else:
                    try:
                        response_data = response_data['results']['return'][0]
                        return Response({'results': response_data, 'status': True})
                    except Exception as e:
                        return Response({'results': '\n' + 'salt快捷工具命令执行任务状态查询失败_error(1):' + str(response_data), 'status': False})
        except Exception as e:
            logger.error('salt快捷工具命令执行任务状态查询后台出错_error(2)：' + str(e))
            return Response({'results': 'salt快捷工具命令执行任务状态查询后台出错_error(3)：' + str(e), 'status': False})


# 任务查询 结果查询操作
class SaltToolJobResultViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """

    create:
        任务查询 结果查询操作
            salt_tool_tag值为search_jid_result
            jid值为要查询的jid

    """
    serializer_class = saltstack_serializers.SaltToolJobResultSerializer

    def create(self, request, *args, **kwargs):
        jid = request.data.get('jid')
        try:
            with requests.Session() as s:
                saltapi = SaltAPI(session=s)
                response_data = saltapi.jid_api(jid=jid)
                # 当调用api失败的时候会返回false
                if response_data['status'] is False:
                    logger.error(response_data)
                    return Response(response_data)
                else:
                    try:
                        response_data = response_data['results']['return'][0]
                        return Response({'results': response_data, 'status': True})
                    except Exception as e:
                        return Response({'results': '\n' + 'salt快捷工具命令执行任务结果查询失败_error(1):' + str(response_data), 'status': False})
        except Exception as e:
            logger.error('salt快捷工具命令执行任务结果查询后台出错_error(2)：' + str(e))
            return Response({'results': 'salt快捷工具命令执行任务结果查询后台出错_error(3)：' + str(e), 'status': False})


# --- 文件管理
# 文件管理 查树状目录
class FileTreeViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    文件管理 查树状目录

    """
    serializer_class = saltstack_serializers.FileeManageTreeSerializer

    def create(self, request, *args, **kwargs):
        # 这里留了一个口，可以传递目录进来查询，不过实际前端并不需要传递，下面直接通过salt获取到目录了
        base_path = request.query_params.get('base_path')
        # 获取file_roots的base目录列表，正常是返回{'return': [['/srv/salt', 'xxxxxx']]}
        if not hasattr(settings, 'SITE_SALT_FILE_ROOTS'):
            with requests.Session() as s:
                saltapi = SaltAPI(session=s)
                response_data = saltapi.saltrun_file_roots_api()
                # 当调用api失败的时候会返回false
                if response_data['status'] is False:
                    logger.error(response_data)
                    return Response(response_data)
                else:
                    try:
                        # 结果是一个目录的列表
                        settings.SITE_SALT_FILE_ROOTS = response_data['results']['return'][0]
                    except Exception as e:
                        return Response({'results': '文件管理执行文件目录查询失败_error(1):' + str(response_data), 'status': False})
        file_roots_base = settings.SITE_SALT_FILE_ROOTS
        if not base_path:
            base_path = file_roots_base[0]
        elif base_path.rstrip('/') not in file_roots_base:
            return Response({'results': '非法目录', 'status': False})
        with requests.Session() as s:
            saltapi = SaltAPI(session=s)
            response_data = saltapi.find_find_api(tgt=settings.SITE_SALT_MASTER, arg=['path=%s' % base_path.rstrip('/'), 'print=path,type,size'])
            # 当调用api失败的时候会返回false
            if response_data['status'] is False:
                logger.error(response_data)
                return Response(response_data)
            else:
                try:
                    response_path = response_data['results']['return'][0][settings.SITE_SALT_MASTER]
                except Exception as e:
                    return Response(
                        {'results': '文件管理执行文件目录查询失败_error(2):' + str(response_data), 'status': False})
        # 返回的树状目录列表，下面是按照salt的find命令得到的内容做了处理最终变成一个树状列表，太难了奶奶的搞了好久才想出来
        b = len(response_path)
        for i in range(b):
            path = response_path[i][0]
            # 把路径/srv/salt部分替换为空
            repath = re.sub(r"^%s" % base_path.rstrip('/'), "", path, 1)
            # 分割剩下的路径
            data = repath.split('/')[1:]
            response_path[i] = {'label': data[-1] if data else data, 'type': response_path[i][1], 'id': i + 1,
                                'size': response_path[i][2], 'floor': len(data), 'full_path': path}
            if response_path[i]['floor'] == 0:
                response_path[i]['label'] = base_path.rstrip('/')
            else:
                floor = response_path[i]['floor'] - 1
                check = 1
                count = i
                while count:
                    # 获取前一个的层数floor
                    before_floor = response_path[i - check]['floor']
                    # 获取前一个的最后一个路径
                    before_path = (response_path[i - check]['full_path']).split('/')[-1]
                    # 如果这个路径的层数和floor的一样其实就是比现在上一层哈，并且路径也要一样的就匹配，不然继续往上,
                    # 注意floor等0不需要判断路径了因为等0下面的data[-2]根本没有会报错
                    if before_floor == floor == 0 or (before_floor == floor and data[-2] == before_path):
                        if response_path[i - check].get('children'):
                            response_path[i - check]['children'].append(response_path[i])
                        else:
                            response_path[i - check]['children'] = [response_path[i]]
                        count = 0
                    else:
                        check += 1
                        count -= 1
        if not len(response_path):
            return Response({'results': '文件管理执行文件目录查询失败,请确认base目录是否存在', 'status': False})
        # 多返回一个max_id，主要是前端创建文件或者文件夹的时候需要用到id，避免下重复
        return Response({'results': [response_path[0]], 'max_id': b, 'max_size': settings.SITE_MAX_FILE_SIZE, 'status': True})


# 文件管理 文件内容查看
class FileContentViewSet(viewsets.GenericViewSet):
    """
    文件管理 文件内容查看
    """

    serializer_class = saltstack_serializers.FileManageContentSerializer

    # 自定义查看文件内容方法
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            response_data = {'results': serializer.errors, 'status': False}
            return Response(response_data)
        file_path = serializer.validated_data.get('file_path')
        file_size = serializer.validated_data.get('file_size')
        file_type = serializer.validated_data.get('file_type')
        # 返回的是5242880 btyes换算成兆5M,大于5M限制打开,如果后期频繁修改建议入库弄个表记录大小,然后弄个页面调整打开大小
        if str(file_size).isdigit() and int(str(file_size)) > settings.SITE_MAX_FILE_SIZE:
            return Response(
                {'results': '文件超过5M太大无法打开，需调整上限请联系管理员', 'status': False})
        elif file_type != 'f':
            return Response(
                {'results': '文件读取失败，请确认是文件夹还是文件', 'status': False})
        with requests.Session() as s:
            saltapi = SaltAPI(session=s)
            response_data = saltapi.file_read_api(tgt=settings.SITE_SALT_MASTER, arg=file_path)
            # 当调用api失败的时候会返回false
            if response_data['status'] is False:
                logger.error(response_data)
                return Response(response_data)
            else:
                try:
                    file_content = response_data['results']['return'][0][settings.SITE_SALT_MASTER]
                except Exception as e:
                    return Response(
                        {'results': '文件读取失败_error(1):' + str(response_data), 'status': False})
        return Response({'results': file_content, 'status': True})


# 文件管理 文件内容更新
class FileUpdateViewSet(viewsets.GenericViewSet):
    """
    文件内容更新

    """

    serializer_class = saltstack_serializers.FileManageUpdateSerializer

    # 自定义更新文件方法
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            response_data = {'results': serializer.errors, 'status': False}
            return Response(response_data)
        file = serializer.validated_data.get('file')
        file_name = serializer.validated_data.get('file_name')
        # file_path是包含文件名的全路径
        file_path = serializer.validated_data.get('file_path')
        file_name = file_name + '_' + datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        tmp_path = os.path.join(settings.SITE_BASE_TMP_PATH,  '%s' % file_name)
        try:
            with requests.Session() as s:
                saltapi = SaltAPI(session=s)
                # 如果master和rsync服务器和web服务器是同一台则直接保存到对应的文件位置即可,其实只要master和web同台即可不过为了后面判断
                # 所以直接先判断3个都同台
                if settings.SITE_WEB_MINION == settings.SITE_RSYNC_MINION == settings.SITE_SALT_MASTER:
                    try:
                        with open('%s' % file_path, 'w') as f:
                            f.write(file)
                    except FileNotFoundError:
                        os.makedirs(os.path.dirname(file_path))
                        with open('%s' % file_path, 'w') as f:
                            f.write(file)
                else:
                    try:
                        with open('%s' % tmp_path, 'w') as f:
                            f.write(file)
                    except FileNotFoundError:
                        os.makedirs(settings.SITE_BASE_TMP_PATH)
                        with open('%s' % tmp_path, 'w') as f:
                            f.write(file)
                    # rsync服务器和web服务器是同一台则先存入rsync的daemon指定的目录中即tmp_path里然后同步到master
                    # 注意tmp_path是通过settings.SITE_BASE_TMP_PATH生成的settings.SITE_BASE_TMP_PATH要在rsync的daemon中存在
                    if settings.SITE_WEB_MINION == settings.SITE_RSYNC_MINION:
                        # 下面有一个xpgg_tmp是rsync定义的文件源，记得要和rsync服务端daemo里一致
                        response_data = saltapi.rsync_rsync_api(tgt=settings.SITE_SALT_MASTER, arg=[
                            'src=rsync://{ip}:{port}/xpgg_tmp/{file_name}'.format(ip=settings.SITE_RSYNC_IP,
                                                                                  port=settings.SITE_RSYNC_PORT,
                                                                                  file_name=file_name),
                            'dst={file_path}'.format(file_path=file_path)])
                    # 如果rsync服务和web服务器和master服务器3个都是独立的，则web服务器也需要开启rsync的daemon，然后把文件先存入web服务器的
                    # rsync对应目录中，master从web服务器去拉取这个文件即可
                    else:
                        # 下面有一个xpgg_tmp是rsync定义的文件源，记得要和rsync服务端daemo里一致
                        response_data = saltapi.rsync_rsync_api(tgt=settings.SITE_SALT_MASTER, arg=[
                            'src=rsync://{ip}:{port}/xpgg_tmp/{file_name}'.format(ip=settings.SITE_WEB_RSYNC_IP,
                                                                                  port=settings.SITE_WEB_RSYNC_PORT,
                                                                                  file_name=file_name),
                            'dst={file_path}'.format(file_path=file_path)])
                    # 当调用api失败的时候会返回false，并删除临时文件
                    if response_data['status'] is False:
                        logger.error(response_data)
                        os.remove(tmp_path)
                        return Response(response_data)
                    else:
                        try:
                            data = response_data['results']['return'][0][settings.SITE_SALT_MASTER]
                            if data.get('retcode') != 0:
                                return Response({'results': '更新文件在同步时失败_error(0):' + str(data['stderr']), 'status': False})
                        except Exception as e:
                            return Response({'results': '更新文件在同步时失败_error(1):' + str(e), 'status': False})
                        finally:
                            os.remove(tmp_path)
        except Exception as e:
            return Response({'results': '更新文件失败_error(2):' + str(e), 'status': False})
        return Response({'results': '更新成功', 'status': True})


# 文件管理 创建文件或者文件夹
class FileCreateViewSet(viewsets.GenericViewSet):
    """
    创建文件或者文件夹

    """

    serializer_class = saltstack_serializers.FileManageCreateSerializer

    # 自定义创建文件或者文件夹
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            response_data = {'results': serializer.errors, 'status': False}
            return Response(response_data)
        file_path = serializer.validated_data.get('file_path')
        file_type = serializer.validated_data.get('file_type')
        with requests.Session() as s:
            saltapi = SaltAPI(session=s)
            if file_type == 'd':
                response_data = saltapi.file_mkdir_api(tgt=settings.SITE_SALT_MASTER, arg=file_path)
            else:
                response_data = saltapi.file_touch_api(tgt=settings.SITE_SALT_MASTER, arg=file_path)
            # 当调用api失败的时候会返回false
            if response_data['status'] is False:
                logger.error(response_data)
                return Response(response_data)
            else:
                try:
                    response_data = response_data['results']['return'][0][settings.SITE_SALT_MASTER]
                    if response_data is True:
                        return Response({'results': '创建成功', 'status': True})
                    else:
                        return Response({'results': '创建失败，error:%s' % response_data, 'status': False})
                except Exception as e:
                    return Response(
                        {'results': '文件读取失败_error(1):' + str(response_data), 'status': False})


# 文件管理 重命名文件或者文件夹
class FileRenameViewSet(viewsets.GenericViewSet):
    """
    重命名文件或者文件夹

    """

    serializer_class = saltstack_serializers.FileManageRenameSerializer

    # 自定义重命名文件或者文件夹
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            response_data = {'results': serializer.errors, 'status': False}
            return Response(response_data)
        old_name = serializer.validated_data.get('old_name')
        new_name = serializer.validated_data.get('new_name')
        with requests.Session() as s:
            saltapi = SaltAPI(session=s)
            response_data = saltapi.file_rename_api(tgt=settings.SITE_SALT_MASTER, arg=[old_name, new_name])
            # 当调用api失败的时候会返回false
            if response_data['status'] is False:
                logger.error(response_data)
                return Response(response_data)
            else:
                try:
                    response_data = response_data['results']['return'][0][settings.SITE_SALT_MASTER]
                    if response_data is True:
                        return Response({'results': '重命名成功', 'status': True})
                    else:
                        return Response({'results': '重命名失败，error:%s' % response_data, 'status': False})
                except Exception as e:
                    return Response(
                        {'results': '重命名失败_error(1):' + str(response_data), 'status': False})


# 文件管理 删除文件或者文件夹
class FileDeleteViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    删除文件或者文件夹

    """

    serializer_class = saltstack_serializers.FileManageDeleteSerializer

    # 删除文件
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            response_data = {'results': serializer.errors, 'status': False}
            return Response(response_data)
        file_path = serializer.validated_data.get('file_path')
        with requests.Session() as s:
            saltapi = SaltAPI(session=s)
            response_data = saltapi.file_remove_api(tgt=settings.SITE_SALT_MASTER, arg=[file_path])
            # 当调用api失败的时候会返回false
            if response_data['status'] is False:
                logger.error(response_data)
                return Response(response_data)
            else:
                try:
                    response_data = response_data['results']['return'][0][settings.SITE_SALT_MASTER]
                    if response_data is True:
                        return Response({'results': '删除成功', 'status': True})
                    else:
                        return Response({'results': '删除失败，error:%s' % response_data, 'status': False})
                except Exception as e:
                    return Response(
                        {'results': '删除失败_error(1):' + str(response_data), 'status': False})


# 文件管理 上传文件
class FileUploadViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    上传文件

    """
    # 指定解释器是MultiPartParser可以解释上传多文件，单个可以用FileUploadParser,FormParser是解析表单使用，同常都是如下同事使用
    parser_classes = [FormParser, MultiPartParser]
    serializer_class = saltstack_serializers.FileManageUploadSerializer

    # 上传文件
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            response_data = {'results': serializer.errors, 'status': False}
            return Response(response_data)
        # 上传参考官网的FileUploadParser
        # 如果是多文件则使用request.FILES.getlist('file', None),然后通过for来提取单个文件
        # 并且文件字段不能序列化，因为序列化FileField只能接受一个文件
        file = request.data.get('file')
        file_name = file.name
        if file.size > settings.SITE_MAX_FILE_SIZE:
            return Response({'results': '上传文件失败: 文件大于5M，如需帮助请联系管理员', 'status': False})
        # file_path是不包含文件名的目的文件路径，所以要拼接
        file_path = serializer.validated_data.get('file_path')
        file_path = os.path.join(file_path,  '%s' % file_name)
        file_name = file_name + '_' + datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        tmp_path = os.path.join(settings.SITE_BASE_TMP_PATH,  '%s' % file_name)
        try:
            with requests.Session() as s:
                saltapi = SaltAPI(session=s)
                # 如果master和rsync服务器和web服务器是同一台则直接保存到对应的文件位置即可
                if settings.SITE_WEB_MINION == settings.SITE_RSYNC_MINION == settings.SITE_SALT_MASTER:
                    try:
                        with open('%s' % file_path, 'wb') as f:
                            # django读写文件流的方式，避免写入内存导致溢出
                            for chunk in file.chunks():
                                f.write(chunk)
                    except FileNotFoundError:
                        os.makedirs(os.path.dirname(file_path))
                        with open('%s' % file_path, 'wb') as f:
                            for chunk in file.chunks():
                                f.write(chunk)
                else:
                    try:
                        with open('%s' % tmp_path, 'wb') as f:
                            for chunk in file.chunks():
                                f.write(chunk)
                    except FileNotFoundError:
                        os.makedirs(settings.SITE_BASE_TMP_PATH)
                        with open('%s' % tmp_path, 'wb') as f:
                            for chunk in file.chunks():
                                f.write(chunk)
                    # rsync服务器和web服务器是同一台则先存入rsync的daemon指定的目录中即tmp_path里然后同步到master
                    if settings.SITE_WEB_MINION == settings.SITE_RSYNC_MINION:
                        # 下面有一个xpgg_tmp是rsync定义的文件源，记得要和rsync服务端daemo里一致
                        response_data = saltapi.rsync_rsync_api(tgt=settings.SITE_SALT_MASTER, arg=[
                            'src=rsync://{ip}:{port}/xpgg_tmp/{file_name}'.format(ip=settings.SITE_RSYNC_IP,
                                                                                  port=settings.SITE_RSYNC_PORT,
                                                                                  file_name=file_name),
                            'dst={file_path}'.format(file_path=file_path)])
                    # 如果rsync服务和web服务器和master服务器3个都是独立的，则web服务器也需要开启rsync的daemon，然后把文件先存入web服务器的
                    # rsync对应目录中，master从web服务器去拉取这个文件即可
                    else:
                        # 下面有一个xpgg_tmp是rsync定义的文件源，记得要和rsync服务端daemo里一致
                        response_data = saltapi.rsync_rsync_api(tgt=settings.SITE_SALT_MASTER, arg=[
                            'src=rsync://{ip}:{port}/xpgg_tmp/{file_name}'.format(ip=settings.SITE_WEB_RSYNC_IP,
                                                                                  port=settings.SITE_WEB_RSYNC_PORT,
                                                                                  file_name=file_name),
                            'dst={file_path}'.format(file_path=file_path)])
                    # 当调用api失败的时候会返回false，并删除临时文件
                    if response_data['status'] is False:
                        logger.error(response_data)
                        os.remove(tmp_path)
                        return Response(response_data)
                    else:
                        try:
                            data = response_data['results']['return'][0][settings.SITE_SALT_MASTER]
                            if data.get('retcode') != 0:
                                return Response({'results': '上传文件在同步时失败_error(0):' + str(data['stderr']), 'status': False})
                        except Exception as e:
                            return Response({'results': '上传文件在同步时失败_error(1):' + str(e), 'status': False})
                        finally:
                            os.remove(tmp_path)
        except Exception as e:
            return Response({'results': '上传文件失败_error(2):' + str(e), 'status': False})
        return Response({'results': '上传成功', 'status': True})
