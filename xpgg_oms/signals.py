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

