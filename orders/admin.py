from django.contrib import admin
from .models import Item, Order, OrderItem, Address, Payment, Coupon, Refund, UserProfile


def make_refund_accepted(modeladmin, request, queryset):
    queryset.update(refund_requested=False, refund_granted=True)

make_refund_accepted.short_descrition = "Update order to refund granted"

class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'ordered', 
        'being_delivered',
        'received',
        'refund_requested',
        'refund_granted',
        'billing_address',
        'shipping_address',
        'payment',
        'coupon',
    ]
    list_display_links = [
        'user',
        'billing_address',
        'shipping_address',
        'payment',
        'coupon',
    ]

    list_filter = [
        'ordered', 
        'being_delivered',
        'received',
        'refund_requested',
        'refund_granted',
    ]

    search_fields = [
        'user__username',
        'ref_code'
    ]

    actions = [make_refund_accepted]

class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'item', 'ordered']



class RefundAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'order',
        'reason',
        'email',
    ]

class AddressAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'street_address',
        'apartment_address',
        'country',
        'zip_code',
        'address_type',
        'defaut',
    ]

    list_filter = [
        'address_type',
        'defaut',    
        'country',
        
    ]

    search_fields = [
        'user',
        'street_address',
        'apartment_address',
        'zip_code',
    ]


admin.site.register(Address, AddressAdmin)
admin.site.register(Item)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem, OrderItemAdmin)
admin.site.register(Payment)
admin.site.register(Coupon)
admin.site.register(Refund, RefundAdmin)
admin.site.register(UserProfile)

