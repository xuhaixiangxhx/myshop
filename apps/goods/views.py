from django.shortcuts import render
from django.views.generic import View
from django.core.cache import cache
from goods.models import GoodsType,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner
from django_redis import get_redis_connection
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

