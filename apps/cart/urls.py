
from django.contrib import admin
from django.urls import path

from cart.views import CartAddView


app_name = 'cart'
urlpatterns = [
    # path('admin/', admin.site.urls),
    path(r'add', CartAddView.as_view(), name='add'),
]
