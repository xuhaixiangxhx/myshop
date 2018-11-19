
from django.contrib import admin
from django.urls import path
from order.views import OrderPlaceView,OrderCommitView


app_name = 'order'
urlpatterns = [
    # path('admin/', admin.site.urls),
    path(r'place', OrderPlaceView.as_view(), name='place'),     #订单提交页面显示
    path(r'commit', OrderCommitView.as_view(), name='commit'),      #订单创建
]
