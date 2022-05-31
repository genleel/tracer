import datetime
import uuid
from io import BytesIO

from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect

from utils.image_code import check_code
from web import models
from web.forms.account import RegisterModelForm, SendSmsForm, LoginSMSForm, LoginForm


def register(request):
    """注册"""
    if request.method == "GET":
        form = RegisterModelForm()
        return render(request, 'register.html', {'form': form})

    form = RegisterModelForm(data=request.POST)
    if form.is_valid():
        instance = form.save()

        # 初始化交易记录
        policy_object = models.PricePolicy.objects.filter(category=1, title='个人免费版').first()
        print(policy_object)
        models.Transaction.objects.create(
            status=2,
            order=str(uuid.uuid4()),  # 随机字符串
            user=instance,
            price_policy_id=policy_object.id,
            count=0,
            price=0,
            start_datetime=datetime.datetime.now()
        )
        return JsonResponse({'status': True, 'data': '/login/'})

    return JsonResponse({'status': False, 'error': form.errors})


def send_sms(request):
    """发送短信"""

    form = SendSmsForm(request, data=request.GET)
    # 校验手机号不能为空/格式是否正确
    if form.is_valid():
        return JsonResponse({'status': True})

    return JsonResponse({'status': False, 'error': form.errors})


def login_sms(request):
    """短信登录"""
    if request.method == 'GET':
        form = LoginSMSForm()
        return render(request, 'login_sms.html', {'form': form})

    form = LoginSMSForm(request.POST)
    if form.is_valid():
        user = form.cleaned_data['mobile_phone']
        # 用户信息存入session
        request.session['user_id'] = user.id
        request.session.set_expiry(60 * 60 * 24 * 14)
        return JsonResponse({'status': True, 'data': "/index/"})

    return JsonResponse({'status': False, 'error': form.errors})


def login(request):
    """用户名密码登录"""
    if request.method == 'GET':
        form = LoginForm(request)
        return render(request, 'login.html', {'form': form})
    form = LoginForm(request, data=request.POST)
    if form.is_valid():
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        # user = models.UserInfo.objects.filter(username=username, password=password).first()

        # 邮箱或手机号登录
        user = models.UserInfo.objects.filter(Q(email=username) | Q(mobile_phone=username)).filter(
            password=password).first()

        if user:
            # 用户名密码正确
            request.session['user_id'] = user.id
            request.session.set_expiry(60 * 60 * 24 * 14)
            return redirect('index')
        form.add_error('username', '用户名或密码错误')
    return render(request, 'login.html', {'form': form})


def image_code(request):
    """生成图片验证码"""

    image_object, code = check_code()
    request.session['image_code'] = code
    request.session.set_expiry(60)

    # 把图片写入内存
    stream = BytesIO()
    image_object.save(stream, 'png')

    return HttpResponse(stream.getvalue())


def logout(request):
    # 清空session中的数据
    request.session.flush()
    return redirect('index')
