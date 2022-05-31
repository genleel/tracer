import random

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django_redis import get_redis_connection

from utils import encrypt
from web import models
from web.forms.bootstrap import BootstrapForm


class RegisterModelForm(BootstrapForm, forms.ModelForm):
    mobile_phone = forms.CharField(label='手机号', validators=[RegexValidator(r'^(1[3|4|5|6|7|8|9])\d{9}$', '手机号格式错误。'), ])

    password = forms.CharField(
        label='密码',
        min_length=8,
        max_length=64,
        error_messages={
            'min_length': '密码长度不能小于8个字符。',
            'max_length': '密码长度不能大于64个字符。'
        },
        widget=forms.PasswordInput())

    confirm_password = forms.CharField(
        label='重复密码',
        min_length=8,
        max_length=64,
        error_messages={
            'min_length': '重复密码长度不能小于8个字符。',
            'max_length': '重复密码长度不能大于64个字符。'
        },
        widget=forms.PasswordInput())

    code = forms.CharField(
        label='验证码',
        widget=forms.TextInput())

    class Meta:
        model = models.UserInfo
        fields = ['username', 'email', 'password', 'confirm_password', 'mobile_phone', 'code']

    def clean_username(self):
        username = self.cleaned_data['username']

        exists = models.UserInfo.objects.filter(username=username).exists()
        if exists:
            raise ValidationError('用户名已存在。')

        return username

    def clean_email(self):
        email = self.cleaned_data['email']

        exists = models.UserInfo.objects.filter(email=email).exists()
        if exists:
            raise ValidationError('邮箱已存在。')

        return email

    def clean_password(self):
        pwd = self.cleaned_data['password']
        # 加密
        return encrypt.md5(pwd)

    def clean_confirm_password(self):
        pwd = self.cleaned_data.get('password')
        confirm_pwd = encrypt.md5(self.cleaned_data['confirm_password'])
        if pwd != confirm_pwd:
            raise ValidationError('两次密码不一致。')
        return confirm_pwd

    def clean_mobile_phone(self):
        mobile_phone = self.cleaned_data['mobile_phone']

        exists = models.UserInfo.objects.filter(mobile_phone=mobile_phone).exists()
        if exists:
            raise ValidationError('手机号已注册。')

        return mobile_phone

    def clean_code(self):
        code = self.cleaned_data['code']
        mobile_phone = self.cleaned_data.get('mobile_phone')

        conn = get_redis_connection()
        redis_code = conn.get(mobile_phone)
        if not redis_code:
            raise ValidationError('验证码失效或未发送，请重试。')

        redis_str_code = redis_code.decode('utf-8')

        if code.strip() != redis_str_code:
            raise ValidationError('验证码错误。')

        return code


class SendSmsForm(forms.Form):
    mobile_phone = forms.CharField(label='手机号', validators=[RegexValidator(r'^(1[3|4|5|6|7|8|9])\d{9}$', '手机号格式错误。'), ])

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request

    def clean_mobile_phone(self):
        """手机号校验"""
        mobile_phone = self.cleaned_data['mobile_phone']

        tpl = self.request.GET.get('tpl')
        template_id = settings.TENCENT_SMS_TEMPLATE.get(tpl)
        # 校验模板id
        if not template_id:
            raise ValidationError('短信模板错误。')

        # 校验数据库中是否有手机号
        exists = models.UserInfo.objects.filter(mobile_phone=mobile_phone).exists()
        if tpl == 'login':
            if not exists:
                raise ValidationError('手机号不存在。')

        if tpl == 'register':
            if exists:
                raise ValidationError('手机号已存在。')

        # 发短信
        code = random.randrange(10000, 99999)
        print('****** CODE: {} ******'.format(code))
        sms = {'result': 0}
        # sms = send_sms_single(mobile_phone, template_id, [code, ])
        if sms['result'] != 0:
            raise ValidationError('短信发送失败, {}。'.format(sms['errmsg']))

        # 写入redis
        conn = get_redis_connection()
        conn.set(mobile_phone, code, ex=60)

        return mobile_phone


class LoginSMSForm(BootstrapForm, forms.Form):
    mobile_phone = forms.CharField(label='手机号', validators=[RegexValidator(r'^(1[3|4|5|6|7|8|9])\d{9}$', '手机号格式错误。'), ])

    code = forms.CharField(
        label='验证码',
        widget=forms.TextInput())

    def clean_mobile_phone(self):
        mobile_phone = self.cleaned_data['mobile_phone']
        user = models.UserInfo.objects.filter(mobile_phone=mobile_phone).first()
        if not user:
            raise ValidationError('手机号不存在。')

        return user

    def clean_code(self):
        code = self.cleaned_data['code']
        user = self.cleaned_data.get('mobile_phone')
        # 手机号不存在无需校验
        if not user:
            return code

        conn = get_redis_connection()
        redis_code = conn.get(user.mobile_phone)
        if not redis_code:
            raise ValidationError('验证码失效或未发送，请重试。')

        redis_str_code = redis_code.decode('utf-8')

        if code.strip() != redis_str_code:
            raise ValidationError('验证码错误。')

        return code


class LoginForm(BootstrapForm, forms.Form):
    username = forms.CharField(
        label='邮箱或手机号',
        max_length=32,
        error_messages={
            'max_length': '用户名长度不能大于32个字符。'
    })

    password = forms.CharField(
        label='密码',
        min_length=8,
        max_length=64,
        error_messages={
            'min_length': '密码长度不能小于8个字符。',
            'max_length': '密码长度不能大于64个字符。'
        },
        widget=forms.PasswordInput())
    code = forms.CharField(label='图片验证码')

    def __init__(self, request, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        self.request = request

    def clean_code(self):
        """校验图片验证码"""
        code = self.cleaned_data['code']
        # 在session中获取image_code
        session_code = self.request.session.get('image_code')
        if not session_code:
            raise ValidationError('验证码已过期，请重新获取')

        if code.strip().upper() != session_code.strip().upper():
            raise ValidationError('验证码输入错误')

        return code

    def clean_password(self):
        pwd = self.cleaned_data['password']
        # 加密
        return encrypt.md5(pwd)

