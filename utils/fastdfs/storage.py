#author xuhaixiang

from django.core.files.storage import Storage

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
