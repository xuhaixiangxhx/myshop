from django.shortcuts import render,HttpResponse,redirect
from django.urls import reverse
from django.views.generic import View
from django.conf import settings
from django.core.mail import send_mail
from user.models import User

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired

# Create your views here.

#/user/register
def register(request):
    '''注册'''
    if request.method == 'GET':
        '''显示注册页面'''
        return render(request,'register.html')
    if request.method == 'POST':
        '''接受数据，进行注册处理'''
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        if not all([username,password,email]):
            '''注册信息不全'''
            return render(request,'register.html',{'error_msg':'请提供完整信息'})

        if allow != 'on':
            return render(request,'register.html',{'error_msg':'请同意协议'})

        #校验用户名是否重复
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
        if user:
            return render(request,'register.html',{'error_msg':'用户名已存在'})
        #用户注册
        user = User.objects.create_user(username,email,password)
        user.is_active = 0
        user.save()
        return redirect(reverse('goods:index'))

def login(request):
    '''登录'''
    return render(request,'login.html')

class RegisterView(View):
    '''用户注册'''
    def get(self,request):
        '''显示注册页面'''
        return render(request,'register.html')

    def post(self,request):
        '''接受数据，进行注册处理'''
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        if not all([username,password,email]):
            '''注册信息不全'''
            return render(request,'register.html',{'error_msg':'请提供完整信息'})

        if allow != 'on':
            return render(request,'register.html',{'error_msg':'请同意协议'})

        #校验用户名是否重复
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
        if user:
            return render(request,'register.html',{'error_msg':'用户名已存在'})
        #用户注册
        user = User.objects.create_user(username,email,password)
        user.is_active = 0
        user.save()

        #发送激活邮件,包含激活链接 http://127.0.0.1:8000/user/active/1
        #激活链接需包含用户的身份信息

        #加密用户的身份信息，生成token
        serializer = Serializer(settings.SECRET_KEY,expires_in=10)
        token = serializer.dumps({'id':user.id}).decode()
        print(token)
        #邮件发送
        subject = 'welcome to myshop'
        message = ''
        sender = settings.EMAIL_FROM
        recive_list = [email]
        html_msg = '%s,欢迎注册myshop会员!请点击如下链接激活您的账户：<a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>'%(username,token,token)
        send_mail(subject,message,sender,recive_list,html_message=html_msg)
        return redirect(reverse('goods:index'))

class ActiveView(View):
    '''用户激活'''
    def get(self,request,token):
        '''进行用户激活'''
        #解密，获取要激活的用户信息
        serializer = Serializer(settings.SECRET_KEY,expires_in=10)
        try:
            user_info = serializer.loads(token)
            #获取用户id
            user_id = user_info['id']
            #根据id激活用户
            user = User.objects.get(id = user_id)
            user.is_active = 1
            user.save()
            return redirect(reverse('user:login'))
        except SignatureExpired as e:
            return HttpResponse('链接已失效')

class LoginView(View):
    '''登录'''
    def get(self,request):
        '''登录页面'''
        return render(request,'login.html')
