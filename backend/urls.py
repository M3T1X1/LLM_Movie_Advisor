"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView


frontend = TemplateView.as_view(template_name='index.html')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('backend.accounts.urls')),
    path('api/', include('backend.api.urls')),
    path('', frontend, name='frontend-home'),
    path('login', frontend, name='frontend-login'),
    path('register', frontend, name='frontend-register'),
    path('recommendations', frontend, name='frontend-recommendations'),
    path('catalog', frontend, name='frontend-catalog'),
    path('trends', frontend, name='frontend-trends'),
    path('upcoming', frontend, name='frontend-upcoming'),
    path('watchlist', frontend, name='frontend-watchlist'),
    path('analytics', frontend, name='frontend-analytics'),
    path('profile', frontend, name='frontend-profile'),
]
