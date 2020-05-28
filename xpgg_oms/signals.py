from django.db.models.signals import post_save, pre_delete, post_delete, pre_save
from django.dispatch import receiver
from xpgg_oms.models import *
from django_celery_results.models import TaskResult
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


# 这个信号想了几天才想到用信号来完成，玛德垃圾的django_celery_results这个扩展默认记录的任务结果没办法知道到底是哪个任务执行产生的结果
# 他只记录的任务调用的任务模板task_name，这样我很多个任务调用同一个模板的时候结果显示都是同样的task_name，根本无法区分是哪个任务的结果
# 于是我在创建任务的时候把任务名称periodic_name作为一个key写入到任务的task_kwargs里，这个操作在我自己的前端页面创建任务的时候添加了
# 如果用amdin后台添加并且也想要个性化task_name，一样需要在设置任务时候的Keyword Arguments里添加periodic_name参数值
# 在计划任务结果表task result创建的时候修改他的task_name值
@receiver(pre_save, sender=TaskResult, dispatch_uid="TaskResult_post_create")
def create_taskresult(sender, instance, **kwargs):
    # 本来是用json(instance.task_kwargs)，玛德没想到数据进来以后不是标准json格式里面是单引号奶奶的只能用eval解
    if 'periodic_name' in eval(instance.task_kwargs):
        instance.task_name = eval(instance.task_kwargs)['periodic_name']

