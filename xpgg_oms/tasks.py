#!/usr/bin/env python3
#-.- coding=utf-8 -.-

import time
import datetime
from xpgg_oms.models import *
from xpgg_oms.salt_api import SaltAPI
import requests
import urllib3
from celery import shared_task, uuid, result
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import logging
logger = logging.getLogger('xpgg_oms.views')


@shared_task(bind=True, options={"task_id": "666666"})
def add(self, x, y):
    print('我是加法测试，会输出到celery日志中')
    print(self.AsyncResult(self.request.id).status)
    time.sleep(30)
    print(result.AsyncResult.status)
    # 下面这个能够获取到id
    print(self.request.id)
    print('测试看能不能配置task_id')
    return x + y


@shared_task(bind=True, name='命令')
def cmd(self, periodic_name='未命名', tgt='*', tgt_type='glob', execute_cmd=''):
    if tgt_type == 'list':
        tgt = [tgt]
    with requests.Session() as s:
        saltapi = SaltAPI(session=s)
        response_data = saltapi.cmd_run_api(tgt=tgt, tgt_type=tgt_type,
                                            arg=[execute_cmd, "shell='/bin/bash'",
                                                 "runas='root'"])
        # 当调用api失败的时候会返回false
        if response_data['status'] is False:
            return '任务执行后台出错_error(1)，请联系管理员'
        else:
            response_data = response_data['results']['return'][0]
            return response_data


def saltkey_list():
    salt_list = SaltKeyList.objects.values_list('minion_id', 'certification_status')
    minion_list = []
    with requests.Session() as s:
        saltapi = SaltAPI(session=s)
        response_data = saltapi.saltkey_listall_api()
        if not response_data['status']:
            logger.error('saltkey_list调用api失败，请检查api接口状态')
            return False
        try:
            data_source = response_data['results']['return'][0]['data']['return']
            minions_pre = data_source['minions_pre']
            minions_denied = data_source['minions_denied']
            minions = data_source['minions']
            minions_rejected = data_source['minions_rejected']
            if minions_pre:
                for i in minions_pre:
                    minion_list.append((i, 'unaccepted'))
                    updated_values = {'minion_id': i, 'certification_status': 'unaccepted',
                                      'update_time': datetime.datetime.now()}
                    SaltKeyList.objects.update_or_create(minion_id=i, certification_status='unaccepted', defaults=updated_values)
            if minions_denied:
                for i in minions_denied:
                    minion_list.append((i, 'denied'))
                    updated_values = {'minion_id': i, 'certification_status': 'denied',
                                      'update_time': datetime.datetime.now()}
                    SaltKeyList.objects.update_or_create(minion_id=i, certification_status='denied', defaults=updated_values)
            if minions:
                for i in minions:
                    minion_list.append((i, 'accepted'))
                    updated_values = {'minion_id': i, 'certification_status': 'accepted',
                                      'update_time': datetime.datetime.now()}
                    SaltKeyList.objects.update_or_create(minion_id=i, certification_status='accepted', defaults=updated_values)
            if minions_rejected:
                for i in minions_rejected:
                    minion_list.append((i, 'rejected'))
                    updated_values = {'minion_id': i, 'certification_status': 'rejected',
                                      'update_time': datetime.datetime.now()}
                    SaltKeyList.objects.update_or_create(minion_id=i, certification_status='rejected', defaults=updated_values)
            # 删除原表中不在本次查询结果里的记录，因为如果你删除了一个minion那么查询结果就没有这个minion了所以要从表中删除
            for i in salt_list:
                if i not in minion_list:
                    SaltKeyList.objects.filter(minion_id=i[0], certification_status=i[1]).delete()
            return True
        except Exception as e:
            logger.error('saltkey_list在执行数据库操作时候出错了：' + str(e))
            return False


