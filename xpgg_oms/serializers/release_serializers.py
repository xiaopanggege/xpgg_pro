from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.conf import settings
from xpgg_oms.models import AppRelease, AppReleaseLog, AppGroup, AppAuth
import time
import datetime
import json
import logging
logger = logging.getLogger('xpgg_oms.views')


# 应用list序列化类
class ReleaseModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppRelease
        fields = '__all__'


# 应用创建息序列化类
class ReleaseCreateSerializer(serializers.Serializer):
    app_name = serializers.CharField(max_length=100, help_text='应用名称', validators=[UniqueValidator(queryset=AppRelease.objects.all(), message='应用名称已存在！')])
    sys_type = serializers.CharField(max_length=20, help_text='系统类型')
    minion_list = serializers.CharField(max_length=2000, help_text='minion_list')
    app_path = serializers.CharField(max_length=2000, help_text='应用目录')
    app_path_owner = serializers.CharField(required=False, max_length=20, help_text='应用目录属主')
    # co_path = serializers.CharField(max_length=500, help_text='SVN/GIT检出目录')
    app_svn_url = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=500, help_text='SVN地址')
    app_svn_user = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50, help_text='SVN账户')
    app_svn_password = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50, help_text='SVN密码')
    app_git_url = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=500, help_text='git地址')
    app_git_user = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50, help_text='git账户')
    app_git_password = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50, help_text='git密码')
    app_git_branch = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50, help_text='git分支')
    sync_file_check_diff = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50, help_text='同步文件检查方式')
    sync_file_method = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50, help_text='同步文件方式')
    rsync_ip = serializers.IPAddressField(required=False, allow_blank=True, allow_null=True, max_length=50, help_text='rsync_ip')
    rsync_port = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50, help_text='rsync_port')
    app_stop_style = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50, help_text='应用停止方式')
    app_stop_cmd = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=2000, help_text='应用停止命令')
    app_start_style = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50, help_text='应用启动方式')
    app_start_cmd = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=2000, help_text='应用启动命令')
    cmd1 = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=2000, help_text='命令执行1')
    cmd2 = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=2000, help_text='命令执行2')
    execution_style = serializers.CharField(max_length=20, help_text='多主机执行顺序')
    operation_list = serializers.ListField(max_length=400, help_text='操作列表')
    operation_arguments = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=4000, help_text='操作参数')
    app_backup_path = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=400, help_text='应用备份目录')
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=500, help_text='描述备注')

    def validate(self, data):
        operation_arguments = {}
        error_msg = {}
        # 由于上面默认的验证返回错误信息是这种格式的{'app_name':['字段必须唯一'],'app_start_cmd':['字段不为空']}
        # 所以下面自定义的错误也要这种格式
        if 'SVN更新' in data.get('operation_list'):
            if data.get('app_svn_url', '').strip():
                operation_arguments['app_svn_url'] = data.get('app_svn_url')
            else:
                error_msg['app_svn_url'] = ['svn地址不能为空']
            if data.get('app_svn_user', '').strip():
                operation_arguments['app_svn_user'] = data.get('app_svn_user')
            else:
                error_msg['app_svn_user'] = ['svn用户不能为空']
            if data.get('app_svn_password', '').strip():
                operation_arguments['app_svn_password'] = data.get('app_svn_password')
            else:
                error_msg['app_svn_password'] = ['svn密码不能为空']
        if 'GIT更新' in data.get('operation_list'):
            if data.get('app_git_url', '').strip():
                operation_arguments['app_git_url'] = data.get('app_git_url')
            else:
                error_msg['app_git_url'] = ['git地址不能为空']
            if data.get('app_git_user', '').strip():
                operation_arguments['app_git_user'] = data.get('app_git_user')
            else:
                error_msg['app_git_user'] = ['git用户不能为空']
            if data.get('app_git_password', '').strip():
                operation_arguments['app_git_password'] = data.get('app_git_password')
            else:
                error_msg['app_git_password'] = ['git密码不能为空']
            if data.get('app_git_branch', '').strip():
                operation_arguments['app_git_branch'] = data.get('app_git_branch')
            else:
                error_msg['app_git_branch'] = ['git分支不能为空']
        if '同步文件' in data.get('operation_list'):
            if data.get('sync_file_check_diff', '').strip():
                operation_arguments['sync_file_check_diff'] = data.get('sync_file_check_diff')
            else:
                error_msg['sync_file_check_diff'] = ['同步文件检查方式不能为空']
            if data.get('sync_file_method', '').strip() == 'rsync':
                operation_arguments['sync_file_method'] = data.get('sync_file_method')
                if data.get('rsync_ip', '').strip():
                    operation_arguments['rsync_ip'] = data.get('rsync_ip')
                else:
                    error_msg['rsync_ip'] = ['rsync_ip不能为空']
                if data.get('rsync_port', '').strip():
                    operation_arguments['rsync_port'] = data.get('rsync_port')
                else:
                    error_msg['rsync_port'] = ['rsync_port不能为空']
            elif data.get('sync_file_method', '').strip() == 'salt':
                operation_arguments['sync_file_method'] = data.get('sync_file_method')
            else:
                error_msg['sync_file_method'] = ['同步文件方式不能为空']
        if '应用停止' in data.get('operation_list'):
            if data.get('app_stop_style', '').strip():
                operation_arguments['app_stop_style'] = data.get('app_stop_style')
            else:
                error_msg['app_stop_style'] = ['应用停止方式不能为空']
            if data.get('app_stop_cmd', '').strip():
                if data.get('app_stop_style', '').strip() == '映像名称和命令行':
                    # 映像名称中出现双引号或者单引号要去掉，因为后台psutil命令返回结果拼接的时候去掉了引号，所以这里也要去掉才能逻辑匹配到
                    operation_arguments['app_stop_cmd'] = data.get('app_stop_cmd').replace('"', '').replace("'", '')
                else:
                    operation_arguments['app_stop_cmd'] = data.get('app_stop_cmd')
            else:
                error_msg['app_stop_cmd'] = ['应用停止命令不能为空']

        if '应用启动' in data.get('operation_list'):
            if data.get('app_start_style', '').strip():
                operation_arguments['app_start_style'] = data.get('app_start_style')
            else:
                error_msg['app_start_style'] = ['应用启动方式不能为空']
            if data.get('app_start_cmd', '').strip():
                operation_arguments['app_start_cmd'] = data.get('app_start_cmd')
            else:
                error_msg['app_start_cmd'] = ['应用启动命令不能为空']
        if '命令执行1' in data.get('operation_list'):
            if data.get('cmd1', '').strip():
                operation_arguments['cmd1'] = data.get('cmd1')
            else:
                error_msg['cmd1'] = ['命令执行1不能为空']
        if '命令执行2' in data.get('operation_list'):
            if data.get('cmd2', '').strip():
                operation_arguments['cmd2'] = data.get('cmd2')
            else:
                error_msg['cmd2'] = ['命令执行2不能为空']
        if len(error_msg):
            raise serializers.ValidationError(error_msg)
        else:
            data['operation_arguments'] = operation_arguments
            return data

    def create(self, validated_data):
        data = dict()
        data['app_name'] = validated_data.get('app_name').strip()
        data['sys_type'] = validated_data.get('sys_type').strip()
        data['minion_list'] = validated_data.get('minion_list').strip()
        data['app_path'] = validated_data.get('app_path').strip()
        data['app_path_owner'] = validated_data.get('app_path_owner').strip()
        data['execution_style'] = validated_data.get('execution_style').strip()
        data['co_path'] = settings.SITE_BASE_CO_PATH + time.strftime('%Y%m%d_%H%M%S')
        data['operation_list'] = json.dumps(validated_data.get('operation_list'), ensure_ascii=False)
        data['operation_arguments'] = json.dumps(validated_data.get('operation_arguments'), ensure_ascii=False)
        data['update_time'] = datetime.datetime.now()
        data['app_backup_path'] = validated_data.get('app_backup_path').strip()
        data['description'] = validated_data.get('description').strip()
        return AppRelease.objects.create(**data)

    def update(self, instance, validated_data):
        instance.app_name = validated_data.get('app_name', instance.app_name)
        instance.sys_type = validated_data.get('sys_type', instance.sys_type)
        instance.minion_list = validated_data.get('minion_list', instance.minion_list)
        instance.app_path = validated_data.get('app_path', instance.app_path)
        instance.app_path_owner = validated_data.get('app_path_owner', instance.app_path_owner)
        instance.execution_style = validated_data.get('execution_style', instance.execution_style)
        # instance.co_path = settings.SITE_BASE_CO_PATH + time.strftime('%Y%m%d_%H%M%S')
        instance.co_status = validated_data.get('co_status', instance.co_status)
        instance.operation_list = json.dumps(validated_data.get('operation_list', json.loads(instance.operation_list)), ensure_ascii=False)
        instance.operation_arguments = json.dumps(validated_data.get('operation_arguments', json.loads(instance.operation_arguments)), ensure_ascii=False)
        instance.update_time = datetime.datetime.now()
        instance.app_backup_path = validated_data.get('app_backup_path', instance.app_backup_path)
        instance.description = validated_data.get('description', instance.description)
        instance.save()
        return instance


# 应用发布序列化类
class ReleaseOperationSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text='应用发布id')
    single_cmd = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50, help_text='单项操作指令')
    release_version = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50, help_text='SVN/GIT版本号')

    def validate_id(self, value):
        if not AppRelease.objects.filter(id=value).exists():
            raise serializers.ValidationError("id不存在")
        return value


# 应用发布 删除序列化
class ReleaseDeleteSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text='应用发布id')
    delete_app_file_select = serializers.CharField(max_length=100, help_text='是否删除应用目录,等于delete_app_file表示删除')

    def validate_id(self, value):
        if not AppRelease.objects.filter(id=value).exists():
            raise serializers.ValidationError("id不存在")
        return value


# 应用日志list序列化类
class ReleaseLogModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppReleaseLog
        fields = '__all__'


# 应用发布组list序列化类
class ReleaseGroupModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppGroup
        fields = '__all__'

