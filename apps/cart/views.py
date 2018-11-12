from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic import View
from django_redis import get_redis_connection

from goods.models import GoodsSKU

#ajax请求
#/cart/add
class CartAddView(View):
    '''购物车记录添加'''
    def post(self,request):
        '''购物车记录添加'''

        #判断用户是否登录
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res':0,'err_msg':'请先登录'})

        #接受数据，商品id:goods_id,商品数量:goods_num
        goods_id = request.POST.get('goods_id')
        goods_num = request.POST.get('goods_num')

        #数据校验
        if not all([goods_id,goods_num]):
            return JsonResponse({'res':1,'err_msg':'数据不完整'})

        #校验商品数量是否合法
        try:
            goods_num = int(goods_num)
        except Exception as e:
            return JsonResponse({'res':2,'err_msg':'商品数量出错'})

        #校验商品是否存在
        try:
            goods_sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist as e:
            return JsonResponse({'res':3,'err_msg':'商品不存在'})

        #添加购物车记录
        cart_key = 'cart_%d'%user.id
        conn = get_redis_connection('default')
        #获取购物车中商品数量
        cart_goods_num = conn.hget(cart_key,goods_id)
        print()
        #累加购物车中的商品
        if cart_goods_num:
            goods_num += int(cart_goods_num)

        #校验商品库存
        if goods_num >= goods_sku.stock:
            return JsonResponse({'res':4,'err_msg':'商品库存不足'})

        #设置购物车中商品数量
        conn.hset(cart_key,goods_id,goods_num)

        #计算购物车中商品条目数
        total_count = conn.hlen(cart_key)

        return JsonResponse({'res':5,'total_count':total_count,'msg':'添加成功'})




