# 公用全局方法
from rest_framework.views import exception_handler
from rest_framework.response import Response
from django.utils import six
from rest_framework.serializers import Serializer
from rest_framework.pagination import PageNumberPagination
from django.conf import settings
from django.core.paginator import Paginator
import logging
logger = logging.getLogger('xpgg_oms.views')


# 自定义rest framework的异常捕获返回,在settings里调用
def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Now add the HTTP status code to the response.
    if response is not None:
        response.data['code'] = response.status_code
        # 这个可以使所有错误码改成200返回，然后在code中指定返回码
        # response.status_code = 200
        try:
            # 可能没有detail所以要用try
            response.data['message'] = response.data['detail']
            del response.data['detail']
        except Exception as e:
            pass

    return response

# 参考：
# def custom_exception_handler(exc, context):
#     # Call REST framework's default exception handler first,
#     # to get the standard error response.
#     response = exception_handler(exc, context)
#
#     # Now add the HTTP status code to the response.
#     if response is not None:
#         print(response.data)
#         response.data.clear()
#         response.data['code'] = response.status_code
#         response.data['data'] = []
#
#         if response.status_code == 404:
#             try:
#                 response.data['message'] = response.data.pop('detail')
#                 response.data['message'] = "Not found"
#             except KeyError:
#                 response.data['message'] = "Not found"
#
#         if response.status_code == 400:
#             response.data['message'] = 'Input error'
#
#         elif response.status_code == 401:
#             response.data['message'] = "Auth failed"
#
#         elif response.status_code >= 500:
#             response.data['message'] =  "Internal service errors"
#
#         elif response.status_code == 403:
#             response.data['message'] = "Access denied"
#
#         elif response.status_code == 405:
#             response.data['message'] = 'Request method error'
#     return response


# 自定义Response返回，把原来返回的data放到下一层即data.data，然后在data中添加code，message等,目前还没有用到
class MyResponse(Response):
    """
    An HttpResponse that allows its data to be rendered into
    arbitrary media types.
    """

    def __init__(self, data=None, code=None, msg=None,
                 status=None,
                 template_name=None, headers=None,
                 exception=False, content_type=None):
        """
        Alters the init arguments slightly.
        For example, drop 'template_name', and instead use 'data'.
        Setting 'renderer' and 'media_type' will typically be deferred,
        For example being set automatically by the `APIView`.
        """
        super(Response, self).__init__(None, status=status)

        if isinstance(data, Serializer):
            msg = (
                'You passed a Serializer instance as data, but '
                'probably meant to pass serialized `.data` or '
                '`.error`. representation.'
            )
            raise AssertionError(msg)

        self.data = {"code": code, "message": msg, "data": data}
        self.template_name = template_name
        self.exception = exception
        self.content_type = content_type

        if headers:
            for name, value in six.iteritems(headers):
                self[name] = value


# 封装分页代码，第一个参数要request是因为里头代码要request.GET东西需要有request支持
def getPage(request, data_list, page_num=10):
    # 传2参数，一个是要分页的列表或者queryset，一个是每页显示数量默认10
    paginator = Paginator(data_list, page_num)  # import引入的django自带分页模块Paginator，data_list是数据库查询后的queryset，每页10条记录
    try:
        page = int(request.GET.get('page', 1))  # 从页面上的?page获取值，看html里分页设置了这个值,如果没有就赋值1，第一页
        data_list = paginator.page(page)
    except Exception:
        data_list = paginator.page(1)
    return data_list


# 分页代码
class StandardPagination(PageNumberPagination):
    # 每页显示个数
    page_size = 1
    # url中默认修改每页个数的参数名
    # 比如http://127.0.0.1:8000/api/snippets/?page=1&page_size=4
    # 就是显示第一页并且显示个数是4个
    # page_size的变量名称默认如下
    page_size_query_param = 'page_size'
    # url中默认是参数名是page下面还是改成page哈
    page_query_param = "page"
    # 每页最大个数不超过100
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        """
        获取分页内容
        """
        page_size = self.get_page_size(request)
        if not page_size:
            return None

        paginator = self.django_paginator_class(queryset, page_size)
        page_number = request.query_params.get(self.page_query_param, 1)
        if page_number in self.last_page_strings:
            page_number = paginator.num_pages
        # 重定义错误，默认如果页数page超过分页大小会报错，这里改成超过的话页数变成第一页
        # page_number是传递进来要展示第几页的页数
        try:
            self.page = paginator.page(page_number)
        except Exception as e:
            self.page = paginator.page(1)

        if paginator.num_pages > 1 and self.template is not None:
            # The browsable API should display pagination controls.
            self.display_page_controls = True

        self.request = request
        return list(self.page)

    def get_paginated_response(self, data):
        """
        设置返回内容格式
        """
        return Response({
            'results': data,
            'count': self.page.paginator.count,
            'page_size': self.page.paginator.per_page,
            'page': self.page.start_index(),
            'next': self.get_next_link(),
            'previous': self.get_previous_link()
        })
