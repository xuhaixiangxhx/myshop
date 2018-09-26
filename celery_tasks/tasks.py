from celery import Celery
from django.conf import settings
from django.core.mail import send_mail
import time

# 在任务处理者(worker)一端加这几句,django环境初始化
# import os
# import django
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myshop.settings")
# django.setup()

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
