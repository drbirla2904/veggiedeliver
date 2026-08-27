from django.urls import path
from . import views

urlpatterns = [
    # cart
    path("cart/", views.cart_page, name="cart"),
    path("cart/add/<int:variant_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<int:variant_id>/", views.update_cart_item, name="update_cart_item"),
    path("cart/remove/<int:variant_id>/", views.remove_from_cart, name="remove_from_cart"),

    # checkout + customer orders
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.order_history, name="order_history"),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path("orders/<int:order_id>/cancel/", views.cancel_order, name="cancel_order"),
    path("orders/<int:order_id>/spin-gift/", views.spin_gift, name="spin_gift"),
    path("orders/<int:order_id>/tracking-data/", views.order_tracking_data, name="order_tracking_data"),

    # area admin
    path("area/", views.area_dashboard, name="area_dashboard"),
    path("area/orders/<int:order_id>/assign/", views.assign_delivery_member, name="assign_delivery_member"),
    path("area/orders/<int:order_id>/auto-assign/", views.auto_assign_delivery_member, name="auto_assign_delivery_member"),
    path("area/delivery-members/new/", views.create_delivery_member, name="create_delivery_member"),
    path("area/map/", views.area_live_map, name="area_live_map"),
    path("area/map/data/", views.area_live_map_data, name="area_live_map_data"),

    # delivery member
    path("delivery/", views.delivery_dashboard, name="delivery_dashboard"),
    path("delivery/toggle-duty/", views.toggle_duty, name="toggle_duty"),
    path("delivery/update-location/", views.update_my_location, name="update_my_location"),
    path("delivery/orders/<int:order_id>/status/", views.update_order_status, name="update_order_status"),
    path("delivery/orders/<int:order_id>/ping/", views.ping_location, name="ping_location"),
]