from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.product_list, name="product_list"),
    path("products/<slug:slug>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:pk>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:pk>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:pk>/", views.cart_remove, name="cart_remove"),
    path("register/", views.register, name="register"),
    path("login/", views.StoreLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),  # POST only
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.order_history, name="order_history"),
    path("orders/<str:order_number>/", views.order_detail, name="order_detail"),
    path("orders/<str:order_number>/confirmation/", views.order_confirmation, name="order_confirmation"),
]
