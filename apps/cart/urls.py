
from django.contrib import admin
from django.urls import path

from cart.views import CartAddView,CartInfoView,CartUpdateView,CartDeleteView


app_name = 'cart'
urlpatterns = [
    # path('admin/', admin.site.urls),
    path(r'add', CartAddView.as_view(), name='add'),    #购物车-》添加商品到购物车
    path(r'info',CartInfoView.as_view(),name='info'),   #购物车-》显示购物车商品信息
    path(r'update',CartUpdateView.as_view(),name='update'),   #购物车-》更新购物车商品信息
    path(r'delete',CartDeleteView.as_view(),name='delete'),   #购物车-》删除购物车商品信息
]
