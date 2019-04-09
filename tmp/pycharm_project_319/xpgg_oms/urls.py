from django.urls import path, re_path, include
from django.conf.urls import url
from rest_framework.routers import DefaultRouter
from xpgg_oms.views import user, saltstack
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework.schemas import get_schema_view
from rest_framework_swagger.renderers import SwaggerUIRenderer, OpenAPIRenderer
schema_view = get_schema_view(title='XPGG系统 API', renderer_classes=[OpenAPIRenderer, SwaggerUIRenderer])


router = DefaultRouter()
# 通过router注册方式配置路由，快准狠
router.register(r'userinfo', user.MyUserViewSet, base_name='userinfo')
router.register(r'saltstack/saltkey', saltstack.SaltKeyViewSet, base_name='saltkey')


urlpatterns = [
    url(r'^docs/', schema_view, name="docs"),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^login/$', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    url(r'^api/token/refresh/$', TokenRefreshView.as_view(), name='token_refresh'),
    url(r'^saltstack/testping$', saltstack.salt_test_ping, name='salt_test_ping'),
    url(r'^saltstack/salt_key_global/$', saltstack.salt_key_global, name='salt_key_global'),
    url(r'^saltstack/saltkey_manage/$', saltstack.saltkey_manage, name='saltkey_manage'),
    # 把router注册的路由添加到django的url中
    url(r'', include(router.urls)),
]
