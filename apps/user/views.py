from django.shortcuts import render,HttpResponse,redirect
from django.urls import reverse
from django.views.generic import View
from django.conf import settings
from django.contrib.auth import authenticate,login,logout
from utils.mixin import LoginRequireView
from celery_tasks.tasks import send_register_active_email
from user.models import User,Address

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
import re
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

        #校验数据
        if not all([username,password]):
            return render(request,'login.html',{'error_msg','数据不完整'})

        #登录校验
        user = authenticate(username=username, password=password)
        if user is not None:
            #用户名密码正确,且激活

            #记录用户登陆状态
            login(request,user)

            # 获取登录后所要跳转到的地址
            # 默认跳转到首页
            next_url = request.GET.get('next',reverse('goods:index'))


            #跳转首页
            response = redirect(next_url)

            #判断是否需要记住用户名
            remember = request.POST.get('remember')

            if remember == 'on':
                #记住用户名一小时内
                response.set_cookie('username',username,max_age=120)
            else:
                response.delete_cookie('username')
            return response
        else:
            #用户未激活或者用户名密码错误
            user = User.objects.filter(username = username).first()
            if user is not None:
                #用户已注册

                #校验密码
                is_pwd_correct = user.check_password(password)
                if not is_pwd_correct:
                    #密码不正确
                    return render(request,'login.html',{'error_msg':'密码错误'})
                else:
                    #密码正确，说明用户未激活
                    return render(request,'login.html',{'error_msg':'用户未激活'})
            else:
                #用户不存在
                return render(request,'login.html',{'error_msg':'用户不存在'})

class LogoutView(View):
    '''注销'''
    def get(self,request):
        '''退出登录'''
        #清楚用户session
        logout(request)

        #跳转到登录页面
        return redirect(reverse('goods:index'))

#/user
class UserInfoView(LoginRequireView,View):
    '''用户中心-信息'''
    def get(self,request):
        '''显示'''
        #django会给每一个request添加request.user属性（通过session和middleware来实现）
        # 如果用户未登录->user是AnonymousUser类的一个实例对象
        # 如果用户登录->user是User类的一个实例对象
        # request.user.is_authenticated()
        #获取默认地址
        user = request.user
        try:
            default_addr = Address.objects.get(user=user,is_default=True)
        except Address.DoesNotExist:
            default_addr = None

        return render(request,'user_center_info.html',{'page':'address','default_addr':default_addr})

#/user/order
class UserOrderView(LoginRequireView,View):
    '''用户中心-订单'''
    def get(self,request):
        '''显示'''
        return render(request,'user_center_order.html',{'page':'order'})

#/user/address
class UserAddressView(LoginRequireView,View):
    '''用户中心-地址'''
    def get(self,request):
        '''显示'''
        #获取默认地址
        user = request.user
        try:
            default_addr = Address.objects.get(user=user,is_default=True)
        except Address.DoesNotExist:
            default_addr = None

        return render(request,'user_center_site.html',{'page':'address','default_addr':default_addr})

    def post(self,request):
        '''添加地址'''

        #获取数据
        receiver = request.POST.get('recv')
        address = request.POST.get('address')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')

        #数据校验
        if not all([receiver,address,phone]):
            return render(receiver,'user_center_site.html',{'error_msg':'数据不完整'})

        #电话校验
        if not re.match(r'^1[3|4|5|7|8][0-9]{9}',phone):
            return render(receiver,'user_center_site.html',{'error_msg':'手机格式错误'})

        #业务处理：地址添加
        #如果该用户存在默认地址，则添加地址不作为默认，否则添加为默认地址
        user = request.user

        try:
            default_addr = Address.objects.get(user=user,is_default=True)
        except Address.DoesNotExist:
            default_addr = None

        is_default = False if default_addr else True

        Address.objects.create(user=user,
                               recv=receiver,
                               addr=address,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default
                               )
        return redirect(reverse('user:address'))