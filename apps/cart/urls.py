
from django.contrib import admin
from django.urls import path

from cart.views import CartAddView,CartInfoView


app_name = 'cart'
urlpatterns = [
    # path('admin/', admin.site.urls),
    path(r'add', CartAddView.as_view(), name='add'),    #购物车-》添加商品到购物车
    path(r'info',CartInfoView.as_view(),name='info'),   #购物车-》显示购物车商品信息
]
