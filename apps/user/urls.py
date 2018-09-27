
from django.urls import path,re_path
from django.contrib.auth.decorators import login_required
from apps.user.views import RegisterView,ActiveView,LoginView,UserInfoView,UserOrderView,UserAddressView

app_name = 'user'
urlpatterns = [
    # path(r'register', views.register, name = 'register'),   #注册
    # path('login', views.login, name = 'login'), #登录

    path(r'register', RegisterView.as_view(),name='register'),  #注册
    re_path(r'active/(?P<token>.*)',ActiveView.as_view(),name='active'),   #激活
    path(r'login',LoginView.as_view(),name='login'), #登录

    # path(r'',login_required(UserInfoView.as_view()),name='user'),    #用户中心-信息
    # path(r'order',login_required(UserOrderView.as_view()),name='order'),    #用户中心-订单
    # path(r'address',login_required(UserAddressView.as_view()),name='address'),    #用户中心-地址

    path(r'',UserInfoView.as_view(),name='user'),    #用户中心-信息
    path(r'order',UserOrderView.as_view(),name='order'),    #用户中心-订单
    path(r'address',UserAddressView.as_view(),name='address'),    #用户中心-地址
]
