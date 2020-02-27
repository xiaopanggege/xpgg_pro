from rest_framework import serializers
from xpgg_oms.models import SaltKeyList, MinionList, SaltCmdInfo
import logging
logger = logging.getLogger('xpgg_oms.views')


# SaltKey List操作序列化类
class SaltKeySerializer(serializers.ModelSerializer):
    class Meta:
        # 设置继承的数据库
        model = SaltKeyList
        # 设置显示的字段
        fields = "__all__"


# SaltKey 刷新操作序列化类
class SaltKeyFlushSerializer(serializers.Serializer):
    salt_key_tag = serializers.CharField(max_length=100, help_text='执行操作字段')

    def validate_salt_key_tag(self, value):
        if value != 'global_flush_salt_key':
            raise serializers.ValidationError("未知的参数")
        return value


# SaltKey 接受认证操作序列化类
class SaltKeyAcceptSerializer(serializers.Serializer):
    salt_key_tag = serializers.CharField(max_length=100, help_text='执行操作字段')
    minion_id = serializers.ListField(required=False, help_text='增删改时需传递minion_id列表')

    def validate_salt_key_tag(self, value):
        if value != 'accept_salt_key':
            raise serializers.ValidationError("未知的参数")
        return value


# SaltKey 删除认证操作序列化类
class SaltKeyDeleteSerializer(serializers.Serializer):
    salt_key_tag = serializers.CharField(max_length=100, help_text='执行操作字段')
    minion_id = serializers.ListField(required=False, help_text='增删改时需传递minion_id列表')

    def validate_salt_key_tag(self, value):
        if value != 'delete_salt_key':
            raise serializers.ValidationError("未知的参数")
        return value


# SaltKey 拒绝认证操作序列化类
class SaltKeyRejectSerializer(serializers.Serializer):
    salt_key_tag = serializers.CharField(max_length=100, help_text='执行操作字段')
    minion_id = serializers.ListField(required=False, help_text='增删改时需传递minion_id列表')

    def validate_salt_key_tag(self, value):
        if value != 'reject_salt_key':
            raise serializers.ValidationError("未知的参数")
        return value


# SaltKey 删除denied操作序列化类
class SaltKeyDeleteDeniedSerializer(serializers.Serializer):
    salt_key_tag = serializers.CharField(max_length=100, help_text='执行操作字段')
    minion_id = serializers.ListField(required=False, help_text='增删改时需传递minion_id列表')

    def validate_salt_key_tag(self, value):
        if value != 'delete_denied_salt_key':
            raise serializers.ValidationError("未知的参数")
        return value


# Minion List操作序列化类
class SaltMinionSerializer(serializers.ModelSerializer):
    class Meta:
        # 设置继承的数据库
        model = MinionList
        # 设置显示的字段
        fields = "__all__"


# Minion 更新minion列表操作序列化类
class SaltMinionListUpdateSerializer(serializers.Serializer):
    salt_minion_tag = serializers.CharField(max_length=100, help_text='执行操作字段')

    def validate_salt_minion_tag(self, value):
        if value != 'global_update_salt_minion_list':
            raise serializers.ValidationError("未知的参数")
        return value

# Minion 更新minion状态操作序列化类
class SaltMinionStateUpdateSerializer(serializers.Serializer):
    salt_minion_tag = serializers.CharField(max_length=100, help_text='执行操作字段')

    def validate_salt_minion_tag(self, value):
        if value != 'global_update_salt_minion_status':
            raise serializers.ValidationError("未知的参数")
        return value


# Minion 更新单个minion操作序列化类
class SaltMinionUpdateSerializer(serializers.Serializer):
    salt_minion_tag = serializers.CharField(max_length=100, help_text='执行操作字段')
    minion_id = serializers.CharField(required=False, help_text='单个更新需传递minion_id')

    def validate_salt_minion_tag(self, value):
        if value != 'update_salt_minion':
            raise serializers.ValidationError("未知的参数")
        return value


# Salt命令集操作序列化类
class SaltCmdSerializer(serializers.ModelSerializer):
    class Meta:
        # 设置继承的数据库
        model = SaltCmdInfo
        # 设置显示的字段
        fields = "__all__"


# Salt命令集 收集操作序列化类
class SaltCmdPostSerializer(serializers.Serializer):
    salt_cmd_tag = serializers.CharField(max_length=100, help_text='执行操作字段')
    collection_style = serializers.CharField(required=False, help_text='需要收集的命令类型')
    minions = serializers.CharField(required=False, help_text='来源选择，可以是逗号隔开的多个minion_id字符串')

    def validate_salt_cmd_tag(self, value):
        if value != 'collection_info':
            raise serializers.ValidationError("未知的参数")
        return value


