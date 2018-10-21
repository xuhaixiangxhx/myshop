#author xuhaixiang

from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client
from myshop import settings

class FdfsStorage(Storage):
    '''自定义fast dfs文件存储类'''
    def __init__(self):
        pass

    def _open(self, name, mode='rb'):
        '''打开文件时使用'''
        pass

    def _save(self, name, content):
        '''保存文件时使用'''
        # name:你选择上传文件的名字
        # content:包含你上传文件内容的File对象
        client = Fdfs_client(settings.FDFS_CLIENT_CONF)
        res = client.upload_by_buffer(content.read())
        #  return res is a dict
        # {
        #     'Group name': 'group1',
        #     'Remote file_id': 'group1/M00/00/00/wKjigFvIH5aAUgUYAAA_C2JBPEg953.jpg',
        #     'Status': 'Upload successed.',
        #     'Local file name': '/home/test/1.jpg',
        #     'Uploaded size': '15.00KB',
        #     'Storage IP': '192.168.11.131'
        # }
        print(res)
        # 上传失败
        if res.get('Status') != 'Upload successed.':
            raise Exception('上传文件到fast dfs失败')

        # 获取返回的文件ID
        filename = res.get('Remote file_id')
        return filename

    def exists(self, name):
        '''Django判断文件名是否可用'''
        return False

    def url(self, name):
        '''返回访问文件的url路径'''
        return settings.base_url+name