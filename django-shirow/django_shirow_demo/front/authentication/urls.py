from . import views
from django.views.generic.base import TemplateView
from django.conf.urls import url, include

urlpatterns = [
    url(r'^$', TemplateView.as_view(template_name='home.html'), name='home'),
    url(r'accounts/signup/', views.SignUp.as_view(), name='signup'),
    url(r'accounts/login/submit/', views.submit, name='login'),
    url(r'accounts/', include('django.contrib.auth.urls')),
]
