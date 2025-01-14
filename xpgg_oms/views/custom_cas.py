from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _
from rest_framework_simplejwt.state import User
from xpgg_oms.models import MyUser
from rest_framework import serializers
from django.utils.six import text_type
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
# 下面是自定义cas的登录视图使用到的
from django_cas_ng.views import LoginView
from django.http import JsonResponse



import logging
logger = logging.getLogger('xpgg_oms.views')


# 下面是继承jwt的重写一套sso单点登录的认证过程，其实就是取消了密码。。。目前已经没有使用了留着做个重写jwt认证的参考
class SsoTokenObtainSerializer(serializers.Serializer):
    username_field = User.USERNAME_FIELD

    def __init__(self, *args, **kwargs):
        super(SsoTokenObtainSerializer, self).__init__(*args, **kwargs)

        self.fields[self.username_field] = serializers.CharField()
        # sso登陆进来就只传了个用户过来奶奶的，所以取消密码
        # self.fields['password'] = PasswordField()


    def validate(self, attrs):
        # 默认验证用户密码这里不能用了，注释重写
        # self.user = authenticate(**{
        #     self.username_field: attrs[self.username_field],
        #     'password': attrs['password'],
        # })

        # 直接同步用户，并且带上邮箱
        result = MyUser.objects.get_or_create(username=attrs[self.username_field],defaults={'email':attrs[self.username_field] + '@ruijie.com.cn'})
        self.user = result[0]
        # 如果用户不存在，或者用户离职即disabled为True就报错不让登陆
        if self.user is None or not self.user.is_active:
            raise serializers.ValidationError(
                _('No active account found with the given credentials'),
            )
        return {}

    @classmethod
    def get_token(cls, user):
        raise NotImplemented('Must implement `get_token` method for `TokenObtainSerializer` subclasses')

class SsoTokenObtainPairSerializer(SsoTokenObtainSerializer):
    @classmethod
    def get_token(cls, user):
        return RefreshToken.for_user(user)

    def validate(self, attrs):
        data = super(SsoTokenObtainPairSerializer, self).validate(attrs)
        refresh = self.get_token(self.user)

        data['refresh'] = text_type(refresh)
        data['access'] = text_type(refresh.access_token)
        return data

class SsoTokenObtainPairView(TokenObtainPairView):
    """
    Takes a set of user credentials and returns an access and refresh JSON web
    token pair to prove the authentication of those credentials.
    """
    serializer_class = SsoTokenObtainPairSerializer


sso_token_obtain_pair = SsoTokenObtainPairView.as_view()


# 下面是正规的cas视图因为返回要集成jwt的token所以重写
class CustomLoginView(LoginView):
    def successful_login(self, request, next_page):
        # 调用父类的成功登录逻辑
        super().successful_login(request, next_page)

        # 使用 djangorestframework_simplejwt 生成 JWT
        refresh = RefreshToken.for_user(request.user)
        # 返回 JWT，使用 Response 返回
        return JsonResponse({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'username': str(request.user),
            'next_page': next_page
        })


