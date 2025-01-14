# 公用全局方法
from django.contrib.auth import authenticate
from rest_framework.views import exception_handler
from rest_framework.response import Response
from django.utils import six
from rest_framework.serializers import Serializer
from django.utils.six import text_type
from rest_framework import serializers
from rest_framework_simplejwt.state import User
from django.utils.translation import ugettext_lazy as _
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import PasswordField
from rest_framework_simplejwt.views import TokenObtainPairView

# 邮件发送相关
from email.header import Header
from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr
import smtplib
from smtplib import SMTP_SSL

import logging
logger = logging.getLogger('xpgg_oms.views')

# 这个特么都有坑，自义定异常这个不能和其他settings的自定义放一起，放一起其他的都用不了，
# 所以我只能在上面一层再弄一个utils存settings里的自定义
# 自定义rest framework的异常捕获返回,在settings里调用
def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # 注意当response为None时候将会重新触发django的标准500异常,
    if response is not None:
        response.data['status_code'] = response.status_code
        # 把所有错误码改成200返回，然后在返回的data里添加status_code中指定返回码,注意这个自定义方法只有在发生异常时才会被调用
        # 为了规范response.data里的字段，我统一规定code为返回码，msg为额外需要的返回信息
        response.status_code = 200

        # 返回信息统一到msg字段,有时候没有detail有时候未知字段是non_field_errors，具体有没有其他情况后面再看看
        if 'detail' in response.data:
            response.data['msg'] = response.data['detail']
            del response.data['detail']
        elif 'non_field_errors' in response.data:
            response.data['msg'] = response.data['non_field_errors']
            del response.data['non_field_errors']
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


# 以下3个是用来自定义jwt错误返回，默认不会返回到底是用户名错误还是密码错误奶奶的，目前没有使用
# 这个可以修改验证错误返回内容等
class MyTokenObtainSerializer(serializers.Serializer):
    username_field = User.USERNAME_FIELD

    def __init__(self, *args, **kwargs):
        super(MyTokenObtainSerializer, self).__init__(*args, **kwargs)

        self.fields[self.username_field] = serializers.CharField()
        self.fields['password'] = PasswordField()

    def validate(self, attrs):
        # 这里改验证方法和返回错误的内容
        self.user = authenticate(**{
            self.username_field: attrs[self.username_field],
            'password': attrs['password'],
        })

        # Prior to Django 1.10, inactive users could be authenticated with the
        # default `ModelBackend`.  As of Django 1.10, the `ModelBackend`
        # prevents inactive users from authenticating.  App designers can still
        # allow inactive users to authenticate by opting for the new
        # `AllowAllUsersModelBackend`.  However, we explicitly prevent inactive
        # users from authenticating to enforce a reasonable policy and provide
        # sensible backwards compatibility with older Django versions.
        if self.user is None or not self.user.is_active:
            raise serializers.ValidationError(
                _('No active account found with the given credentials'),
            )

        return {}

    @classmethod
    def get_token(cls, user):
        raise NotImplemented('Must implement `get_token` method for `TokenObtainSerializer` subclasses')


# 这个可以修改验证成功后返回的内容，官网有例子
class MyTokenObtainPairSerializer(MyTokenObtainSerializer):
    # token内容在这里改
    @classmethod
    def get_token(cls, user):
        return RefreshToken.for_user(user)

    def validate(self, attrs):
        data = super(MyTokenObtainSerializer, self).validate(attrs)

        refresh = self.get_token(self.user)

        data['refresh'] = text_type(refresh)
        data['access'] = text_type(refresh.access_token)

        return data


# 这个是最外层应用jwt的认证做登录，应用在urls.py里的login路由上
class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


# 自定义Response
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

        self.data = {"code": code, "msg": msg, "data": data}
        self.template_name = template_name
        self.exception = exception
        self.content_type = content_type

        if headers:
            for name, value in six.iteritems(headers):
                self[name] = value


