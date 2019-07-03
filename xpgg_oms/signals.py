from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from xpgg_oms.models import *
import datetime
import json
import logging
# Create your views here.
logger = logging.getLogger('xpgg_oms.views')


# 在操作saltkey表的保存时候同时对minion管理表做创建或更新操作
@receiver(post_save, sender=SaltKeyList, dispatch_uid="saltkey_list_post_save")
def create_minion_list(sender, instance, created, update_fields, **kwargs):
    if created and instance.certification_status == 'accepted':
        updated_values = {'minion_id': instance.minion_id, 'minion_status': '在线', 'update_time': datetime.datetime.now()}
        MinionList.objects.update_or_create(minion_id=instance.minion_id, defaults=updated_values)


# 在操作saltkey表的删除时候同时对minion管理表做删除操作
@receiver(post_delete, sender=SaltKeyList, dispatch_uid="saltkey_list_post_delete")
def delete_minion_list(sender, instance, **kwargs):
    if instance.certification_status == 'accepted':
        MinionList.objects.filter(minion_id=instance.minion_id).delete()


# 在操作用户表表的删除时候同时对AppAuth表做删除对应用户操作
@receiver(post_delete, sender=MyUser, dispatch_uid="MyUser_post_delete")
def delete_app_auth_myuser(sender, instance, **kwargs):
    AppAuth.objects.filter(my_user_id=instance.id).delete()


# 在操作用户表表的更新时候同时对AppAuth表做更新对应用户操作
@receiver(post_save, sender=MyUser, dispatch_uid="MyUser_post_update")
def update_app_auth_myuser(sender, instance, created, **kwargs):
    if not created:
        check_exists = AppAuth.objects.filter(my_user_id=instance.id).exists()
        if check_exists:
            new_username = instance.username
            old_username = AppAuth.objects.get(my_user_id=instance.id).username
            if new_username != old_username:
                AppAuth.objects.filter(my_user_id=instance.id).update(username=instance.username)


# 在操作AppRelease表的删除时候同时对AppAuth表做删除对应权限操作
@receiver(post_delete, sender=AppRelease, dispatch_uid="AppRelease_post_delete")
def delete_app_auth_apprelease(sender, instance, **kwargs):
    # 这个匹配主要是坑在，前端是用json把数组变成了字符串传回来是[1,2,3,4]第一次用app_perms__regex=r'^%d$|^%d,|,%d$|,%d,没什么问题
    # 但是经过第一次后下面python的json.loads会把列表变成[1, 2, 3, 4]中间有一个空格。。第一次发现，所以正则又要多加几种匹配
    app_auth_obj = AppAuth.objects.filter(app_perms__regex=r'^%d$|^%d,|,%d$|, %d$|,%d,|, %d, ' % (instance.id, instance.id, instance.id, instance.id, instance.id, instance.id))
    for obj in app_auth_obj:
        app_perms_list = json.loads(obj.app_perms)
        app_perms_list.remove(instance.id)
        obj.app_perms = json.dumps(app_perms_list)
        obj.save()


# 在操作AppGroup表的删除时候同时对AppAuth表做删除对应权限操作
@receiver(post_delete, sender=AppGroup, dispatch_uid="AppGroup_post_delete")
def delete_app_auth_appgroup(sender, instance, **kwargs):
    app_auth_obj = AppAuth.objects.filter(app_perms__regex=r'^%d$|^%d,|,%d$|, %d$|,%d,|, %d, ' % (instance.id, instance.id, instance.id, instance.id, instance.id, instance.id))
    for obj in app_auth_obj:
        app_group_perms_list = json.loads(obj.app_group_name)
        app_group_perms_list.remove(instance.app_group_name)
        obj.app_group_perms = json.dumps(app_group_perms_list)
        obj.save()