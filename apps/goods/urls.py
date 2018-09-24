from django.urls import path
from apps.goods import views

app_name = 'goods'
urlpatterns = [
    path(r'',views.index, name='index')
]
