from django.urls import path, re_path, include
from django.conf.urls import url
from rest_framework.routers import DefaultRouter
from xpgg_oms.views import user, saltstack, release
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
router.register(r'saltstack/salt-key', saltstack.SaltKeyViewSet, base_name='salt-key')
router.register(r'saltstack/salt-key-opt/accept', saltstack.SaltKeyAcceptViewSet, base_name='salt-key-accept')
router.register(r'saltstack/salt-key-opt/delete', saltstack.SaltKeyDeleteViewSet, base_name='salt-key-delete')
router.register(r'saltstack/salt-key-opt/reject', saltstack.SaltKeyRejectViewSet, base_name='salt-key-reject')
router.register(r'saltstack/salt-key-opt/del-denied', saltstack.SaltKeyDeleteDeniedViewSet, base_name='salt-key-del-denied')
router.register(r'saltstack/salt-minion', saltstack.SaltMinionViewSet, base_name='salt-minion')
router.register(r'saltstack/salt-minion-opt/status-update', saltstack.SaltMinionStateUpdateViewSet, base_name='salt-minion-status-upate')
router.register(r'saltstack/salt-minion-opt/update', saltstack.SaltMinionUpdateViewSet, base_name='salt-minion-update')
router.register(r'saltstack/salt-cmd', saltstack.SaltCmdViewSet, base_name='salt-cmd')
router.register(r'saltstack/salt-cmd-opt/delete', saltstack.SaltCmdDeleteViewSet, base_name='salt-cmd-delete')
router.register(r'saltstack/salt-cmd-opt/get-module', saltstack.SaltCmdModuleListViewSet, base_name='salt-cmd-get-module')
router.register(r'saltstack/salt-cmd-opt/get-cmd', saltstack.SaltCmdCmdleListViewSet, base_name='salt-cmd-get-cmd')
router.register(r'saltstack/salt-exe', saltstack.SaltExeViewSet, base_name='salt-exe')
router.register(r'saltstack/salt-tool/job-search/status', saltstack.SaltToolJobStatusViewSet, base_name='salt-tool-job-search-status')
router.register(r'saltstack/salt-tool/job-search/result', saltstack.SaltToolJobResultViewSet, base_name='salt-tool-job-search-result')
router.register(r'release/release-base', release.ReleaseModelViewSet, base_name='release-base')
router.register(r'release/release-opt', release.ReleaseOperationViewSet, base_name='release-opt')
router.register(r'release/release-del', release.ReleaseDeleteViewSet, base_name='release-del')


urlpatterns = [
    url(r'^docs/', schema_view, name="docs"),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^login/$', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    url(r'^api/token/refresh/$', TokenRefreshView.as_view(), name='token_refresh'),
    # 把router注册的路由添加到django的url中
    url(r'', include(router.urls)),
]
