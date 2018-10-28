from django.urls import path
from apps.goods.views import IndexView

app_name = 'goods'
urlpatterns = [
    path(r'',IndexView.as_view(), name='index') #首页
]
