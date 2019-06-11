from xpgg_oms.salt_api import SaltAPI
from xpgg_oms.models import AppRelease, MinionList, AppReleaseLog, AppGroup
from xpgg_oms import tasks
from .utils import StandardPagination, format_state
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import filters
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from xpgg_oms.serializers import release_serializers
from xpgg_oms.filters import MinionListFilter
import datetime
import requests
import json
import time
import re
# 下面这个是py3解决requests请求https误报问题
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import logging
logger = logging.getLogger('xpgg_oms.views')


# --- 应用发布 ---
# 应用发布搜索过滤器 直接写在这里因为每个功能基本就一个
class AppReleaseFilter(django_filters.rest_framework.FilterSet):
    minion_id = django_filters.CharFilter(field_name='minion_list', lookup_expr='icontains')
    app_name = django_filters.CharFilter(field_name='app_name', lookup_expr='icontains')
    # 匹配操作参数中的内容，主要是用来匹配svn/git的url的，因为有时候需要通过这个查询应用，但其实这个可以查询所有操作参数内容
    app_url = django_filters.CharFilter(field_name='operation_arguments', lookup_expr='icontains')

    class Meta:
        model = AppRelease
        fields = ['app_name', 'minion_id', 'app_url']


# 应用发布：查询添加应用
class ReleaseModelViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    list:
        应用信息列表

    create:
        创建应用，按需求传递相关参数，主要是operation_arguments参数的传递需要前端配合
        目前我设计是前端每个都以字段都传递过来比如svn地址、应用停止命令等，然后我序列化里
        对这些字段整合到operation_arguments参数里存入数据库

    update:
        更新应用，类似创建

    """
    queryset = AppRelease.objects.all()
    serializer_class = release_serializers.ReleaseCreateSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filter_class = AppReleaseFilter
    pagination_class = StandardPagination

    # 自定义每页个数
    # pagination_class.page_size = 1

    # 可选的排序规则
    ordering_fields = ('id', 'minion_list', 'app_name')
    # 默认排序规则
    ordering = ('id',)

    # 动态选择serializer
    def get_serializer_class(self):
        if self.action == "list":
            return release_serializers.ReleaseModelSerializer
        elif self.action == "create":
            return release_serializers.ReleaseCreateSerializer
        elif self.action == "update":
            return release_serializers.ReleaseCreateSerializer
        return release_serializers.ReleaseModelSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # 下面都是create源码内容
            self.perform_create(serializer)
            response_data = {'results': '添加成功', 'status': True}
            return Response(response_data)
        else:
            response_data = {'results': serializer.errors, 'status': False}
            return Response(response_data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            # 判断有没有更新svn/git相关信息，如果有要删除对应的检出目录，因为如果不删重新检出的时候会存在很多问题，比如旧文件无法被删除导致检出失败
            old_opt_arg = json.loads(instance.operation_arguments)
            new_opt_arg = serializer.validated_data.get('operation_arguments')
            co_status = instance.co_status
            co_path = instance.co_path
            old_app_svn_url = old_opt_arg.get('app_svn_url')
            old_app_git_url = old_opt_arg.get('app_git_url')
            old_app_git_user = old_opt_arg.get('app_git_user')
            old_app_git_password = old_opt_arg.get('app_git_password')
            old_app_git_branch = old_opt_arg.get('app_git_branch')
            new_app_svn_url = new_opt_arg.get('app_svn_url')
            new_app_git_url = new_opt_arg.get('app_git_url')
            new_app_git_user = new_opt_arg.get('app_git_user')
            new_app_git_password = new_opt_arg.get('app_git_password')
            new_app_git_branch = new_opt_arg.get('app_git_branch')
            if old_app_svn_url == new_app_svn_url and old_app_git_url == new_app_git_url and old_app_git_user == new_app_git_user and old_app_git_password == new_app_git_password and old_app_git_branch == new_app_git_branch:
                # 下面的源码内容
                self.perform_update(serializer)
                if getattr(instance, '_prefetched_objects_cache', None):
                    # If 'prefetch_related' has been applied to a queryset, we need to
                    # forcibly invalidate the prefetch cache on the instance.
                    instance._prefetched_objects_cache = {}

                response_data = {'results': '更新成功', 'status': True}
                return Response(response_data)
            else:
                if co_status is True:
                    result = {'results': '', 'status': False}
                    with requests.Session() as s:
                        saltapi = SaltAPI(session=s)
                        response_data = saltapi.file_remove_api(tgt=settings.SITE_SALT_MASTER, arg=[co_path])
                        if response_data['status'] is False:
                            result['results'] = '更新应用在删除应用原检出内容时失败，%s' % response_data['results']
                            return Response(result)
                        else:
                            response_data = response_data['results']['return'][0][settings.SITE_SALT_MASTER]
                            if response_data is True:
                                # 删除成功后提交更新，记得把co_status检出状态还原为False,
                                # 检出目录还是不变，在做发布的时候会重新自动创建出来不用担心
                                aa = serializer.save(co_status=False)
                                if getattr(instance, '_prefetched_objects_cache', None):
                                    # If 'prefetch_related' has been applied to a queryset, we need to
                                    # forcibly invalidate the prefetch cache on the instance.
                                    instance._prefetched_objects_cache = {}

                                response_data = {'results': '更新成功', 'status': True}
                                return Response(response_data)
                            else:
                                result['results'] = '更新应用在删除应用原检出内容时API返回结果错误：' + str(response_data)
                                return Response(result)
                else:
                    # 下面的源码内容
                    self.perform_update(serializer)
                    if getattr(instance, '_prefetched_objects_cache', None):
                        # If 'prefetch_related' has been applied to a queryset, we need to
                        # forcibly invalidate the prefetch cache on the instance.
                        instance._prefetched_objects_cache = {}

                    response_data = {'results': '更新成功', 'status': True}
                    return Response(response_data)
        else:
            response_data = {'results': serializer.errors, 'status': False}
            return Response(response_data)


# 应用发布：删除应用
class ReleaseDeleteViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """

    create:
        删除应用，因为不是单纯的删除数据库记录，所以需要用post来处理并接收相关参数
        接收id和delete_app_file_select，delete_app_file_select值为delete_app_file表示删除应用目录


    """
    queryset = AppRelease.objects.all()
    serializer_class = release_serializers.ReleaseDeleteSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            instance = AppRelease.objects.get(id=serializer.validated_data.get('id'))
            delete_app_file_select = serializer.validated_data.get('delete_app_file_select')
            result = {'results': None, 'status': False}
            try:
                co_path = instance.co_path
                app_path = instance.app_path
                app_backup_path = instance.app_backup_path
                minion_id_list = instance.minion_list.split(',')

                # 应用发布组为开发，先注释
                # app_group_exist = AppGroup.objects.filter(
                #     app_group_members__regex=r'^%s$|^%s,|,%s$|,%s,' % (app_name, app_name, app_name, app_name)).exists()
                # if app_group_exist:
                #     result['result'] = '该应用属于应用发布组的成员，请先从应用发布组中踢除该应用，再执行删除操作'
                #     return Response(result)

                with requests.Session() as s:
                    saltapi = SaltAPI(session=s)
                    # 判断一下检出的目录是否存在，因为如果没发布过，目录还没生成，存在的话删除项目的时候要顺带删除
                    response_data = saltapi.file_directory_exists_api(tgt=settings.SITE_SALT_MASTER,
                                                                      arg=[co_path])
                    # 当调用api失败的时候会返回false
                    if response_data['status'] is False:
                        result['results'] = '删除应用失败error(1)，%s' % response_data['results']
                        return Response(result)
                    else:
                        response_data = response_data['results']['return'][0][settings.SITE_SALT_MASTER]
                        if response_data is True:
                            # 删除master端项目的检出目录
                            response_data = saltapi.file_remove_api(tgt=settings.SITE_SALT_MASTER,
                                                                    arg=[co_path])
                            # 当调用api失败的时候会返回false
                            if response_data['status'] is False:
                                result['results'] = '删除应用失败error(2)，%s' % response_data['results']
                                return Response(result)
                            else:
                                response_data = response_data['results']['return'][0][settings.SITE_SALT_MASTER]
                                if response_data is True:
                                    pass
                                else:
                                    result['results'] = '删除应用失败error(3)：' + str(response_data['results'])
                                    return Response(result)
                    if delete_app_file_select == 'delete_app_file':
                        for minion in minion_id_list:
                            # 删除应用目录
                            response_data = saltapi.file_directory_exists_api(tgt=minion, arg=[app_path])
                            # 当调用api失败的时候会返回false
                            if response_data['status'] is False:
                                result['results'] = 'Minion ID:%s 删除应用时删除应用目录失败error(1)，%s' % (
                                    minion, response_data['results'])
                                return Response(result)
                            else:
                                response_data = response_data['results']['return'][0][minion]
                                # 判断一下svn检出的目录是否存在，因为如果没发布过，目录还没生成，存在的话删除项目的时候要顺带删除
                                if response_data is True:
                                    response_data = saltapi.file_remove_api(tgt=minion, arg=[app_path])
                                    # 当调用api失败的时候会返回false
                                    if response_data['status'] is False:
                                        result['results'] = 'Minion ID:%s 删除应用时删除应用目录失败error(2)，%s' % (
                                            minion, response_data['results'])
                                        return Response(result)
                                    else:
                                        response_data = response_data['results']['return'][0][minion]
                                        if response_data is True:
                                            pass
                                        else:
                                            result['results'] = 'Minion ID:%s 删除应用时删除应用目录结果错误error(1)，%s' % (
                                                minion, str(response_data['results']))
                                            return Response(result)
                            # 删除备份目录
                            response_data = saltapi.file_directory_exists_api(tgt=minion, arg=[app_backup_path])
                            if response_data['status'] is False:
                                result['results'] = 'Minion ID:%s 删除应用时删除应用备份目录失败error(1)，%s' % (
                                    minion, response_data['results'])
                                return Response(result)
                            else:
                                response_data = response_data['results']['return'][0][minion]
                                # 判断一下检出的目录是否存在，因为如果没发布过，目录还没生成，存在的话删除项目的时候要顺带删除
                                if response_data is True:
                                    response_data = saltapi.file_remove_api(tgt=minion, arg=[app_backup_path])
                                    # 当调用api失败的时候会返回false
                                    if response_data['status'] is False:
                                        result['results'] = 'Minion ID:%s 删除应用时删除应用备份目录失败error(2)，%s' % (
                                            minion, response_data['results'])
                                        return Response(result)
                                    else:
                                        response_data = response_data['results']['return'][0][minion]
                                        if response_data is True:
                                            pass
                                        else:
                                            result['results'] = 'Minion ID:%s 删除应用时删除应用备份目录结果错误，%s' % (
                                                minion, str(response_data['results']))
                                            return Response(result)
                    # 删除数据库记录
                    AppRelease.objects.filter(id=instance.id).delete()
                result['results'] = '删除成功'
                result['status'] = True
            except Exception as e:
                result['result'] = str(e)
            return Response(result)
        else:
            response_data = {'results': serializer.errors, 'status': False}
            return Response(response_data)


# 应用发布 发布操作
class ReleaseOperationViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """

    create:
        发布操作

    """
    serializer_class = release_serializers.ReleaseOperationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            response_data = {'results': '提交的参数没有通过验证', 'status': False}
            # logger.error(serializer.errors)
            return Response(response_data)
        result = {'results': None, 'status': False}
        app_log = []
        app_id = request.data.get('id')
        app_data = AppRelease.objects.get(id=app_id)
        # 判断执行的是否为单项操作执行判断，如果不是就是执行操作步骤顺序的操作
        single_cmd = request.data.get('single_cmd')
        if single_cmd:
            operation_list = [single_cmd]
        else:
            operation_list = json.loads(app_data.operation_list)
        operation_arguments = json.loads(app_data.operation_arguments)
        # 判断应用是否已经在发布中，如果正在发布不能重复发布，直接返回
        if app_data.release_status != '空闲':
            result['results'] = '应用：%s 正在发布中，请稍后再试' % app_data.app_name
            result['release_status'] = '发布中'
            return Response(result)
        try:
            # 修改应用状态为发布中
            AppRelease.objects.filter(id=app_id).update(release_status='发布中')
            # 由于用的salt来做发布所以如果minion离线或不存在删除了就无法执行，所以要判断，另外还有一个原因是minion管理表如果
            # 删除了某个minion会触发try的except
            try:
                minion_list = app_data.minion_list.split(',')
                for minion_id in minion_list:
                    minion_status = MinionList.objects.get(minion_id=minion_id).minion_status
                    if minion_status == '离线':
                        app_log.append('\n应用minion_id:%s离线了，请确认全部在线或移除离线minino_id才可执行应用发布' % minion_id)
                        result['results'] = app_log
                        return Response(result)
            except Exception as e:
                logger.error('\n检查应用的Minion_ID出错，可能有Minion已经不存在了，报错信息:' + str(e))
                app_log.append('\n检查应用的Minion_ID出错，可能有Minion已经不存在了，报错信息:' + str(e))
                result['results'] = app_log
                return Response(result)
            for minion_id in minion_list:
                app_log.append(
                    ('-' * 10 + ('Minion_ID:%s开始发布 时间戳%s' % (minion_id, time.strftime('%X'))) + '-' * 10).center(
                        88) + '\n')
                for operation in operation_list:
                    if operation == 'SVN更新':
                        # 检出状态需要在这里获取，因为下面操作需要判断是检出还是更新操作，
                        # 如果在上面就定义好，那么多个minion_id的新项目第一个id是检出后也全是检出，因为判断版本的时候都是空
                        co_status = AppRelease.objects.get(id=app_id).co_status
                        release_version = request.data.get('release_version', 'HEAD')
                        app_log.append('\n\n开始执行SVN更新-> 时间戳%s\n' % time.strftime('%X'))
                        with requests.Session() as s:
                            saltapi = SaltAPI(session=s)
                            # 判断检出状态，如果有说明已经检出过，那就使用更新up，如果没有就用检出co
                            if co_status:
                                cmd_data = 'svn up -r %s %s --no-auth-cache --non-interactive  --username=%s --password=%s' % (
                                    release_version, app_data.co_path, operation_arguments['app_svn_user'],
                                    operation_arguments['app_svn_password'])
                                # 用来做执行结果判断的，因为结果有很多意外情况，下面是对的情况下会出现的关键字
                                check_data = "Updating '%s'" % app_data.co_path
                            else:
                                cmd_data = 'svn co -r %s %s  %s --username=%s --password=%s --non-interactive --no-auth-cache' % (
                                    release_version, operation_arguments['app_svn_url'], app_data.co_path,
                                    operation_arguments['app_svn_user'], operation_arguments['app_svn_password'])
                                check_data = 'Checked out revision'
                            response_data = saltapi.cmd_run_api(tgt=settings.SITE_SALT_MASTER, arg=[
                                cmd_data, 'reset_system_locale=false', "shell='/bin/bash'", "runas='root'"])
                            # 当调用api失败的时候会返回false
                            if response_data['status'] is False:
                                app_log.append('\n更新svn后台出错_error(1),报错内容：%s，请联系管理员. 时间戳%s\n' % (response_data['results'], time.strftime('%X')))
                                result['results'] = app_log
                                return Response(result)
                            else:
                                response_data = response_data['results']['return'][0][settings.SITE_SALT_MASTER]

                                if check_data in response_data:
                                    AppRelease.objects.filter(id=app_id).update(co_status=True)
                                    app_log.append(
                                        '\n' + str(response_data) + '\n\nSVN更新完成<- 时间戳%s\n' % time.strftime(
                                            '%X'))

                                else:
                                    app_log.append(
                                        '\nSVN更新失败:' + str(response_data) + '\n时间戳%s' % time.strftime('%X'))
                                    result['results'] = app_log
                                    return Response(result)
                    if operation == 'GIT更新':
                        co_status = AppRelease.objects.get(id=app_id).co_status
                        release_version = request.data.get('release_version', 'HEAD')
                        # 目前只支持http方式的git，下面是拼接把用户名密码拼接进去这样就不用输入了,如果用户名有@需要转义
                        app_git_user_new = operation_arguments['app_git_user'].replace('@', '%40')
                        app_git_url_join_usr_passwd = operation_arguments['app_git_url'].split('://')[
                                                          0] + '://' + app_git_user_new + ':' + operation_arguments['app_git_password'] + '@' + \
                                                      operation_arguments['app_git_url'].split('://')[1]
                        app_log.append('\n\n开始执行GIT更新-> 时间戳%s\n' % time.strftime('%X'))
                        with requests.Session() as s:
                            saltapi = SaltAPI(session=s)
                            # 判断状态是否为True，如果有说明已经检出过，那就使用更新pull，如果没有就用git clone
                            if co_status is not True:
                                app_log.append('\n\ngit clone ....\n')
                                response_data = saltapi.git_clone_api(tgt=settings.SITE_SALT_MASTER, arg=[
                                    'cwd=%s' % app_data.co_path.rsplit('/', 1)[0],
                                    'url=%s' % app_git_url_join_usr_passwd,
                                    'name=%s' % app_data.co_path.rsplit('/', 1)[1],
                                    'opts="-b %s"' % operation_arguments['app_git_branch']])
                                check_data = True
                            else:
                                if release_version == 'HEAD':
                                    response_data = saltapi.git_pull_api(tgt=settings.SITE_SALT_MASTER,
                                                                         arg=[app_data.co_path])
                                    check_data = 'Updating'
                                else:
                                    response_data = saltapi.git_reset_api(tgt=settings.SITE_SALT_MASTER,
                                                                          arg=[app_data.co_path,
                                                                               'opts="--hard %s"' % release_version])
                                    check_data = 'HEAD is now at'
                            # 当调用api失败的时候会返回false
                            if response_data['status'] is False:
                                app_log.append('\n更新git后台出错_error(1)，报错内容：%s，请联系管理员. 时间戳%s\n' % (response_data['results'], time.strftime('%X')))
                                result['results'] = app_log
                                return Response(result)
                            else:
                                response_data = response_data['results']['return'][0][settings.SITE_SALT_MASTER]
                                # 对结果进行判断，妈的用salt的module方式还得自个判断结果，比较麻烦一点，而且if还有可能代码错误得加try
                                try:
                                    if response_data is True or check_data in response_data or 'Already up' in response_data:
                                        try:
                                            AppRelease.objects.filter(id=app_id).update(co_status=True)
                                            app_log.append(
                                                '\n' + str(response_data) + '\n\nGIT更新完成<- 时间戳%s\n' % time.strftime(
                                                    '%X'))
                                        except Exception as e:
                                            app_log.append(
                                                '\nGIT更新失败:\n' + str(response_data) + '\n时间戳%s' % time.strftime(
                                                    '%X'))
                                            result['results'] = app_log
                                            return Response(result)
                                    else:
                                        app_log.append(
                                            '\nGIT更新失败:' + str(response_data) + '\n时间戳%s' % time.strftime('%X'))
                                        result['results'] = app_log
                                        return Response(result)
                                except Exception as e:
                                    app_log.append(
                                        '\nGIT更新失败:' + str(response_data) + '\n时间戳%s' % time.strftime('%X'))
                                    result['results'] = app_log
                                    return Response(result)
                    elif operation == '同步文件':
                        sync_file_method = operation_arguments.get('sync_file_method', 'salt')
                        if sync_file_method == 'salt':
                            source_path = app_data.co_path.rstrip('/').rsplit('/', 1)[1]
                            sync_file_check_diff = operation_arguments['sync_file_check_diff']
                            symlink_path = settings.SITE_BASE_CO_SYMLINK_PATH + source_path
                            app_log.append('\n\n开始执行同步文件-> 时间戳%s\n' % time.strftime('%X'))
                            with requests.Session() as s:
                                saltapi = SaltAPI(session=s)
                                # 先创建软连接
                                response_data = saltapi.file_symlink_api(tgt=settings.SITE_SALT_MASTER,
                                                                         arg=[app_data.co_path, symlink_path])
                                if response_data['status'] is False:
                                    app_log.append('\n同步文件后台出错,SaltAPI调用file_symlink_api请求出错，请联系管理员. 时间戳%s\n' % time.strftime('%X'))
                                    result['results'] = app_log
                                    return Response(result)
                                else:
                                    if response_data['results']['return'][0][settings.SITE_SALT_MASTER] is not True:
                                        # 如果软连接创建失败会返回：{'return': [{'192.168.100.170': False}]}
                                        app_log.append('同步文件过程中，创建软连接失败\n' + str(response_data))
                                        app_log.append('\n' + '文件同步失败！！ 时间戳%s\n' % time.strftime('%X'))
                                        result['results'] = app_log
                                        return Response(result)
                                # 执行文件同步
                                jid = saltapi.async_state_api(tgt=minion_id, arg=["rsync_dir",
                                                                                  "pillar={'sync_file_method':'%s','source_path':'%s','name_path':'%s','user':'%s','sync_file_check_diff':'%s'}" % (
                                                                                  sync_file_method, source_path,
                                                                                  app_data.app_path, app_data.app_path_owner,
                                                                                  sync_file_check_diff), "queue=True"])
                                if jid['status'] is False:
                                    app_log.append(
                                        '\n同步文件后台出错,SaltAPI调用async_state_api请求出错，请联系管理员. 时间戳%s\n' % time.strftime(
                                            '%X'))
                                    result['results'] = app_log
                                    return Response(result)
                                else:
                                    try:
                                        jid = jid['results']['return'][0]['jid']
                                        check_count = 400
                                        re_count = 0
                                        time.sleep(10)
                                        while check_count:
                                            job_status = saltapi.job_active_api(tgt=minion_id, arg=jid)
                                            if job_status['status'] is False:
                                                app_log.append(
                                                    '\n同步文件后台出错,SaltAPI调用job_active_api请求出错，请联系管理员. 时间戳%s\n' % time.strftime(
                                                        '%X'))
                                                result['results'] = app_log
                                                return Response(result)
                                            else:
                                                value = job_status['results']['return'][0][minion_id]
                                                if value:
                                                    # 为真说明job还在执行，刚好用来恢复断线false的计数器
                                                    if re_count > 0:
                                                        re_count = 0
                                                # 这个留在这里做个说明，我发现在调用job_active_api接口的时候经常失败返回false了，感觉是接口有问题
                                                # 而如果出现都是false用jid_api接口取到的结果就会是[{}]所以下面对这个要做一层判断，以免因为接口不稳导致没取到结果
                                                # 另外注意这里value is False看上去好像和上面是if value是相反的可以直接用else代替，但是不行！因为当执行完毕返回是{}而{}和False是不同的！
                                                elif value is False:
                                                    # 连续监测2次都是那就不用跑了直接返回离线结束呵呵
                                                    if re_count == 2:
                                                        app_log.append('\n同步文件后台出错,您要发布的主机%s离线了，请联系管理员. 时间戳%s\n' % (
                                                        minion_id, time.strftime('%X')))
                                                        result['results'] = app_log
                                                        return Response(result)
                                                    # re计数器不到3次则+1，继续下一轮循环
                                                    else:
                                                        re_count += 1
                                                # 当value等于[{}]时候说明job执行完毕了，则执行下面
                                                else:
                                                    jid_data = saltapi.jid_api(jid=jid)
                                                    # 注意[{}] ！= False所以不能用if jid_data['return']判断是否有数据，这个坑埋了好久奶奶的！！！
                                                    if jid_data['status'] is False:
                                                        app_log.append(
                                                            '\n同步文件后台出错,SaltAPI调用jid_api请求出错,jid:%s，请联系管理员. 时间戳%s\n' % (
                                                            jid, time.strftime('%X')))
                                                        result['results'] = app_log
                                                        return Response(result)
                                                    elif jid_data['results']['return'] == [{}]:
                                                        # 这个判断没必要，只是留这里做个说明，我之前上面没有做if value is False判断的时候，如果job_active_api
                                                        # 的结果全部false了也会正常跳出for循环，然后在这里会出现jid_data['return'] == [{}]的情况，因为false
                                                        # 说明minion断线了，结果肯定取到空了；还有另一种情况就是还没有返回值的时候也会等于[{}],
                                                        # 不过后面我在上面加了对false做判断这里就没必要了呵呵
                                                        pass
                                                    else:
                                                        format_result = format_state(jid_data)
                                                        if type(format_result) == str:
                                                            # 如果minion客户端停了会返回：{'return': [{'192.168.100.170': False}]}
                                                            app_log.append(format_result)
                                                            app_log.append(
                                                                '\n' + '文件同步失败！！ 时间戳%s\n' % time.strftime('%X'))
                                                            result['results'] = app_log
                                                            return Response(result)
                                                        else:
                                                            try:
                                                                failed_result = re.search(r'Failed:     (\d+)',
                                                                                          format_result[0]).group(1)
                                                                if int(failed_result) != 0:
                                                                    app_log.extend(format_result)
                                                                    app_log.append(
                                                                        '\n' + '文件同步失败！！ 时间戳%s\n' % time.strftime(
                                                                            '%X'))
                                                                    result['results'] = app_log
                                                                    return Response(result)
                                                                else:
                                                                    app_log.extend(format_result)
                                                                    app_log.append(
                                                                        '\n\n文件同步完成<- 时间戳%s\n' % time.strftime(
                                                                            '%X'))
                                                                    break
                                                            except Exception as e:
                                                                app_log.append('\n' + '文件同步代码出错：' + str(
                                                                    e) + '\n时间戳%s' % time.strftime('%X'))
                                                                result['results'] = app_log
                                                                return Response(result)
                                                check_count -= 1
                                                time.sleep(15)
                                        else:
                                            app_log.append(
                                                '\n' + '文件同步超过100分钟还没有结束，系统默认同步失败，如需获取同步结果请联系管理员通过jid：%s查看！！ 时间戳%s\n' % (
                                                jid, time.strftime('%X')))
                                            result['results'] = app_log
                                            return Response(result)
                                    except Exception as e:
                                        app_log.append(str(e))
                                        app_log.append('\n' + '文件同步失败！！ 时间戳%s\n' % time.strftime('%X'))
                                        result['results'] = app_log
                                        return Response(result)
                                    finally:
                                        # 释放掉软连接
                                        response_data = saltapi.file_remove_api(tgt=settings.SITE_SALT_MASTER,
                                                                                arg=[symlink_path])
                                        # 当调用api失败的时候会返回false
                                        if response_data['status'] is False:
                                            app_log.append('删除软连接失败(0)，未避免目录不断膨胀请联系管理员删除软连接\n')
                                        else:
                                            response_data = response_data['results']['return'][0][
                                                settings.SITE_SALT_MASTER]
                                            if response_data is True:
                                                app_log.append('\n释放软连接成功\n')
                                            else:
                                                app_log.append('\n释放软连接失败(1)，未避免目录不断膨胀请联系管理员删除软连接\n')
                        elif sync_file_method == 'rsync':
                            source_path = app_data.co_path.rstrip('/').rsplit('/', 1)[1]
                            sync_file_check_diff = operation_arguments.get('sync_file_check_diff')
                            rsync_ip = operation_arguments.get('rsync_ip', settings.RSYNC_IP)
                            # salt-2018.3.0以前rsync的参数中没有additional_opts，无法指定很多东西，2018版本就有了，留这里为了新版使用
                            rsync_port = operation_arguments.get('rsync_port', settings.RSYNC_PORT)
                            app_log.append('\n\n开始执行同步文件-> 时间戳%s\n' % time.strftime('%X'))
                            with requests.Session() as s:
                                saltapi = SaltAPI(session=s)
                                if app_data.sys_type == 'windows':
                                    # windows下的rsync语法中路径写法比较特殊，所以要做下修改来适应，name_path存传递给后端SLS的name字段
                                    name_path = '/cygdrive/' + app_data.app_path.replace(':\\', '/').replace('\\', '/')
                                else:
                                    name_path = app_data.app_path
                                jid = saltapi.async_state_api(tgt=minion_id, arg=["rsync_dir",
                                                                                  "pillar={'sync_file_method':'%s','mkdir_path':'%s','rsync_ip':'%s','rsync_port':'%s','source_path':'%s','name_path':'%s','user':%s,'sync_file_check_diff':'%s'}" % (
                                                                                      sync_file_method, app_data.app_path,
                                                                                      rsync_ip, rsync_port,
                                                                                      source_path,
                                                                                      name_path, app_data.app_path_owner,
                                                                                      sync_file_check_diff),
                                                                                  "queue=True"])

                                if jid['status'] is False:
                                    app_log.append(
                                        '\n同步文件后台出错,SaltAPI调用async_rsync_rsync_api请求出错，请联系管理员. 时间戳%s\n' % time.strftime(
                                            '%X'))
                                    result['results'] = app_log
                                    return Response(result)
                                else:
                                    try:
                                        jid = jid['results']['return'][0]['jid']
                                        check_count = 400
                                        re_count = 0
                                        time.sleep(10)
                                        while check_count:
                                            job_status = saltapi.job_active_api(tgt=minion_id, arg=jid)
                                            if job_status['status'] is False:
                                                app_log.append(
                                                    '\n同步文件后台出错,SaltAPI调用job_active_api请求出错，请联系管理员. 时间戳%s\n' % time.strftime(
                                                        '%X'))
                                                result['results'] = app_log
                                                return Response(result)
                                            else:
                                                value = job_status['results']['return'][0][minion_id]
                                                if value:
                                                    # 为真说明job还在执行，刚好用来恢复断线false的计数器
                                                    if re_count > 0:
                                                        re_count = 0
                                                # 这个留在这里做个说明，我发现在调用job_active_api接口的时候经常失败返回false了，感觉是接口有问题
                                                # 而如果出现都是false用jid_api接口取到的结果就会是[{}]所以下面对这个要做一层判断，以免因为接口不稳导致没取到结果
                                                # 另外注意这里value is False看上去好像和上面是if value是相反的可以直接用else代替，但是不行！因为当执行完毕返回是{}而{}和False是不同的！
                                                elif value is False:
                                                    # 连续监测2次都是那就不用跑了直接返回离线结束呵呵
                                                    if re_count == 2:
                                                        app_log.append(
                                                            '\n同步文件后台出错,您要发布的主机%s离线了，请联系管理员. 时间戳%s\n' % (
                                                                minion_id, time.strftime('%X')))
                                                        result['results'] = app_log
                                                        return Response(result)
                                                    # re计数器不到3次则+1，继续下一轮循环
                                                    else:
                                                        re_count += 1
                                                # 当value等于[{}]时候说明job执行完毕了，则执行下面
                                                else:
                                                    jid_data = saltapi.jid_api(jid=jid)
                                                    # 注意[{}] ！= False所以不能用if jid_data['return']判断是否有数据，这个坑埋了好久奶奶的！！！
                                                    if jid_data['status'] is False:
                                                        app_log.append(
                                                            '\n同步文件后台出错,SaltAPI调用jid_api请求出错，请联系管理员. 时间戳%s\n' % time.strftime(
                                                                '%X'))
                                                        result['results'] = app_log
                                                        return Response(result)
                                                    elif jid_data['results']['return'] == [{}]:
                                                        # 这个判断没必要，只是留这里做个说明，我之前上面没有做if value is False判断的时候，如果job_active_api
                                                        # 的结果全部false了也会正常跳出for循环，然后在这里会出现jid_data['return'] == [{}]的情况，因为false
                                                        # 说明minion断线了，结果肯定取到空了；还有另一种情况就是还没有返回值的时候也会等于[{}],
                                                        # 不过后面我在上面加了对false做判断这里就没必要了呵呵
                                                        pass
                                                    else:
                                                        format_result = format_state(jid_data)
                                                        if type(format_result) == str:
                                                            # 如果minion客户端停了会返回：{'return': [{'192.168.100.170': False}]}
                                                            app_log.append(format_result)
                                                            app_log.append(
                                                                '\n' + '文件同步失败！！ 时间戳%s\n' % time.strftime(
                                                                    '%X'))
                                                            result['results'] = app_log
                                                            return Response(result)
                                                        else:
                                                            try:
                                                                failed_result = re.search(
                                                                    r'Failed:     (\d+)',
                                                                    format_result[0]).group(1)
                                                                if int(failed_result) != 0:
                                                                    app_log.extend(format_result)
                                                                    app_log.append(
                                                                        '\n' + '文件同步失败！！ 时间戳%s\n' % time.strftime(
                                                                            '%X'))
                                                                    result['results'] = app_log
                                                                    return Response(result)
                                                                else:
                                                                    app_log.extend(format_result)
                                                                    app_log.append(
                                                                        '\n\n文件同步完成<- 时间戳%s\n' % time.strftime(
                                                                            '%X'))
                                                                    break
                                                            except Exception as e:
                                                                app_log.append('\n' + '文件同步代码出错：' + str(
                                                                    e) + '\n时间戳%s' % time.strftime('%X'))
                                                                result['results'] = app_log
                                                                return Response(result)
                                                check_count -= 1
                                                time.sleep(15)
                                        else:
                                            app_log.append(
                                                '\n' + '文件同步超过100分钟还没有结束，系统默认同步失败，如需获取同步结果请联系管理员通过jid：%s查看！！ 时间戳%s\n' % (
                                                    jid, time.strftime('%X')))
                                            result['results'] = app_log
                                            return Response(result)
                                    except Exception as e:
                                        app_log.append(str(e))
                                        app_log.append('\n' + '文件同步失败！！ 时间戳%s\n' % time.strftime('%X'))
                                        result['results'] = app_log
                                        return Response(result)
                    elif operation == '应用停止':
                        app_log.append('\n\n开始执行应用服务停止操作->')
                        if '停止服务名' in operation_arguments:
                            stop_server_name = operation_arguments['停止服务名']
                            with requests.Session() as s:
                                saltapi = SaltAPI(session=s)
                                response_data = saltapi.service_available_api(tgt=minion_id, arg=[stop_server_name])
                                if response_data['status'] is False:
                                    app_log.append('\n应用停止后台出错_error(1)，请联系管理员')
                                    result['results'] = app_log
                                    return Response(result)
                                else:
                                    if response_data['results']['return'][0][minion_id] is False:
                                        app_log.append('\n' + '应用停止失败,请确定是否存在该服务！！')
                                        result['results'] = app_log
                                        return Response(result)
                                    elif response_data['results']['return'][0][minion_id] is True:
                                        response_data = saltapi.service_stop_api(tgt=minion_id,
                                                                                 arg=[stop_server_name])
                                        # 当调用api失败的时候会返回false
                                        if response_data['status'] is False:
                                            app_log.append('\n应用停止后台出错_error(2)，请联系管理员')
                                            result['results'] = app_log
                                            return Response(result)
                                        else:
                                            stop_data = response_data['results']['return'][0][minion_id]
                                            response_data = saltapi.service_status_api(tgt=minion_id,
                                                                                       arg=[stop_server_name])
                                            # 当调用api失败的时候会返回false
                                            if response_data['status'] is False:
                                                app_log.append('\n应用停止后台出错_error(3)，请联系管理员')
                                                result['results'] = app_log
                                                return Response(result)
                                            elif response_data['results']['return'][0][minion_id] is False:
                                                app_log.append('\n' + '应用停止成功<-\n')
                                            elif response_data['results']['return'][0][minion_id] is True:
                                                app_log.append('\n' + '应用停止失败，程序还在运行中。')
                                                result['results'] = app_log
                                                return Response(result)
                                            else:
                                                app_log.append('\n' + '应用停止失败,执行结果：' + str(stop_data) + str(
                                                    response_data['results']['return'][0][minion_id]))
                                                result['results'] = app_log
                                                return Response(result)
                                    else:
                                        app_log.append('\n' + '应用停止失败查询服务时没有返回正确结果,执行结果：' + str(
                                            response_data['results']['return'][0][minion_id]))
                                        result['results'] = app_log
                                        return Response(result)
                        elif '停止命令' in operation_arguments:
                            stop_cmd = operation_arguments['停止命令']
                            if app_data.sys_type == 'windows':
                                stop_cmd = stop_cmd + '&& echo %errorlevel%'
                                split_cmd = '\r\n'
                            else:
                                stop_cmd = stop_cmd + '; echo $?'
                                split_cmd = '\n'
                            with requests.Session() as s:
                                saltapi = SaltAPI(session=s)
                                response_data = saltapi.cmd_run_api(tgt=minion_id,
                                                                    arg=[stop_cmd, "shell='/bin/bash'",
                                                                         "runas='root'"])
                                # 当调用api失败的时候会返回false
                                if response_data['status'] is False:
                                    app_log.append('\n应用停止命令后台出错_error(5)，请联系管理员')
                                    result['results'] = app_log
                                    return Response(result)
                                else:
                                    try:
                                        response_data = response_data['results']['return'][0][minion_id].rsplit(split_cmd, 1)
                                        # 发现有的命令没有输出那么最终只会有成功失败的0、1返回这时候列表长度就=1
                                        if len(response_data) == 1:
                                            if response_data[0] == '0':
                                                app_log.append('\n' + '应用停止成功<-\n')
                                            else:
                                                app_log.append('\n' + '应用停止失败:' + response_data[0])
                                                result['results'] = app_log
                                                return Response(result)
                                        else:
                                            if response_data[1] == '0':
                                                app_log.append('\n' + '应用停止成功<-\n')
                                            else:
                                                app_log.append('\n' + '应用停止失败:' + response_data[0])
                                                result['results'] = app_log
                                                return Response(result)
                                    except Exception as e:
                                        app_log.append('\n' + '应用停止失败_error(6):' + str(response_data))
                                        result['results'] = app_log
                                        return Response(result)
                        elif '任务计划停止' in operation_arguments:
                            start_cmd = operation_arguments['任务计划停止']
                            if app_data.sys_type == 'linux':
                                logger.error('应用停止失败，应用停止中《任务计划启动》启动方式只适用于windows')
                                app_log.append('\n\n应用停止失败，应用停止中《任务计划停止》停止方式只适用于windows')
                                result['results'] = app_log
                                return Response(result)
                            with requests.Session() as s:
                                saltapi = SaltAPI(session=s)
                                response_data = saltapi.task_stop_api(tgt=minion_id, arg=[start_cmd])
                                # 当调用api失败的时候会返回false
                                if response_data['status'] is False:
                                    app_log.append('\n应用停止命令后台出错_error(2)，请联系管理员')
                                    result['results'] = app_log
                                    return Response(result)
                                else:
                                    try:
                                        response_data = response_data['results']['return'][0][minion_id]
                                        if response_data is True:
                                            app_log.append('\n' + '应用停止成功<-\n')
                                        else:
                                            app_log.append('\n' + '应用停止失败:' + response_data)
                                            result['results'] = app_log
                                            return Response(result)
                                    except Exception as e:
                                        app_log.append('\n' + '应用停止后台出错_error(3):' + str(e))
                                        result['results'] = app_log
                                        return Response(result)
                        elif '映像名称和命令行' in operation_arguments:
                            stop_cmd = operation_arguments['映像名称和命令行']
                            data = stop_cmd.split('|')
                            if len(data) != 2:
                                logger.error('应用停止失败,填写的命令不符合规范')
                                app_log.append('\n\n应用停止失败,填写的命令不符合规范')
                                result['results'] = app_log
                                return Response(result)
                            exe_name = data[0].strip()
                            cmdline = data[1].strip()
                            with requests.Session() as s:
                                saltapi = SaltAPI(session=s)
                                # 查看是否有映像名称的id存在，支持模糊搜索
                                response_data = saltapi.ps_pgrep_api(tgt=minion_id, arg=[exe_name])
                                # 当调用api失败的时候会返回false
                                if response_data['status'] is False:
                                    app_log.append('\n应用停止命令后台出错_error(8)，请联系管理员')
                                    result['results'] = app_log
                                    return Response(result)
                                else:
                                    try:
                                        response_data = response_data['results']['return'][0][minion_id]
                                        if isinstance(response_data, list):
                                            for pid in response_data:
                                                response_data = saltapi.ps_proc_info_api(tgt=minion_id,
                                                                                         arg=['pid=%s' % pid,
                                                                                              'attrs=["cmdline","status"]'])
                                                # 当调用api失败的时候会返回false
                                                if response_data['status'] is False:
                                                    app_log.append('\n应用停止命令后台出错_error(9)，请联系管理员\n')
                                                    result['results'] = app_log
                                                    return Response(result)
                                                else:
                                                    # 返回的cmdline会根据命令中空格（文件名字里有空格不算）进行分割成列表，所以下面用空格合并列表
                                                    cmdline_result = ' '.join(
                                                        response_data['results']['return'][0][minion_id]['cmdline'])
                                                    if cmdline == cmdline_result:
                                                        response_data = saltapi.ps_kill_pid_api(
                                                            tgt=minion_id, arg=['pid=%s' % pid])
                                                        if response_data['status'] is False:
                                                            app_log.append(
                                                                '\n应用停止命令后台出错_error(10)，请联系管理员\n')
                                                            result['results'] = app_log
                                                            return Response(result)
                                                        else:
                                                            if response_data['results']['return'][0][minion_id]:
                                                                app_log.append('\n' + '应用服务停止成功<-\n')
                                                            else:
                                                                app_log.append(
                                                                    '\n' + '应用停止在结束进程pid时返回结果为失败，系统默认为停止失败\n')
                                                                result['results'] = app_log
                                                                return Response(result)
                                                    else:
                                                        app_log.append(
                                                            '\n' + '应用停止在匹配命令行时没有发现可以匹配的命令行，系统默认为已经停止成功\n')

                                        else:
                                            app_log.append('\n' + '应用停止在查看进程时没有发现指定的进程，系统默认为已经停止成功\n')
                                    except Exception as e:
                                        logger.error('应用服务停止代码出错：' + str(e))
                                        app_log.append('\n' + '应用服务停止后台出错_error(11):' + str(e))
                                        result['results'] = app_log
                                        return Response(result)
                        elif 'supervisor_stop' in operation_arguments:
                            stop_cmd = operation_arguments['supervisor_stop']
                            with requests.Session() as s:
                                saltapi = SaltAPI(session=s)
                                # 直接执行supervisor停止命令，只要不出现False，就执行查询状态命令，就看状态来决定成功与否
                                response_data = saltapi.supervisord_stop_api(tgt=minion_id, arg=[stop_cmd])
                                # 当调用api失败的时候会返回false
                                if response_data['status'] is False:
                                    app_log.append('\n应用停止命令后台出错_error(13)，请联系管理员')
                                    result['results'] = app_log
                                    return Response(result)
                                else:
                                    # 查看是否有supervisor名称存在，不支持模糊搜索
                                    response_data = saltapi.supervisord_status_api(tgt=minion_id, arg=[stop_cmd])
                                    # 当调用api失败的时候会返回false
                                    if response_data['status'] is False:
                                        app_log.append('\n应用停止命令后台出错_error(14)，请联系管理员')
                                        result['results'] = app_log
                                        return Response(result)
                                    else:
                                        try:
                                            status_result = response_data['results']['return'][0][minion_id][stop_cmd]['state']
                                            # 这里有发现一个问题，返回的state值可能不是STOPPED可能是FATAL或者BACKOFF,所以判断只要不是RUNNING都算停止
                                            if status_result == 'STOPPED':
                                                app_log.append('\n' + '应用服务停止成功<-\n')
                                            else:
                                                if status_result != 'RUNNING':
                                                    app_log.append(
                                                        '\n' + '返回的状态码为%s,只要不是RUNNING应用服务都默认为停止成功<-\n' % status_result)
                                                else:
                                                    app_log.append('\n' + '应用停止查询状态结果为RUNNING，停止失败\n')
                                                    result['results'] = app_log
                                                    return Response(result)
                                        except Exception as e:
                                            logger.error('应用服务停止代码出错：' + str(e))
                                            app_log.append('\n' + '应用停止结果有错，返回结果：' + str(response_data))
                                            result['results'] = app_log
                                            return Response(result)
                    elif operation == '应用启动':
                        app_log.append('\n\n开始执行应用启动操作->\n')
                        if '启动服务名' in operation_arguments:
                            start_server_name = operation_arguments['启动服务名']
                            with requests.Session() as s:
                                saltapi = SaltAPI(session=s)
                                response_data = saltapi.service_available_api(tgt=minion_id,
                                                                              arg=[start_server_name])
                                if response_data['status'] is False:
                                    app_log.append('\n应用启动后台出错_error(1)，请联系管理员')
                                    result['results'] = app_log
                                    return Response(result)
                                else:
                                    if response_data['results']['return'][0][minion_id] is False:
                                        app_log.append('\n' + '应用启动失败,请确定是否存在该服务！！')
                                        result['results'] = app_log
                                        return Response(result)
                                    elif response_data['results']['return'][0][minion_id] is True:
                                        response_data = saltapi.service_start_api(tgt=minion_id,
                                                                                  arg=[start_server_name])
                                        # 当调用api失败的时候会返回false
                                        if response_data['status'] is False:
                                            app_log.append('\n应用启动后台出错_error(2)，请联系管理员')
                                            result['results'] = app_log
                                            return Response(result)
                                        else:
                                            start_data = response_data['results']['return'][0][minion_id]
                                            response_data = saltapi.service_status_api(tgt=minion_id,
                                                                                       arg=[start_server_name])
                                            # 当调用api失败的时候会返回false
                                            if response_data['status'] is False:
                                                app_log.append('\n应用启动后台出错_error(3)，请联系管理员')
                                                result['results'] = app_log
                                                return Response(result)
                                            elif response_data['results']['return'][0][minion_id] is False:
                                                app_log.append('\n' + '应用启动失败。')
                                                result['results'] = app_log
                                                return Response(result)
                                            elif response_data['results']['return'][0][minion_id] is True:
                                                app_log.append('\n' + '应用启动成功<-\n')
                                            else:
                                                app_log.append('\n' + '应用启动失败,执行结果：' + str(start_data) + str(
                                                    response_data['results']['return'][0][minion_id]))
                                                result['results'] = app_log
                                                return Response(result)
                                    else:
                                        app_log.append('\n' + '应用启动失败查询服务时没有返回正确结果,执行结果：' + str(
                                            response_data['results']['return'][0][minion_id]))
                                        result['results'] = app_log
                                        return Response(result)
                        elif '启动命令' in operation_arguments:
                            start_cmd = operation_arguments['启动命令']
                            if app_data.sys_type == 'windows':
                                start_cmd = start_cmd + '&& echo %errorlevel%'
                                split_cmd = '\r\n'
                            else:
                                start_cmd = start_cmd + '; echo $?'
                                split_cmd = '\n'
                            with requests.Session() as s:
                                saltapi = SaltAPI(session=s)
                                response_data = saltapi.cmd_run_api(tgt=minion_id,
                                                                    arg=[start_cmd, "shell='/bin/bash'",
                                                                         "runas='root'"])
                                # 当调用api失败的时候会返回false
                                if response_data['status'] is False:
                                    app_log.append('\n应用启动命令后台出错_error(4)，请联系管理员')
                                    result['results'] = app_log
                                    return Response(result)
                                else:
                                    try:
                                        response_data = response_data['results']['return'][0][minion_id].rsplit(split_cmd, 1)
                                        # 发现有的命令没有输出那么最终只会有成功失败的0、1返回这时候列表长度就=1
                                        if len(response_data) == 1:
                                            if response_data[0] == '0':
                                                app_log.append('\n' + '应用服务启动成功<-\n')
                                            else:
                                                app_log.append('\n' + '应用启动失败:' + response_data[0])
                                                result['results'] = app_log
                                                return Response(result)
                                        else:
                                            if response_data[1] == '0':
                                                app_log.append('\n' + '应用服务启动成功<-\n')
                                            else:
                                                app_log.append('\n' + '应用启动失败:' + response_data[0])
                                                result['results'] = app_log
                                                return Response(result)
                                    except Exception as e:
                                        app_log.append('\n' + '应用启动失败_error(5):' + str(response_data))
                                        result['results'] = app_log
                                        return Response(result)
                        elif '任务计划启动' in operation_arguments:
                            start_cmd = operation_arguments['任务计划启动']
                            if app_data.sys_type == 'linux':
                                logger.error('应用启动失败，应用启动中《任务计划启动》启动方式只适用于windows')
                                app_log.append('\n\n应用启动失败，应用启动中《任务计划启动》启动方式只适用于windows')
                                result['results'] = app_log
                                return Response(result)
                            with requests.Session() as s:
                                saltapi = SaltAPI(session=s)
                                response_data = saltapi.task_run_api(tgt=minion_id, arg=[start_cmd])
                                # 当调用api失败的时候会返回false
                                if response_data['status'] is False:
                                    app_log.append('\n应用启动命令后台出错_error(7)，请联系管理员')
                                    result['results'] = app_log
                                    return Response(result)
                                else:
                                    try:
                                        response_data = response_data['results']['return'][0][minion_id]
                                        if response_data is True:
                                            app_log.append('\n' + '应用启动成功<-\n')
                                        else:
                                            app_log.append('\n' + '应用启动失败:' + response_data)
                                            result['results'] = app_log
                                            return Response(result)
                                    except Exception as e:
                                        app_log.append('\n' + '应用启动后台出错_error(8):' + str(e))
                                        result['results'] = app_log
                                        return Response(result)
                        elif 'supervisor_start' in operation_arguments:
                            stop_cmd = operation_arguments['supervisor_start']
                            with requests.Session() as s:
                                saltapi = SaltAPI(session=s)
                                # 直接执行supervisor启动命令，只要不出现False，就执行查询状态命令，就看状态来决定成功与否
                                response_data = saltapi.supervisord_start_api(tgt=minion_id, arg=[stop_cmd])
                                # 当调用api失败的时候会返回false
                                if response_data['status'] is False:
                                    app_log.append('\n应用启动命令后台出错_error(10)，请联系管理员')
                                    result['results'] = app_log
                                    return Response(result)
                                else:
                                    # 查看是否有supervisor名称存在，不支持模糊搜索
                                    response_data = saltapi.supervisord_status_api(tgt=minion_id, arg=[stop_cmd])
                                    # 当调用api失败的时候会返回false
                                    if response_data['status'] is False:
                                        app_log.append('\n应用启动命令后台出错_error(11)，请联系管理员')
                                        result['results'] = app_log
                                        return Response(result)
                                    else:
                                        try:
                                            status_result = response_data['results']['return'][0][minion_id][stop_cmd]['state']
                                            if status_result == 'RUNNING':
                                                app_log.append('\n' + '应用启动成功<-\n')
                                            else:
                                                app_log.append('\n' + '应用启动查询状态结果有错，返回结果：' + str(response_data))
                                                result['results'] = app_log
                                                return Response(result)
                                        except Exception as e:
                                            logger.error('应用服务启动代码出错：' + str(e))
                                            app_log.append('\n' + '应用启动结果有错，返回结果：' + str(response_data))
                                            result['results'] = app_log
                                            return Response(result)
                    elif operation == '执行命令1':
                        execute_cmd = operation_arguments['cmd1']
                        if app_data.sys_type == 'windows':
                            execute_cmd = execute_cmd + '&& echo %errorlevel%'
                            split_cmd = '\r\n'
                        else:
                            execute_cmd = execute_cmd + '; echo $?'
                            split_cmd = '\n'
                        with requests.Session() as s:
                            saltapi = SaltAPI(session=s)
                            response_data = saltapi.cmd_run_api(tgt=minion_id,
                                                                arg=[execute_cmd, "shell='/bin/bash'",
                                                                     "runas='root'"])
                            # 当调用api失败的时候会返回false
                            if response_data['status'] is False:
                                app_log.append('\n执行命令1后台出错_error(1)，请联系管理员')
                                result['results'] = app_log
                                return Response(result)
                            else:
                                try:
                                    response_data = response_data['results']['return'][0][minion_id].rsplit(split_cmd, 1)
                                    # 发现有的命令没有输出那么最终只会有成功失败的0、1返回这时候列表长度就=1
                                    if len(response_data) == 1:
                                        if response_data[0] == '0':
                                            app_log.append('\n' + '执行命令1成功<-\n')
                                        else:
                                            app_log.append('\n' + '执行命令1失败:' + response_data[0])
                                            result['results'] = app_log
                                            return Response(result)
                                    else:
                                        if response_data[1] == '0':
                                            app_log.append('\n' + '执行命令1成功<-\n')
                                        else:
                                            app_log.append('\n' + '执行命令1失败:' + response_data[0])
                                            result['results'] = app_log
                                            return Response(result)
                                except Exception as e:
                                    app_log.append('\n' + '执行命令1失败_error(2):' + str(response_data))
                                    result['results'] = app_log
                                    return Response(result)
                    elif operation == '执行命令2':
                        execute_cmd = operation_arguments['cmd2']
                        if app_data.sys_type == 'windows':
                            execute_cmd = execute_cmd + '&& echo %errorlevel%'
                            split_cmd = '\r\n'
                        else:
                            execute_cmd = execute_cmd + '; echo $?'
                            split_cmd = '\n'
                        with requests.Session() as s:
                            saltapi = SaltAPI(session=s)
                            response_data = saltapi.cmd_run_api(tgt=minion_id,
                                                                arg=[execute_cmd, "shell='/bin/bash'",
                                                                     "runas='root'"])
                            # 当调用api失败的时候会返回false
                            if response_data['status'] is False:
                                app_log.append('\n执行命令2后台出错_error(1)，请联系管理员')
                                result['results'] = app_log
                                return Response(result)
                            else:
                                try:
                                    response_data = response_data['results']['return'][0][minion_id].rsplit(split_cmd, 1)
                                    # 发现有的命令没有输出那么最终只会有成功失败的0、1返回这时候列表长度就=1
                                    if len(response_data) == 1:
                                        if response_data[0] == '0':
                                            app_log.append('\n' + '执行命令2成功<-\n')
                                        else:
                                            app_log.append('\n' + '执行命令2失败:' + response_data[0])
                                            result['results'] = app_log
                                            return Response(result)
                                    else:
                                        if response_data[1] == '0':
                                            app_log.append('\n' + '执行命令2成功<-\n')
                                        else:
                                            app_log.append('\n' + '执行命令2失败:' + response_data[0])
                                            result['results'] = app_log
                                            return Response(result)
                                except Exception as e:
                                    app_log.append('\n' + '执行命令2失败_error(2):' + str(response_data))
                                    result['results'] = app_log
                                    return Response(result)

                app_log.append(
                    ('-' * 10 + ('Minion_ID:%s发布完成 时间戳%s' % (minion_id, time.strftime('%X'))) + '-' * 10).center(
                        88) + '\n\n\n\n\n\n')
            result['status'] = True
            result['results'] = app_log
            return Response(result)
        except Exception as e:
            logger.error(str(e))
            result['results'] = app_log
            result['results'].append('\n出错了：' + str(e))
            return Response(result)
        finally:
            if result['status']:
                release_result = '发布成功'
            else:
                release_result = '发布失败'
            username = self.request.user.username
            # 修改应用状态为空闲
            AppRelease.objects.filter(id=app_id).update(release_status='空闲', release_update_time=datetime.datetime.now())
            # 记录日志
            AppReleaseLog.objects.create(app_name=app_data.app_name, log_content=app_log, release_result=release_result,
                                         username=username)


# 应用发布 日志查询
class ReleaseLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    list:
        应用日志列表

    """
    queryset = AppReleaseLog.objects.all()
    serializer_class = release_serializers.ReleaseLogModelSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filter_fields = ('app_name',)
    pagination_class = StandardPagination

    # 自定义每页个数
    # pagination_class.page_size = 1
    ordering_fields = ('id', 'app_name')

    # 默认排序规则
    ordering = ('-id',)


# 应用发布组搜索过滤器
class ReleaseGroupFilter(django_filters.rest_framework.FilterSet):
    app_group_name = django_filters.CharFilter(field_name='app_group_name', lookup_expr='icontains')
    app_group_members = django_filters.CharFilter(field_name='app_group_members', lookup_expr='icontains')

    class Meta:
        model = AppGroup
        fields = ['app_group_name', 'app_group_members']


# 应用发布组 查询、创建、删除
class RealseaGroupViewSet(viewsets.ModelViewSet):
    """
        list:
            应用组信息列表

        create:
            创建应用组

        update:
            更新应用组

        destroy:
            删除应用组

        """
    queryset = AppGroup.objects.all()
    serializer_class = release_serializers.ReleaseGroupModelSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filter_class = ReleaseGroupFilter
    pagination_class = StandardPagination

    # 自定义每页个数
    # pagination_class.page_size = 1

    # 可选的排序规则
    ordering_fields = ('id', 'app_group_name')
    # 默认排序规则
    ordering = ('id',)



