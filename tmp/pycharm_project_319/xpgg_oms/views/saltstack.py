from django.http import JsonResponse, HttpResponseRedirect
from xpgg_oms.salt_api import SaltAPI
from xpgg_oms.models import *
from xpgg_oms import tasks
from .utils import getPage, StandardPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from xpgg_oms.serializers import saltstack_serializers
import requests
# 下面这个是py3解决requests请求https误报问题
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import logging
logger = logging.getLogger('xpgg_oms.views')


class SaltKeyViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    SaltKey列表信息
    """
    queryset = SaltKeyList.objects.all()
    serializer_class = saltstack_serializers.SaltKeySerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filter_fields = ('certification_status', 'id')
    # 引入公共分页类
    pagination_class = StandardPagination
    # 自定义每页个数
    pagination_class.page_size = 1
    # 搜索框
    search_fields = ('minion_id',)
    # 可选的排序规则
    ordering_fields = ('id', 'create_date')


# SaltKey管理
def saltkey_manage(request):
    try:
        if request.method == 'GET':
            accepted_count = SaltKeyList.objects.filter(certification_status='accepted').count()
            unaccepted_count = SaltKeyList.objects.filter(certification_status='unaccepted').count()
            denied_count = SaltKeyList.objects.filter(certification_status='denied').count()
            rejected_count = SaltKeyList.objects.filter(certification_status='rejected').count()
            if request.GET.get('status') is None:
                return HttpResponseRedirect('/saltkey_manage/?status=accepted&search=')
            if request.GET.get('status') == 'accepted':
                if request.GET.get('search').strip() is "":
                    accepted_data = SaltKeyList.objects.filter(certification_status='accepted')
                    data_list = getPage(request, accepted_data, 8)
                    return render(request, 'saltstack/saltkey_manage.html',
                                  {'data_list': data_list, 'accepted_count': accepted_count,
                                   'unaccepted_count': unaccepted_count, 'denied_count': denied_count,
                                   'rejected_count': rejected_count, 'search': ""})
                else:
                    search_data = request.GET.get('search').strip()
                    accepted_data = SaltKeyList.objects.filter(minion_id__icontains=search_data, certification_status='accepted')
                    data_list = getPage(request, accepted_data, 8)
                    return render(request, 'saltstack/saltkey_manage.html',
                                  {'data_list': data_list, 'accepted_count': accepted_count,
                                   'unaccepted_count': unaccepted_count, 'denied_count': denied_count,
                                   'rejected_count': rejected_count, 'search': search_data})
            elif request.GET.get('status') == 'unaccepted':
                if request.GET.get('search').strip() is "":
                    unaccepted_data = SaltKeyList.objects.filter(certification_status='unaccepted')
                    data_list = getPage(request, unaccepted_data, 8)
                    return render(request, 'saltstack/saltkey_manage_unaccepted.html',
                                  {'data_list': data_list, 'accepted_count': accepted_count,
                                   'unaccepted_count': unaccepted_count, 'denied_count': denied_count,
                                   'rejected_count': rejected_count, 'search': ""})
                else:
                    search_data = request.GET.get('search').strip()
                    unaccepted_data = SaltKeyList.objects.filter(minion_id__icontains=search_data, certification_status='unaccepted')
                    data_list = getPage(request, unaccepted_data, 8)
                    return render(request, 'saltstack/saltkey_manage_unaccepted.html',
                                  {'data_list': data_list, 'accepted_count': accepted_count,
                                   'unaccepted_count': unaccepted_count, 'denied_count': denied_count,
                                   'rejected_count': rejected_count, 'search': search_data})
            elif request.GET.get('status') == 'denied':
                if request.GET.get('search').strip() is "":
                    denied_data = SaltKeyList.objects.filter(certification_status='denied')
                    data_list = getPage(request, denied_data, 8)
                    return render(request, 'saltstack/saltkey_manage_denied.html',
                                  {'data_list': data_list, 'accepted_count': accepted_count,
                                   'unaccepted_count': unaccepted_count, 'denied_count': denied_count,
                                   'rejected_count': rejected_count, 'search': ""})
                else:
                    search_data = request.GET.get('search').strip()
                    denied_data = SaltKeyList.objects.filter(minion_id__icontains=search_data, certification_status='denied')
                    data_list = getPage(request, denied_data, 8)
                    return render(request, 'saltstack/saltkey_manage_denied.html',
                                  {'data_list': data_list, 'accepted_count': accepted_count,
                                   'unaccepted_count': unaccepted_count, 'denied_count': denied_count,
                                   'rejected_count': rejected_count, 'search': search_data})
            elif request.GET.get('status') == 'rejected':
                if request.GET.get('search').strip() is "":
                    rejected_data = SaltKeyList.objects.filter(certification_status='rejected')
                    data_list = getPage(request, rejected_data, 8)
                    return render(request, 'saltstack/saltkey_manage_rejected.html',
                                  {'data_list': data_list, 'accepted_count': accepted_count,
                                   'unaccepted_count': unaccepted_count, 'denied_count': denied_count,
                                   'rejected_count': rejected_count, 'search': ""})
                else:
                    search_data = request.GET.get('search').strip()
                    rejected_data = SaltKeyList.objects.filter(minion_id__icontains=search_data, certification_status='rejected')
                    data_list = getPage(request, rejected_data, 8)
                    return render(request, 'saltstack/saltkey_manage_rejected.html',
                                  {'data_list': data_list, 'accepted_count': accepted_count,
                                   'unaccepted_count': unaccepted_count, 'denied_count': denied_count,
                                   'rejected_count': rejected_count, 'search': search_data})

    except Exception as e:
        logger.error('SaltKey管理页面有问题', e)
        return render(request, 'saltstack/saltkey_manage.html')


# SaltKey全局操作
def salt_key_global(request):
    try:
        if 'global_flush_salt_key' in request.POST:
            logger.error('这里')
            if tasks.saltkey_list():
                return JsonResponse({'result': '操作成功', 'status': True})
            else:
                return JsonResponse({'result': '操作失败', 'status': False})
    except Exception as e:
        logger.error('全局操作出错了' + str(e))
        response_data = {'result': '操作失败', 'status': False}
        return JsonResponse(response_data)


# salt的test.ping方法
def salt_test_ping(request):
    try:
        minion_id = request.POST.get('minion_id')
        logger.error(minion_id)
        with requests.Session() as s:
            saltapi = SaltAPI(session=s)
            if saltapi.get_token() is False:
                logger.error('test.ping操作获取SaltAPI调用get_token请求出错')
                response_data = {'result': '检测失败', 'status': False}
                return JsonResponse(response_data)
            else:
                response_data = saltapi.test_api(tgt=minion_id)
                # 当调用api失败的时候比如salt-api服务stop了会返回false
                if response_data is False:
                    logger.error('test.ping失败可能代入的参数有问题，SaltAPI调用test_api请求出错')
                    response_data = {'result': '检测失败', 'status': False}
                    return JsonResponse(response_data)
                # 判断返回值如果为[{}]表明没有这个minion_id
                elif response_data['return'] != [{}]:
                    # 正常结果类似这样：{'return': [{'192.168.68.51': False, '192.168.68.1': True, '192.168.68.50-master': True}]}
                    data_source = response_data['return'][0]
                    response_data = {'result': data_source, 'status': True}
                    return JsonResponse(response_data)
                else:
                    logger.error('test.ping检测失败，请确认minion是否存在。。')
                    response_data = {'result': '检测失败', 'status': False}
                    return JsonResponse(response_data)
    except Exception as e:
        logger.error('test.ping检测出错了' + str(e))
        response_data = {'result': '检测失败', 'status': False}
        return JsonResponse(response_data)