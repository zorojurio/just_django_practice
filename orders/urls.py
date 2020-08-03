from django.urls import path
from orders.views import (
    ItemListView, 
    ItemDetailView, 
    CheckoutView,
    add_to_cart,
    remove_from_cart,
    OrderSummaryView,
    remove_single_item_from_cart,
    PaymentView,
    AddCouponView,
    RequestRefundView

)

app_name = "orders"
urlpatterns = [
    path('', ItemListView.as_view(), name='item_list'),
    path('checkout/', CheckoutView.as_view() , name='checkout'),
    path('product/<slug>/', ItemDetailView.as_view() , name='product-detail'),
    path('add-to-cart/<slug>/', add_to_cart , name='add-to-cart'),
    path('remove-from-cart/<slug>/', remove_from_cart , name='remove-from-cart'),
    path(
        'remove-single-item-from-cart/<slug>/', 
        remove_single_item_from_cart , 
        name='remove-single-item-from-cart'
    ),
    path('order-summary/', OrderSummaryView.as_view(), name='order-summary'),
    path('payment/stripe/', PaymentView.as_view(), name='payment-stripe'),
    path('add_coupon/', AddCouponView.as_view(), name='add_coupon'),
    path('request-refund/', RequestRefundView.as_view(), name='request_refund'),
]