# salt执行state.sls的返回结果格式化，因为通过api返回的结果不怎么好看呵呵
def format_state(result):
    a = result['results']
    # b是返回minion列表
    b = (a['return'])
    # 用来存放所有minion格式化后的结果的
    result_data = []
    # 发现在3000版本api执行sls返回的数据格式变成了{'return': [{'outputter': 'highstate', 'data': {xxxxx}}]}
    # 而之前版本是{'return': [{xxxxx}]}，这个xxxxx就是各个以minion的id为key的结果如下
    # {'192.168.0.118-master': {"cmd_|-rsync_dir_|-rsync -rvtD --exclude '.svn' --exclude .....}
    # 所以需要添加下面的判断来来改变返回数据的结构
    if b[0].get('outputter') and b[0].get('outputter') == 'highstate':
        b = [b[0]['data']]
    try:
        # i是return后面的列表其实就是a['return'][0]
        for i in b:
            # key是minion的ID,value是这个ID执行的所有结果又是一个字典
            for key, value in i.items():
                succeeded = 0
                failed = 0
                changed = 0
                Total_states_run = 0
                Total_run_time = 0
                minion_id = key
                run_num = len(value)  # 得到执行的state个数
                result_list = [k for k in range(run_num)] #把列表先用数字撑大，因为接收的数据随机的顺序如（3,5,6），先撑开列表到时候假设是3过来就插3的位子这样顺序就有序了
                for key1, value1 in value.items():
                    # print(value1)
                    # key1是一个个state的ID，value1是每个state的结果
                    key1 = key1.split('_|-')
                    Function = key1[0] + '_' + key1[-1]
                    ID = key1[1]
                    Name = key1[2]
                    aaa = '----------\n' + 'ID: '.rjust(14) + ID + '\n' + 'Function: '.rjust(
                        14) + Function + '\n' + 'Name: '.rjust(14) + Name + '\n' + 'Result: '.rjust(14) + str(
                        value1['result']) + '\n' + 'Comment: '.rjust(14) + value1['comment'] + '\n'
                    # start_time有的没有有的有
                    if value1.get('start_time'):
                        aaa += 'Started: '.rjust(14) + str(value1['start_time']) + '\n'
                    # duration有的没有有的有
                    if value1.get('duration'):
                        aaa += 'Duration: '.rjust(14) + str(value1['duration']) + ' ms' + '\n'
                        Total_run_time += value1['duration']
                    # changes都有，就算没值也是一个空的{}
                    if value1['changes'] == {}:
                        aaa += 'Changes: '.rjust(14)+'\n'
                    elif type(value1['changes']) == str:
                        aaa += 'ChangesIs: '.rjust(14) + '\n' + ''.rjust(14) + '----------\n'
                        aaa += ''.rjust(14) + value1['changes'] + ':\n' + ''.rjust(18) + '----------\n'
                    else:
                        aaa += 'ChangesIs: '.rjust(14) + '\n' + ''.rjust(14) + '----------\n'
                        for key in value1['changes'].keys():

                            if type(value1['changes'][key]) == dict:
                                aaa += ''.rjust(14) + key + ':\n' + ''.rjust(18) + '----------\n'
                                for ckey, cvalue in value1['changes'][key].items():
                                    aaa += ''.rjust(18) + ckey + ':\n' + ''.rjust(22) + str(cvalue).replace('\n','\n'+' '*18) + '\n'
                            else:
                                aaa += ''.rjust(14) + key + ':\n' + ''.rjust(18) + str(value1['changes'][key]).replace('\n','\n'+' '*18) + '\n'
                        changed += 1
                    if value1.get('__run_num__') is None:
                        result_list.append(aaa)
                    else:
                        result_list[value1.get('__run_num__')] = aaa
                    if value1['result']:
                        succeeded += 1
                    else:
                        failed += 1
                    Total_states_run += 1
                Total_run_time = Total_run_time / 1000
                bbb =74*'-'+ '\nSummary for %s\n-------------\nSucceeded: %d (changed=%d)\nFailed:    %2d\n-------------\nTotal states run:     %d\nTotal run time:    %.3f s\n\n' % (
                minion_id, succeeded, changed, failed, Total_states_run, Total_run_time)
                result_list.insert(0, bbb)
                result_data.extend(result_list)
        return result_data
    #如果格式化有问题，就把原来的以str来返回，然后在调用这个格式化的方法里写判断如果为str说明格式化失败，然后该怎么处理就怎么处理呵呵
    except Exception as e:
        logger.error('格式化不成功'+str(e))
        return str(a)

# 公共类 邮件发送方法
class MailSend:
    def __init__(self,data):
        self.email = data.get('email')
        self.password = data.get('password')
        self.smtp_addr = data.get('smtp_addr')
        self.smtp_port = data.get('smtp_port')
        self.security = data.get('security')
        self.email_name = data.get('email_name', '运维平台邮件助手')
        self.tmail_name = data.get('tmail_name')
        self.header = data.get('header', '运维平台来信')
        self.tmail_name = data.get('tmail_name')
        self.content = data.get('content', '<h3>这是一封来自运维平台的测试邮件</h3>')

    def _format_addr(self,s):
        name, addr = parseaddr(s)
        return formataddr((Header(name, 'utf-8').encode(), addr))

    def send_mail(self):
        from_addr = self.email
        password = self.password
        to_addr = self.tmail_name
        smtp_server = self.smtp_addr

        msg = MIMEText(self.content, 'html', 'utf-8')
        msg['From'] = self._format_addr('%s <%s>' % (self.email_name,from_addr))
        msg['To'] = ','.join(to_addr)  # 用join让每个邮箱分开，不支持列表所以要这样
        msg['Subject'] = Header('%s' % self.header, 'utf-8').encode()

        try:
            if 'ssl' in self.security:
                server = SMTP_SSL(smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(smtp_server, self.smtp_port)
                if 'tls' in self.security:
                    server.starttls()
            # 登陆
            server.login(from_addr, password)
            # 发送
            server.sendmail(from_addr, to_addr, msg.as_string())
            # print('发送成功')
            server.quit()  # 断开和邮件服务器的连接
            return '发送成功'
        except Exception as e:
            # print('发送失败:', e)
            return '发送失败' + str(e)