# Salt命令集 Post操作序列化类
class SaltCmdDeleteSerializer(serializers.Serializer):
    salt_cmd_tag = serializers.CharField(max_length=100, help_text='执行操作字段')

    def validate_salt_cmd_tag(self, value):
        if value != 'salt_cmd_delete':
            raise serializers.ValidationError("未知的参数")
        return value


# Salt命令集 只显示salt_cmd_module字段操作序列化类
class SaltCmdModuleListSerializer(serializers.ModelSerializer):
    class Meta:
        # 设置继承的数据库
        model = SaltCmdInfo
        # 设置显示的字段
        fields = ('salt_cmd_module',)


# Salt命令集 只显示salt_cmd字段操作序列化类
class SaltCmdCmdListSerializer(serializers.ModelSerializer):
    class Meta:
        # 设置继承的数据库
        model = SaltCmdInfo
        # 设置显示的字段
        fields = ('salt_cmd',)


# Salt命令执行 Post操作序列化类
class SaltExeSerializer(serializers.Serializer):
    salt_exe_tag = serializers.CharField(max_length=100, help_text='执行操作字段')
    client = serializers.CharField(max_length=100, help_text='执行操作字段')
    tgt = serializers.CharField(required=False, help_text='执行操作字段')
    tgt_type = serializers.CharField(required=False, help_text='执行操作字段')
    fun = serializers.CharField(help_text='执行操作字段')
    arg = serializers.ListField(required=False, help_text='执行操作字段')

    def validate_salt_cmd_tag(self, value):
        if value != 'salt_exe':
            raise serializers.ValidationError("未知的参数")
        return value


# Salt快捷工具 任务查询 状态查询操作序列化类
class SaltToolJobStatusSerializer(serializers.Serializer):
    salt_tool_tag = serializers.CharField(max_length=100, help_text='执行操作字段')
    jid = serializers.CharField(max_length=100, help_text='jid')

    def validate_salt_cmd_tag(self, value):
        if value != 'search_jid_status':
            raise serializers.ValidationError("未知的参数")
        return value


# Salt快捷工具 任务查询 结果查询操作序列化类
class SaltToolJobResultSerializer(serializers.Serializer):
    salt_tool_tag = serializers.CharField(max_length=100, help_text='执行操作字段')
    jid = serializers.CharField(max_length=100, help_text='jid')

    def validate_salt_cmd_tag(self, value):
        if value != 'search_jid_result':
            raise serializers.ValidationError("未知的参数")
        return value


# 文件管理 获取文件树结构
class FileeManageTreeSerializer(serializers.Serializer):
    base_path = serializers.CharField(required=False, max_length=500, help_text='salt-master的file_roots路径')


# 文件管理 获取文件内容参数序列化
class FileManageContentSerializer(serializers.Serializer):
    file_size = serializers.CharField(max_length=100, help_text='文件大小')
    file_path = serializers.CharField(max_length=500, help_text='文件全路径')
    file_type = serializers.CharField(max_length=10, help_text='文件类型')


# 文件管理 文件更新传参序列化
class FileManageUpdateSerializer(serializers.Serializer):
    file = serializers.CharField(help_text='更新文件内容')
    file_name = serializers.CharField(max_length=100, help_text='更新文件名')
    file_path = serializers.CharField(max_length=500, help_text='更新文件全路径')


# 文件管理 创建文件或者文件夹参数序列化
class FileManageCreateSerializer(serializers.Serializer):
    file_path = serializers.CharField(max_length=500, help_text='文件全路径')
    file_type = serializers.CharField(max_length=10, help_text='文件类型')


# 文件管理 重命名文件或者文件夹参数序列化
class FileManageRenameSerializer(serializers.Serializer):
    old_name = serializers.CharField(max_length=500, help_text='原文件全路径')
    new_name = serializers.CharField(max_length=500, help_text='新文件全路径')


# 文件管理 删除文件或者文件夹参数序列化
class FileManageDeleteSerializer(serializers.Serializer):
    file_path = serializers.CharField(max_length=500, help_text='文件全路径')


# 文件管理 上传文件参数序列化
class FileManageUploadSerializer(serializers.Serializer):
    file_path = serializers.CharField(max_length=500, help_text='文件全路径')
    file_name = serializers.CharField(max_length=100, help_text='文件名')
    file = serializers.FileField(max_length=100, help_text='文件')
