from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("csrf/", views.csrf, name="csrf"),
    path("login/", views.login, name="login"),
    path("register/", views.register, name="register"),
    path("session/", views.session, name="session"),
    path("logout/", views.logout, name="logout"),
]
