
from django.contrib import admin
from django.urls import path, re_path
from order.views import OrderPlaceView,OrderCommitView,OrderPayView,OrderCheckView,OrderCommentkView


app_name = 'order'
urlpatterns = [
    # path('admin/', admin.site.urls),
    path(r'place', OrderPlaceView.as_view(), name='place'),     #订单提交页面显示
    path(r'commit', OrderCommitView.as_view(), name='commit'),      #订单创建
    path(r'pay', OrderPayView.as_view(), name='pay'),      #订单支付
    path(r'check', OrderCheckView.as_view(), name='check'),      #订单支付结果查询
    re_path(r'comment/(?P<order_id>\d+)', OrderCommentkView.as_view(), name='comment'),      #订单商品评论查询
]
