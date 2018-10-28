from celery import Celery
from django.conf import settings
from django.core.mail import send_mail
from django.template import loader
import time,os

# 在任务处理者(worker)一端加这几句,django环境初始化
# import os
# import django
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myshop.settings")
# django.setup()

from goods.models import GoodsType,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner

# 创建一个Celery类的实例对象
app = Celery('celery_tasks.tasks',broker=settings.BROKER)

#定义任务函数
@app.task
def send_register_active_email(to_email,username,token):
    subject = 'myshop购物网站'
    message = ''
    sender = settings.EMAIL_FROM
    recive_list = [to_email]
    html_msg = '%s,<br /><p style="text-indent:4em">欢迎成为myshop购物网站注册会员!请点击如下链接激活您的账户：</p><br /><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>'%(username,token,token)
    send_mail(subject,message,sender,recive_list,html_message=html_msg)
    # time.sleep(5)

@app.task
def generate_static_index_html():
    '''生成静态页面'''
    print('生成静态页面--starrt')
    #获取商品种类信息
    types = GoodsType.objects.all()

    #获取首页商品轮播信息
    goods_banners = IndexGoodsBanner.objects.all().order_by('index')

    #获取首页促销活动信息
    promotion_banners = IndexPromotionBanner.objects.all().order_by('index')
    print('促销活动数量：',len(promotion_banners))
    #获取首页分类商品展示信息（包含图片分类，标题分类）
    for type in types:
        #获取标题分类商品信息
        title_banners = IndexTypeGoodsBanner.objects.filter(type=type,display_type=0).order_by('index')
        #获取图片分类商品信息
        image_banners = IndexTypeGoodsBanner.objects.filter(type=type,display_type=1).order_by('index')

        #动态给type添加属性
        type.title_banners = title_banners
        type.image_banners = image_banners

    #组织模板上下文
    context = {
        'types':types,
        'promotion_banners':promotion_banners,
        'goods_banners':goods_banners
    }

    # 使用模板
    # 1.加载模板文件,返回模板对象
    temp = loader.get_template('static_index.html')
    # 2.模板渲染
    static_index_html = temp.render(context)

    index_file_path = os.path.join(settings.BASE_DIR,'static/index.html')
    print('静态首页文件全路径',index_file_path)
    with open(index_file_path,'w') as f:
        f.write(static_index_html)

    print('生成静态页面--end')
