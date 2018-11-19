from django.shortcuts import render,HttpResponse,redirect
from django.views.generic import View
from django.urls import reverse
from django_redis import get_redis_connection

from goods.models import GoodsSKU
from user.models import Address
from utils.mixin import LoginRequireView
# Create your views here.

#/order/place
class OrderPlaceView(LoginRequireView, View):
    '''提交订单页面显示'''
    def post(self,request):
        '''提交订单显示页面'''
        #获取登录用户
        user = request.user

        #获取参数sku_ids
        sku_ids = request.POST.getlist('sku_ids')
        #校验参数
        if not sku_ids:
            return redirect(reverse('cart:info'))

        cart_key = 'cart_%d'%user.id
        conn = get_redis_connection('default')

        skus = []
        total_count = 0
        total_price = 0
        #遍历sku_ids获取用户购买的商品的信息
        for  sku_id in sku_ids:
            sku = GoodsSKU.objects.get(id=sku_id)
            #获取用户购买的某一商品数量
            count = conn.hget(cart_key, sku_id)
            #计算用户购买的某一商品的小计
            amount = sku.price*int(count)
            #动态给商品添加数量和小计属性
            sku.count = int(count)
            sku.amount = amount
            #添加到购买的商品列表
            skus.append(sku)
            #累计购买的商品数量和价格
            total_count += int(count)
            total_price += amount

        # 运费:实际开发的时候，属于一个子系统
        transit_price = 10 # 写死
        #实付款
        total_pay = total_price + transit_price
        #获取用户收件地址
        addrs = Address.objects.filter(user=user)

        context = {
            'skus':skus,
            'total_count':total_count,
            'total_price':total_price,
            'transit_price':transit_price,
            'total_pay':total_pay,
            'addrs':addrs
        }

        return render(request, 'place_order.html', context)



class OrderCommitView(View):
    '''订单创建'''
    pass