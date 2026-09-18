from django.urls import path

from . import views


urlpatterns = [
    path("anonymous/", views.anonymous_login_view, name="api_auth_anonymous"),
    path("wechat/", views.wechat_login_view, name="api_auth_wechat"),
]
