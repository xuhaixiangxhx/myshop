from django.db import models
from django.contrib.auth.models import AbstractUser
from db.base_model import BaseModel

# Create your models here.

class User(AbstractUser,BaseModel):
    '''用户模型类'''

    class Meta:
        db_table = 'myshop_user'
        verbose_name = '用户'
        verbose_name_plural = '用户'

class AddressManger(models.Manager):
    '''自定义地址模型管理器'''
    #应用场景：
    #1.改变原有查询的结果集：all()
    #2.封装方法:用户操作模型类对应的数据表(增删改查)
    def get_default_address(self,user):
        '''获取用户默认收货地址地址'''
        # self.model:获取self对象所在的模型类
        try:
            # default_addr = Address.objects.get(user=user,is_default=True)
            # default_addr = self.model.objects.get(user=user,is_default=True)
            default_addr = self.get(user=user,is_default=True)
        except Address.DoesNotExist:
            default_addr = None
        return default_addr

class Address(models.Model):
    '''地址模型类'''
    user = models.ForeignKey('User',verbose_name='所属用户',on_delete=models.CASCADE)
    recv = models.CharField(max_length=20,verbose_name='收件人')
    addr = models.CharField(max_length=256,verbose_name='收件地址')
    zip_code = models.CharField(max_length=6,verbose_name='邮政编码')
    phone = models.CharField(max_length=11,verbose_name='联系电话')
    is_default = models.BooleanField(default=False,verbose_name='是否默认')

    objects = AddressManger()

    class Meta:
        db_table = 'myshop_address'
        verbose_name = '地址'
        verbose_name_plural = '地址'
