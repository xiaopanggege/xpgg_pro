from django.db import models
from django.contrib.auth.models import AbstractUser, AbstractBaseUser
# Create your models here.


# 继承admin的user表，不在这方面花太多精力自己做用户管理
class MyUser(AbstractUser):
    avatar = models.ImageField(upload_to='avatar/%Y/%m', max_length=200, verbose_name='用户头像',
                               default='avatar/default.png')

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = verbose_name
        ordering = ['id']

    def __str__(self):
        return self.username


# salt-key信息表
class SaltKeyList(models.Model):
    minion_id = models.CharField(max_length=20, verbose_name='MinionID')
    certification_status = models.CharField(max_length=20, verbose_name='认证状态')
    update_time = models.DateTimeField(auto_now=True, verbose_name='最近一次更新时间')
    create_date = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = 'Salt-key信息表'
        verbose_name_plural = verbose_name
        ordering = ['id']

    def __str__(self):
        return str(self.minion_id)


# minion客户端信息表
class MinionList(models.Model):
    minion_id = models.CharField(max_length=20, verbose_name='MinionID', primary_key=True)
    ip = models.CharField(max_length=200, verbose_name='IP地址', blank=True, null=True)
    minion_version = models.CharField(max_length=20, verbose_name='Minion版本', blank=True, null=True)
    system_issue = models.CharField(max_length=200, verbose_name='系统版本', blank=True, null=True)
    sn = models.CharField(max_length=200, verbose_name='SN', blank=True, null=True)
    cpu_num = models.IntegerField(verbose_name='CPU核数', blank=True, null=True)
    cpu_model = models.CharField(max_length=200, verbose_name='CPU型号', blank=True, null=True)
    sys = models.CharField(max_length=200, verbose_name='系统类型', blank=True, null=True)
    kernel = models.CharField(max_length=200, verbose_name='内核', blank=True, null=True)
    product_name = models.CharField(max_length=200, verbose_name='品牌名称', blank=True, null=True)
    ipv4_address = models.CharField(max_length=900, verbose_name='ipv4地址', blank=True, null=True)
    mac_address = models.CharField(max_length=900, verbose_name='mac地址', blank=True, null=True)
    localhost = models.CharField(max_length=200, verbose_name='主机名', blank=True, null=True)
    mem_total = models.IntegerField(verbose_name='内存大小', blank=True, null=True)
    create_date = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='最近一次更新时间')
    minion_status = models.CharField(max_length=50, verbose_name='Minion状态', blank=True, null=True)
    description = models.CharField(max_length=200, verbose_name='描述备注', blank=True, null=True)

    class Meta:
        verbose_name = 'Minion列表'
        verbose_name_plural = verbose_name
        ordering = ['create_date']

    def __str__(self):
        return self.minion_id


# salt命令集信息表
class SaltCmdInfo(models.Model):
    salt_cmd = models.CharField(max_length=100, verbose_name='命令')
    salt_cmd_type = models.CharField(max_length=20, verbose_name='类型', blank=True, null=True)
    salt_cmd_module = models.CharField(max_length=200, verbose_name='模块', blank=True, null=True)
    salt_cmd_source = models.CharField(max_length=200, verbose_name='命令来源', blank=True, null=True)
    salt_cmd_doc = models.TextField(verbose_name='命令帮助信息', blank=True, null=True)
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='最近一次更新时间')
    description = models.TextField(verbose_name='描述备注', blank=True, null=True)

    class Meta:
        # 复合主键其实就是联合唯一索引,因为必须2个判断唯一，另外这样会自动生成ID主键
        unique_together = ("salt_cmd", "salt_cmd_type")
        verbose_name = 'salt命令集表'
        verbose_name_plural = verbose_name
        ordering = ['salt_cmd_type', 'salt_cmd']

    def __str__(self):
        return self.salt_cmd


# 应用发布系统 应用信息表
class AppRelease(models.Model):
    app_name = models.CharField(max_length=100, verbose_name='应用名称', unique=True)
    sys_type = models.CharField(max_length=20, verbose_name='系统类型', blank=True, null=True)
    minion_list = models.CharField(max_length=2000, verbose_name='minion_list', blank=True, null=True)
    app_path = models.CharField(max_length=2000, verbose_name='应用目录', blank=True, null=True)
    app_path_owner = models.CharField(max_length=20, verbose_name='应用目录属主', blank=True, null=True)
    co_path = models.CharField(max_length=500, verbose_name='SVN/GIT等检出目录', blank=True, null=True)
    co_status = models.NullBooleanField(max_length=20, verbose_name='SVN/GIT等检出状态', default=False, blank=True, null=True)
    execution_style = models.CharField(max_length=20, verbose_name='多主机执行顺序', blank=True, null=True)
    operation_list = models.CharField(max_length=400, verbose_name='操作列表', blank=True, null=True)
    operation_arguments = models.CharField(max_length=4000, verbose_name='操作参数', blank=True, null=True)
    app_backup_path = models.CharField(max_length=400, verbose_name='应用备份目录', blank=True, null=True)
    release_status = models.CharField(max_length=40, verbose_name='发布状态', default='空闲')
    release_update_time = models.DateTimeField(auto_now=True, verbose_name='最近一次发布时间', blank=True, null=True)
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='最近一次更新时间')
    description = models.CharField(max_length=500, verbose_name='描述备注', blank=True, null=True)

    class Meta:
        verbose_name = '应用发布信息表'
        verbose_name_plural = verbose_name
        ordering = ['create_time']

    def __str__(self):
        return self.app_name


# 应用发布系统 应用发布日志表
class AppReleaseLog(models.Model):
    app_name = models.CharField(max_length=100, verbose_name='应用名称', blank=True, null=True)
    log_content = models.TextField(verbose_name='日志内容', blank=True, null=True)
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    release_result = models.CharField(max_length=20, verbose_name='发布结果', blank=True, null=True)
    username = models.CharField(max_length=20, verbose_name='操作人', blank=True, null=True)

    class Meta:
        verbose_name = '应用发布日志表'
        verbose_name_plural = verbose_name
        ordering = ['id']

    def __str__(self):
        return str(self.id)