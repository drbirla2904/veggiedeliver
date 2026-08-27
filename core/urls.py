"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
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
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import about_us, contact_us, privacy_policy, terms

urlpatterns = [
    path('about-us/', about_us, name='about_us'),
    path('privacy-policy/', privacy_policy, name='privacy_policy'),
    path('policy/', privacy_policy, name='policy'),
    path('terms/', terms, name='terms'),
    path('contact-us/', contact_us, name='contact_us'),
    path('contact/', contact_us, name='contact'),
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('', include('catalog.urls')),
    path('', include('orders.urls')),
    path('wallet/', include('wallet.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