def minion_list():
    # 用values_list配合flat=True得到minion_id的列表，用values_list获取的不是列表是QuerySet对象
    # 如果要执行append或者remove等list操作无法执行
    minion_list = MinionList.objects.values_list('minion_id', flat=True)
    id_list = []
    print('开始更新Minion列表'+time.strftime('%Y-%m-%d %X'))
    with requests.Session() as s:
        saltapi = SaltAPI(session=s)
        # salt检测minion最准的方法salt-run manage.status
        minion_data = saltapi.saltrun_manage_status_api()
        if minion_data['status'] is False:
            print(minion_data['results'])
            return False
        else:
            try:
                id_list.extend(minion_data['results']['return'][0]['up'])
                grains_data = saltapi.grains_itmes_api(tgt=id_list, tgt_type='list')
                # 这里获取了所有minion的grains内容，如果以后表字段有增加就从这里取方便
                for key, value in grains_data['results']['return'][0].items():
                    minion_id = key
                    try:
                        value['ipv4'].remove('127.0.0.1')
                    except Exception as e:
                        pass
                    try:
                        # 下面这段代码之前都是直接用cpu_model = value['cpu_model'] 后面发现centos6和7有的有这个key有的没有导致会
                        # 报错，所以改成用get来获取key安全哈哈
                        ip = value.get('ipv4')
                        os = value.get('os') + value.get('osrelease')
                        saltversion = value.get('saltversion')
                        sn = value.get('serialnumber')
                        cpu_num = value.get('num_cpus')
                        cpu_model = value.get('cpu_model')
                        sys = value.get('kernel')
                        kernel = value.get('kernelrelease')
                        productname = value.get('productname')
                        ipv4_addr = value.get('ip4_interfaces')
                        mac_addr = value.get('hwaddr_interfaces')
                        localhost = value.get('localhost')
                        mem_total = value.get('mem_total')
                    except Exception as e:
                        # 有出现过某个minion的依赖文件被删除了但是minion进程还在，导致grains.items没有结果返回
                        # 这样就会出现vlaue不是一个字典而是是一个str正常value内容是{'ipv4':'xxxxx'}异常时候会是'grains.items is false'
                        # 具体是什么str没记住哈哈，不过由于不少字典而又用了get来获取字典值所以会触发try的错误，也就有了下面的操作
                        updated_values = {'minion_id': key, 'minion_status': '异常',
                                          'update_time': datetime.datetime.now()}
                        MinionList.objects.update_or_create(minion_id=key, defaults=updated_values)
                    else:
                        updated_values = {'minion_id': minion_id, 'minion_status': '在线', 'ip': ip, 'sn': sn,
                                          'cpu_num': cpu_num, 'cpu_model': cpu_model, 'sys': sys, 'kernel': kernel,
                                          'product_name': productname, 'ipv4_address': ipv4_addr, 'mac_address': mac_addr,
                                          'localhost': localhost, 'mem_total': mem_total,
                                          'minion_version': saltversion, 'system_issue': os,
                                          'update_time': datetime.datetime.now()}
                        MinionList.objects.update_or_create(minion_id=key, defaults=updated_values)
            except Exception as e:
                print('minion列表更新在线数据出错1，请检查'+time.strftime('%Y-%m-%d %X'), e)
                return False
            try:
                # 更新离线minion状态
                for key in minion_data['results']['return'][0]['down']:
                    id_list.append(key)
                    updated_values = {'minion_id': key, 'minion_status': '离线',
                                      'update_time': datetime.datetime.now()}
                    MinionList.objects.update_or_create(minion_id=key, defaults=updated_values)
            except Exception as e:
                print('minion列表更新离线数据出错2，请检查' + time.strftime('%Y-%m-%d %X'), e)
                return False
        # 清理表中多出来的条目
        try:
            for i in minion_list:
                if i not in id_list:
                    MinionList.objects.filter(minion_id=i).delete()

                    # 下面这些本来是用来操作清理minion表后一些关联了minion的业务表也删除，但是后面想想我不动声响的后台去删除这些
                    # 表中的数据，对于使用人来说是很坑爹的事情，等下人家都不知道怎么minion就消失了，然后可能还会忘了到底原来是关联
                    # 那一个minion_id的，所以最后想了想还是不删除；业务逻辑中写判断minion是否存在，这样还有一个问题就是如果minion
                    # 清理后再重新添加回来，假设加回来的是另一台服务器那会造成业务系统之前绑定了这个minion的在操作的时候会操作错误
                    # 因为minion实际的后端服务器换了一台，所以要在规范上面来避免这问题，尽量小心删除salt-key操作，检查是否有关联
                    # 业务，或者后期看下需不需要下面的删除操作改成类似添加备注说明下被删除了

                    # # 对AppRelease中的minion_id做删除操作，因为这个表关联了minion表，不过我没用外键，所以要手动来
                    # # 下面是用正则匹配minion_id只有一个或者多个时候在前面在中间在最后的情况
                    # app_data_list = AppRelease.objects.filter(
                    #     minion_id__regex=r'^%s$|^%s,|,%s$|,%s,' % (i, i, i, i))
                    # for app_data in app_data_list:
                    #     app_name = app_data.app_name
                    #     minion_id = app_data.minion_id
                    #     minion_id = minion_id.split(',')
                    #     minion_id.remove(i)
                    #     minion_id = ','.join(minion_id)
                    #     AppRelease.objects.filter(app_name=app_name).update(minion_id=minion_id)
            print('minion列表更新完成' + time.strftime('%Y-%m-%d %X'))
            return True
        except Exception as e:
            logger.error('minion列表更新出错，请检查' + time.strftime('%Y-%m-%d %X')+str(e))
            print('minion列表更新出错，请检查' + time.strftime('%Y-%m-%d %X'), e)
            return False