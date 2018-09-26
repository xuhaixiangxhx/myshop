from django.shortcuts import render,HttpResponse,redirect
from django.urls import reverse
from django.views.generic import View
from django.conf import settings
from django.contrib.auth import authenticate,login
from celery_tasks.tasks import send_register_active_email
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
        serializer = Serializer(settings.SECRET_KEY,expires_in=600)
        token = serializer.dumps({'id':user.id}).decode()
        #邮件发送
        send_register_active_email.delay(email,username,token)

        return redirect(reverse('goods:index'))

class ActiveView(View):
    '''用户激活'''
    def get(self,request,token):
        '''进行用户激活'''
        #解密，获取要激活的用户信息
        serializer = Serializer(settings.SECRET_KEY,expires_in=600)
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
        #判断是否记住用户名
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked ='checked'
        else:
            username = ''
            checked = ''
        return render(request,'login.html',{'username':username,'checked':checked})

    def post(self,request):
        '''登录校验'''
        #接受数据
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        print(username,password)

        #校验数据
        if not all([username,password]):
            return render(request,'login.html',{'error_msg','数据不完整'})

        #登录校验
        user = authenticate(username,password)
        if user is not None:
            #用户名密码正确
            if user.is_active:
                #用户已激活
                login(request,user)

                #跳转首页
                response = redirect(reverse('goods:index'))

                #判断是否需要记住用户名
                remember = request.POST.get('rem')
                print(remember)
                if remember == 'on':
                    #记住用户名一小时内
                    response.set_cookie('username',username,max_age=3600)
                else:
                    response.delete_cookie()

                return response
            else:
                #用户未激活
                return render(request,'login.html',{'error_msg','用户未激活'})

