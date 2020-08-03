from django.db import models
from django.conf import settings
from django.urls import reverse
from django_countries.fields import CountryField
from django.db.models.signals import pre_save, post_save


CATEGORY_CHOICES = (
    ('S', 'Shirt'),
    ('SW', 'Sport Wear'),
    ('OW', 'Outwear'),
)

LABEL_CHOICES = (
    ('P', 'primary'),
    ('S', 'secondary'),
    ('D', 'danger'),
)

ADDRESS_TYPE= (
    ('B', 'Billing'),
    ('S', 'Shipping'),
)

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    stripe_customer_id = models.CharField(max_length=50, blank=True, null=True)
    one_click_purchasing = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

class Item(models.Model):
    title = models.CharField(max_length=100)
    price = models.FloatField()
    discount_price = models.FloatField(blank=True, null=True)
    category = models.CharField(choices=CATEGORY_CHOICES, max_length=2)
    label = models.CharField(choices=LABEL_CHOICES, max_length=2)
    slug = models.SlugField()
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="products/", blank=True, null=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('orders:product-detail', kwargs={'slug': self.slug})

    def get_add_to_cart_url(self):
        return reverse("orders:add-to-cart", kwargs={
            'slug': self.slug
        })

    def get_remove_from_cart_url(self):
        return reverse("orders:remove-from-cart", kwargs={
            'slug': self.slug
        })

    def get_price(self):
        if self.discount_price:
            return self.discount_price
        return self.price

    def get_item_image(self):
        if self.image:
            return self.image.url


class OrderItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True)
    ordered = models.BooleanField(default=False)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.pk}  {self.item.title} x {self.quantity} by  {self.user.username}"

    def get_line_order_item_total(self):
        line_order_item_total = self.quantity * self.item.get_price()
        return line_order_item_total

    def get_amount_saved(self):
        amount_saved = (self.item.price- self.item.discount_price) * self.quantity
        if amount_saved > 0:
            return amount_saved 

class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ref_code = models.CharField(max_length=20, blank=True, null=True)
    ordered = models.BooleanField(default=False)
    items = models.ManyToManyField(OrderItem)
    ordered_date = models.DateTimeField(auto_now_add=True)
    shipping_address = models.ForeignKey(
        "Address",
        related_name='shipping_address',
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True,
    )
    billing_address = models.ForeignKey(
        "Address",
        related_name='billing_address',
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True,
    )
    payment = models.ForeignKey(
        "Payment",
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True
    )
    coupon = models.ForeignKey(
        "Coupon",
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True
    )
    being_delivered = models.BooleanField(default=False)
    received = models.BooleanField(default=False)
    refund_requested = models.BooleanField(default=False)
    refund_granted = models.BooleanField(default=False)


    def __str__(self):
        return f"{self.pk} - {self.user.username}"

    def get_total(self):
        total = 0
        for order_item in self.items.all():
            line_total = order_item.quantity * order_item.item.get_price()
            total += line_total
        if self.coupon:
            total -= self.coupon.amount
        return total

    def get_coupon_value(self):
        if self.coupon:
            return self.coupon.amount


class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    street_address = models.CharField(max_length=100)
    apartment_address = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = CountryField(multiple=False)
    zip_code = models.CharField(max_length=10)
    address_type = models.CharField(max_length=1, choices=ADDRESS_TYPE)
    defaut = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name_plural = "Addresses"
        ordering = ["id",]

class Payment(models.Model):
    stripe_charge_id = models.CharField(max_length=255)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    amount = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.stripe_charge_id


class Coupon(models.Model):
    code = models.CharField(max_length=15)
    amount = models.FloatField()

    def __str__(self):
        return self.code


class Refund(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    reason = models.TextField()
    accepted = models.BooleanField(default=False)
    email = models.EmailField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.pk}"


def user_profile_created(sender, instance, created, *args, **kwargs):
    # if user is created in the database create user profile
    if created:
        user_profile = UserProfile.objects.get_or_create(user=instance)


post_save.connect(user_profile_created, sender=settings.AUTH_USER_MODEL)