from django.shortcuts import render,HttpResponse,redirect
from django.urls import reverse
from user.models import User
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
    return render(request,'login.html')