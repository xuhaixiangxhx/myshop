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
from myshop import settings

from datetime import datetime
from alipay import AliPay
import time,os
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

#/order/pay
class OrderPayView(View):
    '''订单支付'''
    def post(self,request):
        '''订单支付'''
        #用户校验
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res':0,'errmsg':'用户未登录'})
        #获取参数:订单编号(order_id)
        order_id = request.POST.get('order_id')
        #校验参数
        if not order_id:
            return JsonResponse({'res':1,'errmsg':'无效的订单id'})
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, pay_method=3, order_status=1)
        except OrderInfo.DoesNotExist as e:
            return JsonResponse({'res':2,'errmsg':'订单错误'})
        #业务处理：使用Python SDK调用支付宝支付接口（https://github.com/fzlee/alipay/blob/master/README.zh-hans.md）
        alipay = AliPay(
            appid="2016091900550515",
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem'),
            alipay_public_key_path=os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem'), # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False
        )
        # 调用支付接口
        # 电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string
        total_pay = order.total_price+order.transit_price # Decimal
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id, # 订单id
            total_amount=str(total_pay), # 支付总金额
            subject='我的生鲜网站%s'%order_id,
            return_url=None,
            notify_url=None  # 可选, 不填则使用默认notify url
        )
        # 返回应答
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        return JsonResponse({'res':3, 'pay_url':pay_url})

#ajax post
#/order/check
class OrderCheckView(View):
    '''订单支付结果查询'''
    def post(self,request):
        '''订单支付结果查询'''
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res':0,'errmsg':'用户未登录'})
        #获取参数:订单编号(order_id)
        order_id = request.POST.get('order_id')
        #校验参数
        if not order_id:
            return JsonResponse({'res':1,'errmsg':'无效的订单id'})
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, pay_method=3, order_status=1)
        except OrderInfo.DoesNotExist as e:
            return JsonResponse({'res':2,'errmsg':'订单错误'})
        #业务处理：使用Python SDK调用支付宝支付接口（https://github.com/fzlee/alipay/blob/master/README.zh-hans.md）
        alipay = AliPay(
            appid="2016091900550515",
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem'),
            alipay_public_key_path=os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem'), # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False
        )
        #调用支付宝的交易查询接口
        while True:
            response = alipay.api_alipay_trade_query(order_id)
            print(response)
          #   response = {
          #   "trade_no": "2017032121001004070200176844",
          #   "code": "10000",
          #   "invoice_amount": "20.00",
          #   "open_id": "20880072506750308812798160715407",
          #   "fund_bill_list": [
          #     {
          #       "amount": "20.00",
          #       "fund_channel": "ALIPAYACCOUNT"
          #     }
          #   ],
          #   "buyer_logon_id": "csq***@sandbox.com",
          #   "send_pay_date": "2017-03-21 13:29:17",
          #   "receipt_amount": "20.00",
          #   "out_trade_no": "out_trade_no15",
          #   "buyer_pay_amount": "20.00",
          #   "buyer_user_id": "2088102169481075",
          #   "msg": "Success",
          #   "point_amount": "0.00",
          #   "trade_status": "TRADE_SUCCESS",
          #   "total_amount": "20.00"
          # }
            code = response.get('code')
            trade_status = response.get('trade_status')

            if code=='10000' and trade_status=='TRADE_SUCCESS':
                #支付成功
                #获取支付宝交易号
                trade_no = response.get('trade_no')
                #更新订单状态
                order.trade_no=trade_no
                order.order_status=4    #待评价
                order.save()
                #返回结果
                return JsonResponse({'res':3,'msg':'支付成功'})
            elif code == '40004' or (code == '10000' and trade_status == 'WAIT_BUYER_PAY'):
                # 等待买家付款
                # 业务处理失败，可能一会就会成功
                time.sleep(5)
                continue
            else:
                #支付出错
                return JsonResponse({'res':4,'errmsg':'支付失败'})
#订单商品品论
#/order/comment
class OrderCommentkView(View):
    '''订单商品评论'''
    def get(self, request, order_id):
        '''显示订单商品评论页面'''
        user = request.user
        #获取参数
        order_id=order_id

        return render(request, 'order_comment.html', {'order_id':order_id})
        # return HttpResponse('OrderCommentkView')
    def post(self, request, order_id):
        '''订单商品评论提交'''
