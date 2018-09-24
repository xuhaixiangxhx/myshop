
from django.urls import path
from apps.user import views

app_name = 'user'
urlpatterns = [
    path(r'register', views.register, name = 'register'),   #注册
    path('login', views.login, name = 'login'),
]
