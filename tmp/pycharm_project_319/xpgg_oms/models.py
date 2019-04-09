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
        return str(self.id)