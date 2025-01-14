# 全局公共设置，这里本来放在xpgg_oms.views.utils里，但是不行放上面一层就可以了，奶奶的
from rest_framework import  permissions
from xpgg_oms.models import ViewApi
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
# from rest_framework.views import exception_handler
import logging
logger = logging.getLogger('xpgg_oms.views')

# 自定义权限，用于全局settings里
class MyPermission(permissions.BasePermission):
    # 如果用户访问量巨大的可以考虑第一次获取权限后存redis，下面代码改造成去redis判断而不是从mysql里，不过现在就没几个人
    # 那就直接去mysql里面查询权限
    def has_permission(self, request, view):
        if bool(request.user and request.user.is_authenticated):
            # 超级管理员直接true，其他用户通过view和method来判断，这两个是在进行判断之前可以获取到的，所以api表是也是按这个来设计
            if request.user.is_superuser:
                return True
            else:
                # 模块拼接类名作为api表的视图名称字段值
                view_name = view.__module__ + '.' + view.__class__.__name__
                request_method = request.method.lower()
                user_roles = set(request.user.roles_set.values_list('name', flat=True))
                try:
                    # 这里面判断api的角色是从request.method中无法获取到类型，其中get方法有一点特殊，因为get代表获取列表也可以代表获取单个对象
                    # ，这个在swagger的页面可以看到，本来要再加一个action字段来判断，后面想想这样应该已经够控制住权限了
                    # 这里使用get方法有错误，如果没有获取到值，会报错的，后面看看是改成filter还是怎么弄，目前做到这里
                    api_data = ViewApi.objects.filter(view_name=view_name, method=request_method)
                    # 判断是否默认允许访问
                    if api_data.default_allow:
                        return True
                    roles_set = set(api_data.roles.values_list('name', flat=True))
                    # 用集合做交集对比确认权限
                    if user_roles & roles_set:
                        return True
                    else:
                        return False
                except Exception as e:
                    print(str(e))
                    return False
        else:
            return False
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return True

# 分页代码 用于全局settings里
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

    # 自定义数据,
    msg = None

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
            'previous': self.get_previous_link(),
            'msg': self.msg
        })

