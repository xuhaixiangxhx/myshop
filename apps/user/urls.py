
from django.urls import path,re_path
from apps.user import views
from apps.user.views import RegisterView,ActiveView,LoginView

app_name = 'user'
urlpatterns = [
    # path(r'register', views.register, name = 'register'),   #注册
    # path('login', views.login, name = 'login'), #登录
    path(r'register', RegisterView.as_view(),name='register'),  #注册
    re_path(r'active/(?P<token>.*)',ActiveView.as_view(),name='active'),   #激活
    path(r'login',LoginView.as_view(),name='login') #登录
]
