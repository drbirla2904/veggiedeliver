from django.urls import path
from .views import home, product_detail

urlpatterns = [
    path("", home, name="home"),
    path("product/<int:pk>/", product_detail, name="product_detail"),
]
