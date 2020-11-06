#!/usr/bin/env python3
# -.- coding:utf-8 -.-

from django.conf import settings
import time

import logging

# Create your views here.
logger = logging.getLogger('xpgg_oms.views')


# 封装salt-api的调用
class SaltAPI(object):
    # 给获取token的几个参数设置默认值，这样如果真突然出现调用另一个salt-api的情况，直接把对应参数传入一样适用哈哈
    # 第一个参数session是为了给with as传入使用的，因为用with as会在程序执行完成后回收资源，不然Session是长连接占着连接不知道会不会造成影响后期
    def __init__(self, session, apiurl=settings.SITE_SALT_API_URL, username=settings.SITE_SALT_API_NAME,
                 password=settings.SITE_SALT_API_PWD, eauth='pam'):
        self.url = apiurl
        self.session = session
        self.username = username
        self.password = password
        self.eauth = eauth
        self.results = {'results': '', 'status': False}

    # 获取token
    def get_token(self):
        count = 2
        connect_test = 1
        while count:
            try:
                # 初始化获取api的token
                token = self.session.post(self.url + '/login',
                                          json={'username': self.username, 'password': self.password,
                                                'eauth': self.eauth, }, timeout=10)
                token.raise_for_status()
            except Exception as e:
                response_data = '第%s次尝试链接saltapi获取token失败:' % connect_test
                logger.error(response_data + str(e))
                count -= 1
                connect_test += 1
                time.sleep(4)
                continue
            else:
                return token.json()['return'][0]['token']
        # 比如当api服务忘了开就会false
        else:
            return False

    # 先做一个最通用的方法，就是不定义data的各个东西，在使用的时候定义好带入，好处是任何一个saltapi的操作都能支持，而且可以单独使用
    def public(self, data, message='public'):
        count = 2
        connect_test = 1
        status_code = 200
        while count:
            try:
                # 这里post操作里不用json格式而是用data是因为，我发现用json操作有不需要arg的时候我是把arg:None，用json会参数多余的错
                # 用data可以正常，用json的时候如果把arg=None的情况从提交里删除，就是不提交arg那也能正常，不过写通用方法比较麻烦感觉
                # 不过如果用arg:[]则data和json都可以正确识别，目前用data都正常，如果有异常再做变更
                headers = {'X-Auth-Token': settings.SITE_SALT_API_TOKEN}
                response_data = self.session.post(self.url, json=data, headers=headers)
                status_code = response_data.status_code
                response_data.raise_for_status()
            except Exception as e:
                response_data = '第%s次尝试SaltAPI调用%s请求出错' % (connect_test, message)
                logger.error(response_data + str(e))
                if status_code == 401:
                    token = self.get_token()
                    if token:
                        settings.SITE_SALT_API_TOKEN = token
                    else:
                        return False
                count -= 1
                connect_test += 1
                time.sleep(4)
                continue
            else:
                # 正确执行后返回值一般有这几种情况：
                # 1、返回需要的值，字典key是return值是[{xxx}]如{'return': [{'192.168.100.171': True}]}
                # 2、返回{'return': [{}]}，第一种没有这个minion_id，第二种是在使用salt-run jobs.lookup_jid任务结果还未返回时候也会如此
                # 出现这种情况说实话不好做判断，所以最好的办法是minion表要多实时刷新保持最新，从源头避免minion不存在的可能
                # 3、{'return': [{'192.168.100.170': False}]} 说明有这个minion_id但是连不上有可能停止了反正就是通不了哈
                # 同样的这种情况最好的办法不是在代码做判断，也是保持minion表中minion状态的实时在线离线，源头避免
                # 所以如果调用的时候有这种情况需要做下判断
                return response_data.json()
        else:
            return False

    # 封装test.ping,默认执行salt '*' test.ping
    def test_api(self, client='local', tgt='*', tgt_type='glob', fun='test.ping', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg
                }
        message = 'test_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        elif response_data['return'] != [{}]:
            # 正常结果类似这样：{'return': [{'192.168.68.51': False, '192.168.68.1': True, '192.168.68.50-master': True}]}
            data_source = response_data['return'][0]
            return {'results': data_source, 'status': True}
        else:
            # 这里用来匹配response_data['return'] == [{}] 情况
            return {'results': '检测失败,请确认minion是否存在。。', 'status': False}

    # 封装cmd.run,使用的时候只要代入tgt和arg即可，最多把tgt_type也代入
    def cmd_run_api(self, client='local', tgt='*', tgt_type='glob', fun='cmd.run', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'cmd_run_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装异步cmd.run,使用的时候只要代入tgt和arg即可，最多把tgt_type也代入
    def async_cmd_run_api(self, client='local_async', tgt='*', tgt_type='glob', fun='cmd.run', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'async_cmd_run_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装state.sls,使用的时候只要代入tgt和arg即可，最多把tgt_type也代入
    def state_api(self, client='local', tgt='*', tgt_type='glob', fun='state.sls', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'state_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装异步state.sls,使用的时候只要代入tgt和arg即可，最多把tgt_type也代入，得到结果为jid号
    def async_state_api(self, client='local_async', tgt='*', tgt_type='glob', fun='state.sls', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'async_state_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装通过jid查询任务执行状态，以便后续操作，返回[{}]表示执行完毕，返回数据表示还在执行
    def job_active_api(self, client='local', tgt='*', tgt_type='glob', fun='saltutil.find_job', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg
                }
        message = 'job_active_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装查询jid执行状态,使用的时候只要代入jid既可以，返回true表示执行结束并且成功退出，false表示没有成功或者还没执行完毕
    def job_exit_success_api(self, client='runner', fun='jobs.exit_success', jid=None):
        jid = [] if jid is None else jid
        data = {'client': client,
                'fun': fun,
                'jid': jid,
                }
        message = 'job_exit_success_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装查询jid结果方法,使用的时候只要代入jid既可以
    def jid_api(self, client='runner', fun='jobs.lookup_jid', jid=None):
        jid = [] if jid is None else jid
        data = {'client': client,
                'fun': fun,
                'jid': jid,
                }
        message = 'jid_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装archive.zip,使用的时候只要代入tgt和arg即可，最多把tgt_type也代入
    def archive_zip_api(self, client='local', tgt='*', tgt_type='glob', fun='archive.zip', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg
                }
        message = 'archive_zip_api'
        return self.public(data, message)

    # 封装archive.tar,使用的时候只要代入tgt和arg即可，最多把tgt_type也代入
    def archive_tar_api(self, client='local', tgt='*', tgt_type='glob', fun='archive.tar', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg
                }
        message = 'archive_tar_api'
        return self.public(data, message)

    # 封装cp.get_file,使用的时候只要代入tgt和arg即可，最多把tgt_type也代入
    def cp_get_file_api(self, client='local', tgt='*', tgt_type='glob', fun='cp.get_file', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'cp_get_file_api'
        return self.public(data, message)

    # 封装cp.get_dir,使用的时候只要代入tgt和arg即可，最多把tgt_type也代入
    def cp_get_dir_api(self, client='local', tgt='*', tgt_type='glob', fun='cp.get_dir', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'cp_get_dir_api'
        return self.public(data, message)

    # 封装salt-key -L
    def saltkey_listall_api(self, client='wheel', fun='key.list_all'):
        data = {'client': client,
                'fun': fun,
                }
        message = 'saltkey_listall_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装salt-key -d删除指令
    def saltkey_delete_api(self, client='wheel', fun='key.delete', match=None):
        match = [] if match is None else match
        data = {'client': client,
                'fun': fun,
                'match': match
                }
        message = 'saltkey_delete_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        # 正常结果类似这样{'return': [{'tag': 'salt/wheel/20190129171928278008',
        # 'data': {'jid': '20190129171928278008', 'return': {},
        # 'success': True, '_stamp': '2019-01-29T09:19:28.424270', 'tag': 'salt/wheel/20190129171928278008',
        # 'user': 'saltapi', 'fun': 'wheel.key.accept'}}]}
        # 这里面有一个'return': {}, 'success': True,里的success表示执行成功,如果是接受认证return里会有值这里是删除key里面都是空的。。
        # 所以不再做其他判断
        else:
            # 这里不做二次判断，只要不返还False就默认会成功，目前来看没有不会有什么问题
            return {'results': response_data, 'status': True}

    # 接受salt-key的方法奶奶的include_rejected和include_denied就算设置为True也无效测试发现！！
    def saltkey_accept_api(self, client='wheel', fun='key.accept', match=None, include_rejected=False,
                           include_denied=False):
        match = [] if match is None else match
        data = {'client': client,
                'fun': fun,
                'match': match,
                'include_rejected': include_rejected,
                'include_denied': include_denied
                }
        message = 'saltkey_accept_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        # 正常结果类似这样{'return': [{'tag': 'salt/wheel/20190129171928278008',
        # 'data': {'jid': '20190129171928278008', 'return': {'minions': ['172.17.0.2']},
        # 'success': True, '_stamp': '2019-01-29T09:19:28.424270', 'tag': 'salt/wheel/20190129171928278008',
        # 'user': 'saltapi', 'fun': 'wheel.key.accept'}}]}
        # 这里面有一个'return': {'minions': ['172.17.0.2']}, 'success': True,里的success表示执行成功，minions表示接受认证的id
        # 如果传了一个不存在的id进来也可以执行成功，但会是这样的结果'return': {}, 'success': True,
        # 如果传['*']表示接受所有，这个所有包括已经接受的key会再接受一次，返回结果不会是['*']而是['172.16.0.7-master', '172.17.0.2', 'php2']
        else:
            # 这里不做二次判断，只要不返还False就默认会成功，目前来看没有不会有什么问题
            return {'results': response_data, 'status': True}

    # 拒绝salt-key的方法奶奶的include_accepted和include_denied就算设置为True也无效测试发现！！
    def saltkey_reject_api(self, client='wheel', fun='key.reject', match=None, include_accepted=False,
                           include_denied=False):
        match = [] if match is None else match
        data = {'client': client,
                'fun': fun,
                'match': match,
                'include_accepted': include_accepted,
                'include_denied': include_denied
                }
        message = 'saltkey_reject_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            # 这里不做二次判断，只要不返还False就默认会成功，目前来看没有不会有什么问题
            return {'results': response_data, 'status': True}

    # salt-run manage.status 查看minion在线离线状态，速度比较慢但是没BUG不像salt-run manage.alived
    def saltrun_manage_status_api(self, client='runner', fun='manage.status', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'fun': fun,
                'arg': arg,
                }
        message = 'saltrun_manage_status_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            # 这里不做二次判断，只要不返还False就默认会成功，目前来看没有不会有什么问题
            return {'results': response_data, 'status': True}

    # salt-run manage.alived 查看在线的minion，非常快速方便可惜有bug后来启用(而且可以带参数show_ipv4=True获取到和master通信的ip是什么，默认False)
    def saltrun_manage_alive_api(self, client='runner', fun='manage.alived', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'fun': fun,
                'arg': arg,
                }
        message = 'saltrun_manage_alive_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # salt-run manage.not_alived 查看不在线的minion，非常快速方便可惜有bug后来启用
    def saltrun_manage_notalive_api(self, client='runner', fun='manage.not_alived', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'fun': fun,
                'arg': arg,
                }
        message = 'saltrun_manage_notalive_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装grains.itmes,使用的时候只要代入tgt和arg即可，最多把tgt_type也代入
    def grains_itmes_api(self, client='local', tgt='*', tgt_type='glob', fun='grains.items', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'grains_itmes_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装service.available查看服务是否存在Ture or False,使用的时候只要代入tgt和arg即可，最多把tgt_type也代入
    def service_available_api(self, client='local', tgt='*', tgt_type='glob', fun='service.available', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'service_available_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装service.status查看启动服务状态,使用的时候只要代入tgt和arg即可，最多把tgt_type也代入
    def service_status_api(self, client='local', tgt='*', tgt_type='glob', fun='service.status', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'service_status_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装service.start启动系统服务windows和linux通用，
    def service_start_api(self, client='local', tgt='*', tgt_type='glob', fun='service.start', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'service_start_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装service.stop停止系统服务windows和linux通用，salt '*' service.stop <service name>，由于有发现停止成功但是返回结果是
    # 一堆错误提示，所以最好使用的时候最后做一步service.status，返回服务状态True说明启动，False说明停止了
    def service_stop_api(self, client='local', tgt='*', tgt_type='glob', fun='service.stop', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'service_stop_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装ps.pgrep查看name的进程号windows和linux通用带模糊查询效果，
    def ps_pgrep_api(self, client='local', tgt='*', tgt_type='glob', fun='ps.pgrep', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'ps_pgrep_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装ps.proc_info通过进程号查看详细信息，
    # {'client':'local', 'tgt':'id','fun':'ps.proc_info', 'arg':['pid=123','attrs=["cmdline","pid","name","status"]']}
    def ps_proc_info_api(self, client='local', tgt='*', tgt_type='glob', fun='ps.proc_info', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'ps_proc_info_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装ps.kill_pid结束某个进程，{'client':'local','fun':'ps.kill_pid','tgt':'192.168.68.1', 'arg':['pid=11932']}
    def ps_kill_pid_api(self, client='local', tgt='*', tgt_type='glob', fun='ps.kill_pid', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'ps_kill_pid_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装task.create_task创建windows计划任务，salt '192.168.68.1' task.create_task ooxx  action_type=Execute
    # cmd='"C:\ooxx\Shadowsocks.exe"' force=true execution_time_limit=False  user_name=administrator
    def task_create_api(self, client='local', tgt='*', tgt_type='glob', fun='task.create_task', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'task_create_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装task.run启动windows计划任务，salt '192.168.100.171' task.run test1
    # ！坑！官方文档里命令是salt '192.168.100.171' task.list_run test1 根本就不行！
    def task_run_api(self, client='local', tgt='*', tgt_type='glob', fun='task.run', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'task_run_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装task.stop启动windows计划任务，salt '192.168.100.171' task.run test1
    def task_stop_api(self, client='local', tgt='*', tgt_type='glob', fun='task.stop', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'task_stop_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装file.mkdir,创建目录最后可以不需要/号，另一个file.makedirs则需要最后/，不然只创建到有/那一层这点也是可以利用的呵呵
    def file_mkdir_api(self, client='local', tgt='*', tgt_type='glob', fun='file.mkdir', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'file_mkdir_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装file.makedirs,创建目录最后可以需要/号，不然只创建到有/那一层这点也是可以利用的呵呵
    def file_makedirs_api(self, client='local', tgt='*', tgt_type='glob', fun='file.makedirs', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'file_makedirs_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装file.touch,同命令行touch命令
    def file_touch_api(self, client='local', tgt='*', tgt_type='glob', fun='file.touch', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'file_touch_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装file.rename,修改文件或者文件夹名称arg=[src,dst]
    def file_rename_api(self, client='local', tgt='*', tgt_type='glob', fun='file.rename', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'file_rename_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装file_exists,检查文件是否存在
    def file_exists_api(self, client='local', tgt='*', tgt_type='glob', fun='file.file_exists', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'file_exists_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装file_write,写入文件
    def file_write_api(self, client='local', tgt='*', tgt_type='glob', fun='file.write', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'file_write_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装file.remove,移除文件，如果是目录则递归删除
    def file_remove_api(self, client='local', tgt='*', tgt_type='glob', fun='file.remove', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'file_remove_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装file.directory_exists,检测目录是否存在返回True/False
    def file_directory_exists_api(self, client='local', tgt='*', tgt_type='glob', fun='file.directory_exists',
                                  arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'file_directory_exists_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装file.symlink,创建软连接
    def file_symlink_api(self, client='local', tgt='*', tgt_type='glob', fun='file.symlink', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'file_symlink_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装file.diskusage,创建软连接
    def file_diskusage_api(self, client='local', tgt='*', tgt_type='glob', fun='file.diskusage', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'file_diskusage_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装file.read,读取文件内容
    def file_read_api(self, client='local', tgt='*', tgt_type='glob', fun='file.read', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'file_read_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装supervisord.status,检测supervisor守护名称的状态，返回结果有这几种情况：
    # 1、没这个命令，salt需要安装supervisor才能用{'return': [{'192.168.100.171': "'supervisord.status' is not available."}]}
    # 2、没这个守护名称{'return': [{'192.168.68.50-master': {'1:': {'reason': '(no such process)', 'state': 'ERROR'}}}]}
    # 3、安装了supervisor但是没启动{'return': [{'192.168.100.170': {'unix:///var/run/supervisor/supervisor.sock': {'reason'
    # : 'such file', 'state': 'no'}}}]}
    # 4、正常获取结果的情况：
    # 启动{'return': [{'192.168.68.50-master': {'djangoproject.runserver': {'state': 'RUNNING', 'reason': 'pid 1233,
    #  uptime 1 day, 6:56:14'}}}]}
    # 停止{'return': [{'192.168.100.170': {'test': {'state': 'STOPPED', 'reason': 'Dec 13 05:23 PM'}}}]}
    def supervisord_status_api(self, client='local', tgt='*', tgt_type='glob', fun='supervisord.status', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'supervisord_status_api'
        return self.public(data, message)

    # 封装supervisord.stop,停止supervisor守护名称，返回结果除了上面status的前面3中情况还有以下几种情况：
    # 1、程序已经停止情况：{'return': [{'192.168.100.170': 'test: ERROR (not running)'}]}
    # 2、正常停止：{'return': [{'192.168.100.170': 'test: stopped'}]}
    # 3、没这个程序名称{'return': [{'192.168.100.170': 'test1: ERROR (no such process)'}]}
    def supervisord_stop_api(self, client='local', tgt='*', tgt_type='glob', fun='supervisord.stop', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'supervisord_stop_api'
        return self.public(data, message)

    # 封装supervisord.start,启动supervisor守护名称，返回结果有这几种情况：
    # 1、正常启动：{'return': [{'192.168.100.170': 'test: started'}]}
    # 2、已经启动过了{'return': [{'192.168.100.170': 'test: ERROR (already started)'}]}
    # 3、没这个程序名称{'return': [{'192.168.100.170': 'test1: ERROR (no such process)'}]}
    def supervisord_start_api(self, client='local', tgt='*', tgt_type='glob', fun='supervisord.start', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'supervisord_start_api'
        return self.public(data, message)

    # supervisord配置重载会启动新添加的程序
    def supervisord_update_api(self, client='local', tgt='*', tgt_type='glob', fun='supervisord.update', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'supervisord_update_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装rsync.rsync同步命令
    def rsync_rsync_api(self, client='local', tgt='*', tgt_type='glob', fun='rsync.rsync', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'rsync_rsync_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装异步rsync.rsync同步命令
    def async_rsync_rsync_api(self, client='local_async', tgt='*', tgt_type='glob', fun='rsync.rsync', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'async_rsync_rsync_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装sys.doc查询模块帮助命令
    def sys_doc_api(self, client='local', tgt='*', tgt_type='glob', fun='sys.doc', arg=None):
        arg = [] if arg is None else arg
        if arg is None:
            arg = []
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'sys_doc_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装sys.doc查询模块帮助命令
    def sys_runner_doc_api(self, client='local', tgt='*', tgt_type='glob', fun='sys.runner_doc', arg=None):
        arg = [] if arg is None else arg
        if arg is None:
            arg = []
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'sys_runner_doc_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装sys.doc查询模块帮助命令
    def sys_state_doc_api(self, client='local', tgt='*', tgt_type='glob', fun='sys.state_doc', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'sys_state_doc_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装git.clone命令
    def git_clone_api(self, client='local', tgt='*', tgt_type='glob', fun='git.clone', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'git_clone_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装git.pull命令
    def git_pull_api(self, client='local', tgt='*', tgt_type='glob', fun='git.pull', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'git_pull_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装git.reset命令
    def git_reset_api(self, client='local', tgt='*', tgt_type='glob', fun='git.reset', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'git_reset_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # salt-run config.get file_roots:base查看master配置文件中file_roots:base相关配置使用
    def saltrun_file_roots_api(self, client='runner', fun='config.get', arg='file_roots:base'):
        data = {'client': client,
                'fun': fun,
                'arg': arg,
                }
        message = 'saltrun_config_get_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

    # 封装find查找文件夹命令
    def find_find_api(self, client='local', tgt='*', tgt_type='glob', fun='file.find', arg=None):
        arg = [] if arg is None else arg
        data = {'client': client,
                'tgt': tgt,
                'tgt_type': tgt_type,
                'fun': fun,
                'arg': arg,
                }
        message = 'find_find_api'
        response_data = self.public(data, message)
        if response_data is False:
            return {'results': 'SaltAPI调用%s请求出错,请检查saltapi接口是否正常' % message, 'status': False}
        else:
            return {'results': response_data, 'status': True}

