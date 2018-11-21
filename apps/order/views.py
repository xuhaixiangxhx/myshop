from django.shortcuts import render,HttpResponse,redirect
from django.http import JsonResponse
from django.views.generic import View
from django.urls import reverse
from django_redis import get_redis_connection
from django.db import transaction

from goods.models import GoodsSKU
from user.models import Address
from order.models import OrderInfo,OrderGoods
from utils.mixin import LoginRequireView

from datetime import datetime
import time
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

        sku_ids = ','.join(sku_ids)

        context = {
            'skus':skus,
            'total_count':total_count,
            'total_price':total_price,
            'transit_price':transit_price,
            'total_pay':total_pay,
            'addrs':addrs,
            'sku_ids':sku_ids
        }

        return render(request, 'place_order.html', context)


#/order/commit
#前端传递数据：1.寄送地址，2.支付方式，3.商品ids
#sql事务操作：一组sql，要么成功，要么失败
#悲观锁
class OrderCommitView1(LoginRequireView, View):
    '''订单创建'''
    @transaction.atomic
    def post(self,request):
        '''订单创建'''
        #校验用户登陆状态
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res':0,'errmsg':'用户未登录'})
        #接受参数
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')
        #校验参数
        if not all([addr_id,pay_method,sku_ids]):
            return JsonResponse({'res':1,'errmsg':'参数不完整'})

        #校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res':2,'errmsg':'非法支付方式'})

        #校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist as e:
            return JsonResponse({'res':3,'errmsg':'地址不存在'})

        #创建订单
        order_id = datetime.now().strftime('%Y%m%d%H%M%S')+str(user.id)

        #运费
        transit_price = 10
        #总数目和总金额
        total_count = 0
        total_price = 0

        #设置事务保存点
        save_id = transaction.savepoint()
        try:
            #向订单表中插入数据
            order = OrderInfo.objects.create(
                order_id=order_id,
                user = user,
                addr = addr,
                pay_method = pay_method,
                total_count = total_count,
                total_price = total_price,
                transit_price = transit_price,
            )
            #向订单商品表中插入数据,一个商品，插一条数据
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                #获取商品信息
                try:
                    # sku = GoodsSKU.objects.get(id=sku_id)
                    #悲观锁,类似于sql:select * from goods_sku where id=sku_id for update
                    #前一个事务未完成时，其他事务执行到这里时会发生阻塞
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                except GoodsSKU.DoesNotExist as e:
                    #商品不存在
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res':4,'errmsg':'商品不存在'})

                #获取商品购买数量
                count = conn.hget(cart_key,sku_id)
                #校验库存
                if int(count) > sku.stock:
                    #库存不足
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res':6,'errmsg':'商品库存不足'})

                OrderGoods.objects.create(
                    order=order,
                    sku=sku,
                    count=count,
                    price=sku.price
                )
                #更新商品的库存和销量
                sku.stock -= int(count)
                sku.sales += int(count)
                sku.save()
                #累计商品数量和金额
                amount = sku.price*int(count)
                total_count += int(count)
                total_price += amount

            #更新订单信息表中的商品的总数量和总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res':7,'errmsg':'下单失败'})
        #下单成功提交事务
        transaction.savepoint_commit(save_id)

        #清除用户的购物车中对应的记录
        conn.hdel(cart_key,*sku_ids)

        return JsonResponse({'res':5, 'message':'创建成功'})


#/order/commit
#前端传递数据：1.寄送地址，2.支付方式，3.商品ids
#sql事务操作：一组sql，要么成功，要么失败
#乐观锁
class OrderCommitView(View):
    '''订单创建'''
    @transaction.atomic
    def post(self,request):
        '''订单创建'''
        #校验用户登陆状态
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res':0,'errmsg':'用户未登录'})
        #接受参数
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')
        #校验参数
        if not all([addr_id,pay_method,sku_ids]):
            return JsonResponse({'res':1,'errmsg':'参数不完整'})

        #校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res':2,'errmsg':'非法支付方式'})

        #校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist as e:
            return JsonResponse({'res':3,'errmsg':'地址不存在'})

        #创建订单
        order_id = datetime.now().strftime('%Y%m%d%H%M%S')+str(user.id)

        #运费
        transit_price = 10
        #总数目和总金额
        total_count = 0
        total_price = 0

        #设置事务保存点
        save_id = transaction.savepoint()
        try:
            #向订单表中插入数据
            order = OrderInfo.objects.create(
                order_id=order_id,
                user = user,
                addr = addr,
                pay_method = pay_method,
                total_count = total_count,
                total_price = total_price,
                transit_price = transit_price,
            )
            #向订单商品表中插入数据,一个商品，插一条数据
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                #获取商品信息
                for i in range(3):
                    try:
                        sku = GoodsSKU.objects.get(id=sku_id)
                    except GoodsSKU.DoesNotExist as e:
                        #商品不存在
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res':4,'errmsg':'商品不存在'})

                    #获取商品购买数量
                    count = conn.hget(cart_key,sku_id)
                    #校验库存
                    if int(count) > sku.stock:
                        #库存不足
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res':6,'errmsg':'商品库存不足'})


                    #更新商品的库存和销量
                    # sku.stock -= int(count)
                    # sku.sales += int(count)
                    # sku.save()

                    #乐观锁模式更新商品的库存和销量
                    origin_stock = sku.stock
                    new_stock = origin_stock - int(count)
                    new_sales = sku.sales + int(count)
                    #返回受影响的行数
                    res = GoodsSKU.objects.filter(id=sku_id, stock=origin_stock).update(stock=new_stock, sales=new_sales)
                    if res == 0:
                        if i==2:
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({'res':7,'errmsg':'下单失败'})
                        continue
                    #往订单商品表中中插入数据
                    OrderGoods.objects.create(
                        order=order,
                        sku=sku,
                        count=count,
                        price=sku.price
                    )
                    #累计商品数量和金额
                    amount = sku.price*int(count)
                    total_count += int(count)
                    total_price += amount
                    #跳出循环
                    break
            #更新订单信息表中的商品的总数量和总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res':7,'errmsg':'下单失败'})
        #下单成功提交事务
        transaction.savepoint_commit(save_id)

        #清除用户的购物车中对应的记录
        conn.hdel(cart_key,*sku_ids)

        return JsonResponse({'res':5, 'message':'订单创建成功'})


