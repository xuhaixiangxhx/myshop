from django.shortcuts import render,HttpResponse,redirect
from django.urls import reverse
from django.views.generic import View
from django.core.cache import cache
from django.core.paginator import Paginator
from goods.models import GoodsType,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner,GoodsSKU
from django_redis import get_redis_connection
from order.models import OrderGoods
# Create your views here.

#http://127.0.0.1:8000
class IndexView(View):
    '''首页'''
    def get(self,request):
        '''显示首页'''

        #尝试获取缓存数据
        context = cache.get('index_page_data')
        if context is None:
            print('设置缓存')

            #获取商品种类信息
            types = GoodsType.objects.all()

            #获取首页轮播商品信息
            goods_banners = IndexGoodsBanner.objects.all().order_by('index')

            #获取首页促销活动信息
            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

            #获取首页分类商品展示信息（包含图片分类，标题分类）
            for type in types:
                #获取标题分类商品信息
                title_banners = IndexTypeGoodsBanner.objects.filter(type=type,display_type=0).order_by('index')
                #获取图片分类商品信息
                image_banners = IndexTypeGoodsBanner.objects.filter(type=type,display_type=1).order_by('index')

                #动态给type添加属性
                type.title_banners = title_banners
                type.image_banners = image_banners

            context = {
                'types':types,
                'goods_banners':goods_banners,
                'promotion_banners':promotion_banners,
            }
            #设置缓存
            #key-value-timeout(s)
            cache.set('index_page_data',context,3600)

        #获取购物车商品数量
        user = request.user
        cart_count = 0

        if user.is_authenticated:
            #用户已登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            cart_count = conn.hlen(cart_key)

        #组织模板上下文
        context.update(cart_count=cart_count)

        return render(request,'index.html',context)

# /goods/商品id
class DetailView(View):
    '''商品详情页'''
    def get(self,request,goods_id):
        '''显示商品详情页面'''
        # return HttpResponse(goods_id)
        try:
            goods_sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist as e:
            return redirect(reverse('goods:index'))

        #获取商品的分类信息
        types = GoodsType.objects.all()

        #获取商品的评论信息
        goods_orders = OrderGoods.objects.filter(sku = goods_sku).exclude(comment='')

        #获取新品信息
        new_goods = GoodsSKU.objects.filter(type=goods_sku.type).order_by('-create_time')[0:2]

        #获取同一个SPU的其他规格商品
        same_spu_goods = GoodsSKU.objects.filter(goods=goods_sku.goods).exclude(id=goods_id)

        #获取用户购物车中商品的数目
        user = request.user
        cart_count = 0

        if user.is_authenticated:
            #用户已登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%s'%user.id
            cart_count = conn.hlen(cart_key)

            #添加用户浏览记录
            history_key = 'history_%s'%user.id
            # 移除列表中的goods_id
            conn.lrem(history_key, 0, goods_id)
            # 把goods_id插入到列表的左侧
            conn.lpush(history_key, goods_id)
            # 只保存用户最新浏览的5条信息
            conn.ltrim(history_key, 0, 4)

        #组织模板上下文
        context = {
            'goods_sku':goods_sku,
            'types':types,
            'goods_orders':goods_orders,
            'new_goods':new_goods,
            'same_spu_goods':same_spu_goods,
            'cart_count':cart_count
        }

        return render(request,'detail.html',context)

#/list/种类id/页码?sort=排序方式
class ListView(View):
    '''列表页'''
    def get(self,request,type_id,page):
        '''显示列表页'''

        #获取商品分类
        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist as e:
            return redirect('goods:index')

        #获取商品分类信息
        types = GoodsType.objects.all()

        #获取排序方式：价格:price,人气:hot,默认:default
        sort = request.GET.get('sort')
        if sort == 'price':
            goods_skus = GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == 'hot':
            goods_skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            sort = 'default'
            goods_skus = GoodsSKU.objects.filter(type=type).order_by('-id')

        #对数据进行分页
        paginator = Paginator(goods_skus,1)

        #获取页码
        try:
            page = int(page)
        except Exception as e:
            page = 1

        if page > paginator.num_pages:
            page = 1

        #获取page页商品
        page_goods = paginator.page(page)

        # todo: 进行页码的控制，页面上最多显示5个页码
        #总页数小于5页，显示所有页码
        #当前页是前三页，显示1-5页
        #当前页是后三页，显示后5页
        #其他情况，显示前俩页、当前页、后俩页
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages+1)
        elif page <= 3:
            pages = range(1, 6)
        elif page > num_pages-3:
            pages = range(num_pages-5, num_pages+1)
        else:
            pages = range(num_pages-2, num_pages+3)

        #新品信息
        new_goods = GoodsSKU.objects.filter(type=type).order_by('-create_time')[0:2]

        #获取用户
        user = request.user

        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            cart_count = conn.hlen(cart_key)


        #组织上下文
        context = {
            'types':types,
            'type':type,
            'sort':sort,
            'page_goods':page_goods,
            'pages':pages,
            'new_goods':new_goods,
            'cart_count':cart_count
        }

        return render(request, 'list.html', context)

