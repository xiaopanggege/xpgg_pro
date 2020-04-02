from django.urls import path, re_path, include
from django.conf.urls import url
from rest_framework.routers import DefaultRouter
from xpgg_oms.views import user, saltstack, release, menus, periodic_task, dashboard
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework.documentation import include_docs_urls
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
   openapi.Info(
      title="XPGG API",
      default_version='v1',
      description="XPGG API文档查看",
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

router = DefaultRouter()
# 通过router注册方式配置路由，快准狠,新版base_name改为basename好像
router.register(r'dashboard', dashboard.DashboardViewSet, basename='dashboard')
router.register(r'userinfo', user.MyUserViewSet, basename='userinfo')
router.register(r'saltstack/salt-key', saltstack.SaltKeyViewSet, basename='salt-key')
router.register(r'saltstack/salt-key-opt/accept', saltstack.SaltKeyAcceptViewSet, basename='salt-key-accept')
router.register(r'saltstack/salt-key-opt/delete', saltstack.SaltKeyDeleteViewSet, basename='salt-key-delete')
router.register(r'saltstack/salt-key-opt/reject', saltstack.SaltKeyRejectViewSet, basename='salt-key-reject')
router.register(r'saltstack/salt-key-opt/del-denied', saltstack.SaltKeyDeleteDeniedViewSet, basename='salt-key-del-denied')
router.register(r'saltstack/salt-minion', saltstack.SaltMinionViewSet, basename='salt-minion')
router.register(r'saltstack/salt-minion-opt/status-update', saltstack.SaltMinionStateUpdateViewSet, basename='salt-minion-status-upate')
router.register(r'saltstack/salt-minion-opt/update', saltstack.SaltMinionUpdateViewSet, basename='salt-minion-update')
router.register(r'saltstack/salt-cmd', saltstack.SaltCmdViewSet, basename='salt-cmd')
router.register(r'saltstack/salt-cmd-opt/delete', saltstack.SaltCmdDeleteViewSet, basename='salt-cmd-delete')
router.register(r'saltstack/salt-cmd-opt/get-module', saltstack.SaltCmdModuleListViewSet, basename='salt-cmd-get-module')
router.register(r'saltstack/salt-cmd-opt/get-cmd', saltstack.SaltCmdCmdleListViewSet, basename='salt-cmd-get-cmd')
router.register(r'saltstack/salt-exe', saltstack.SaltExeViewSet, basename='salt-exe')
router.register(r'saltstack/salt-tool/job-search/status', saltstack.SaltToolJobStatusViewSet, basename='salt-tool-job-search-status')
router.register(r'saltstack/salt-tool/job-search/result', saltstack.SaltToolJobResultViewSet, basename='salt-tool-job-search-result')
router.register(r'saltstack/file-manage/file-tree', saltstack.FileTreeViewSet, basename='salt-file-tree')
router.register(r'saltstack/file-manage/file-content', saltstack.FileContentViewSet, basename='salt-file-content')
router.register(r'saltstack/file-manage/file-update', saltstack.FileUpdateViewSet, basename='salt-file-update')
router.register(r'saltstack/file-manage/file-create', saltstack.FileCreateViewSet, basename='salt-file-create')
router.register(r'saltstack/file-manage/file-rename', saltstack.FileRenameViewSet, basename='salt-file-rename')
router.register(r'saltstack/file-manage/file-delete', saltstack.FileDeleteViewSet, basename='salt-file-delete')
router.register(r'saltstack/file-manage/file-upload', saltstack.FileUploadViewSet, basename='salt-file-upload')
router.register(r'release/release-base', release.ReleaseModelViewSet, basename='release-base')
router.register(r'release/release-opt', release.ReleaseOperationViewSet, basename='release-opt')
router.register(r'release/release-del', release.ReleaseDeleteViewSet, basename='release-del')
router.register(r'release/release-log', release.ReleaseLogViewSet, basename='release-log')
router.register(r'release-group', release.RealseaGroupViewSet, basename='release-group')
router.register(r'release-member', release.ReleaseGroupMemberModelViewSet, basename='release-member')
router.register(r'release-auth', release.RealseaAuthViewSet, basename='release-auth')
router.register(r'roles', menus.RolesModelViewSet, basename='roles')
router.register(r'periodic_task/clocked-schedule', periodic_task.ClockedScheduleModelViewSet, basename='clocked-schedule')
router.register(r'periodic_task/clocked-list', periodic_task.ClockedListModelViewSet, basename='clocked-list')
router.register(r'periodic_task/crontab-schedule', periodic_task.CrontabScheduleModelViewSet, basename='crontab-schedule')
router.register(r'periodic_task/crontab-list', periodic_task.CrontabListModelViewSet, basename='crontab-list')
router.register(r'periodic_task/interval-schedule', periodic_task.IntervalScheduleModelViewSet, basename='interval-schedule')
router.register(r'periodic_task/interval-list', periodic_task.IntervalListModelViewSet, basename='interval-list')
router.register(r'periodic_task/periodic-task', periodic_task.PeriodicTaskModelViewSet, basename='periodic-task')
router.register(r'periodic_task/run-task', periodic_task.RunTaskModelViewSet, basename='run-task')
router.register(r'periodic_task/task-log', periodic_task.TaskResultScheduleModelViewSet, basename='task-log')


urlpatterns = [
    # 新的swagger第三方url配置：第一个不知道为什么会报错，我也没用到所以没去研究
    # url(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    url(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    url(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    # drf登录认证页面
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^login/$', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    url(r'^api/token/refresh/$', TokenRefreshView.as_view(), name='token_refresh'),

    # 把router注册的路由添加到django的url中，如果有APIView的路由表则使用追加的方式如西面的urlpatterns += router.urls
    # url(r'', include(router.urls)),

    #  APIView的路由表
    url(r'^users/$', menus.UserList.as_view()),
    url(r'^routes/$', menus.RoutesModel.as_view()),
]


urlpatterns = format_suffix_patterns(urlpatterns)
urlpatterns += router.urls
