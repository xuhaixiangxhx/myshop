from django.contrib.auth.decorators import login_required

class LoginRequireView(object):
    '''用户认证mixin类'''
    @classmethod
    def as_view(cls, **initkwargs):
        #调用父类的as_view
        view = super(LoginRequireView,cls).as_view(**initkwargs)
        return login_required(view)