from django.shortcuts import render
from orders.models import Item, OrderItem, Order
from django.views.generic import ListView, DetailView, View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from orders.forms import CheckoutForm, CouponForm, RefundForm, PaymentForm
from orders.models import Address, Payment, Coupon, Refund, UserProfile
import stripe
from django.conf import settings
import random
import string

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase+string.digits, k=20 ))


class PaymentView(View):
    def get(self, *args, **kwargs):
        order_qs = Order.objects.filter(user=self.request.user, ordered=False)
        if order_qs.exists():
            order = order_qs.first()
            if order.billing_address:
                context = {
                    'order': order,
                }
                userprofile = self.request.user.userprofile
                if userprofile.one_click_purchasing:
                    cards = stripe.Customer.list_sources(
                        userprofile.stripe_customer_id,
                        limit=3,
                        object='card'
                    )
                    card_list = cards['data']
                    if len(card_list) > 0:
                        # update the context with the default card
                        context.update({
                            'card': card_list[0]
                        })
                return render(self.request, template_name='orders/payment.html', context=context)
            messages.warning(self.request, "Please enter your billing address")
            return redirect("orders:checkout")
        return redirect("orders:item_list")

    def post(self, *args, **kwargs):
        order_qs = Order.objects.filter(user=self.request.user, ordered=False)
        form = PaymentForm(self.request.POST or None)
        userprofile = UserProfile.objects.get(user=self.request.user)
        token_b = self.request.POST.get("stripeToken")
        print(token_b)
        if form.is_valid():
            print(form.cleaned_data)
            token = form.cleaned_data.get("stripeToken")
            save = form.cleaned_data.get("save")
            use_default = form.cleaned_data.get("use_default")
            
            if order_qs.exists():
                order = order_qs.first()
                amount = int(order.get_total() * 100)


                if save:
                    if userprofile.stripe_customer_id != '' and userprofile.stripe_customer_id is not None:
                        customer = stripe.Customer.retrieve(
                            userprofile.stripe_customer_id)
                        customer.sources.create(source=token)

                    else:
                        customer = stripe.Customer.create(
                            email=self.request.user.email,
                        )
                        customer.sources.create(source=token)
                        userprofile.stripe_customer_id = customer['id']
                        userprofile.one_click_purchasing = True
                        userprofile.save()

                # create the payment     
                try:
                # Use Stripe's library to make requests...
                    if use_default or save:
                    # charge the customer because we cannot charge the token more than once
                        charge = stripe.Charge.create(
                            amount=amount,  # cents
                            currency="usd",
                            customer=userprofile.stripe_customer_id
                        )
                    else:
                        # charge once off on the token
                        charge = stripe.Charge.create(
                            amount=amount,  # cents
                            currency="usd",
                            source=token
                        )
        

                    payment = Payment()
                    payment.amount = amount /100
                    payment.stripe_charge_id = charge.id
                    payment.user = self.request.user
                    payment.save()

                    order_item_qs = order.items.all()
                    order_item_qs.update(ordered=True)

                    for order_item in order_item_qs:
                        order_item.save()

                    order.ordered = True
                    order.payment = payment

                    # creating the ref code
                    order.ref_code = create_ref_code()
                    order.save()


                    messages.success(self.request, "Your Order was successfull")
                    return redirect("orders:item_list")
                    
                except stripe.error.CardError as e:
                # Since it's a decline, stripe.error.CardError will be caught
                    messages.warning(self.request, f"{e.error.get('message')}")
                    return redirect("orders:payment-stripe")

                except stripe.error.RateLimitError as e:
                    # Too many requests made to the API too quickly
                    messages.warning(self.request, f"{e.error.get('message')}")
                    return redirect("orders:payment-stripe")

                except stripe.error.InvalidRequestError as e:
                    # Invalid parameters were supplied to Stripe's API
                    messages.warning(self.request, f"{e.error.get('message')}")
                    return redirect("orders:payment-stripe")

                except stripe.error.AuthenticationError as e:
                    # Authentication with Stripe's API failed
                    # (maybe you changed API keys recently)
                    messages.warning(self.request, f"{e.error.get('message')}")
                    return redirect("orders:payment-stripe")

                except stripe.error.APIConnectionError as e:
                    messages.warning(self.request, f"{e.error.get('message')}")
                    return redirect("orders:payment-stripe")

                except stripe.error.StripeError as e:
                    # Display a very generic error to the user, and maybe send
                    # yourself an email
                    messages.warning(self.request, f"{e.error.get('message')}")
                    return redirect("orders:payment-stripe")

                except Exception as e:
                    # Something else happened, completely unrelated to Stripe
                    messages.warning(self.request, "Something happned please contact administrator")
                    return redirect("orders:payment-stripe")
        return redirect('orders:payment-stripe')

class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'order': order,
            }
            
        except ObjectDoesNotExist:
            messages.warning(self.request, "You dont have an active order")
            return redirect("/")
        return render(self.request, template_name="orders/order_summary.html", context=context)

class ItemListView(ListView):
    model = Item
    paginate_by = 12
    template_name = "orders/home-page.html"


class ItemDetailView(DetailView):
    model = Item
    template_name = "orders/product-page.html"


def product_page(request, pk):
    product_qs = Item.objects.filter(pk=pk)
    product = None
    if product_qs.exists():
        product = product_qs.first()
    
    context = {
        'product': product
    }
    return render(request, template_name="orders/product-page.html", context=context)

@login_required
def add_to_cart(request, slug):
    item_qs = Item.objects.filter(slug=slug)
    item = None
    if item_qs.exists():
        item = item_qs.first()

    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs.first()
        if order.items.filter(item__slug=item.slug).exists():
            order_item_qs = order.items.filter(
                item__slug=item.slug, 
                user=request.user, 
                ordered=False
            )
            if order_item_qs.exists():
                order_item = order_item_qs.first()
                order_item.quantity += 1
                order_item.save()
                messages.success(request, "This Item Quantity was Updated in your cart")
        else:
            order_item , order_item_created = OrderItem.objects.get_or_create(
                item=item,
                user=request.user,
                active=True
            )
            order.items.add(order_item)
            order.save()
            messages.success(request, "This item was added to your cart")
    else:
        order_item = OrderItem.objects.create(item=item, user=request.user)
        order = Order.objects.create(user=request.user)
        order.items.add(order_item)
        order.save()
        messages.success(request, "This item was added to your cart")
    return redirect("orders:order-summary")

@login_required
def remove_from_cart(request, slug):
    item_qs = Item.objects.filter(slug=slug)
    item = None
    if item_qs.exists():
        item = item_qs.first()

    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs.first()
        if order.items.filter(item__slug=item.slug).exists():
            order_item_qs = order.items.filter(
                item__slug=item.slug, 
                user=request.user, 
                ordered=False, 
                active=True
            )
            if order_item_qs.exists():
                order_item = order_item_qs.first()
                order.items.remove(order_item)
                order_item.active = False
                order_item.save()
                messages.warning(request, "This item was removed from your cart")
            else:
                messages.success(request, "This item was not in your cart")
        else:
            messages.warning(request, "You dont have an active order")
            # add a message to the  user saying user doent have an active order
    return redirect("orders:order-summary")


def is_valid_form(values):
    valid = True
    for field in values:
        if field == "":
            valid = False
    return valid

class CheckoutView(View):
    def get(self, *args, **kwargs):
        
        form = CheckoutForm()
        context = {
            'form': form,
            'couponForm': CouponForm()
        }
        order_qs = Order.objects.filter(user=self.request.user, ordered=False)
        if order_qs.exists():
            order = order_qs.first()
            context['order'] = order


        default_shipping_address_qs = Address.objects.filter(
            user=self.request.user,
            address_type="S",
            defaut=True,
        )
        if default_shipping_address_qs.exists():
            default_shipping_address=default_shipping_address_qs.first()
            context.update({
                'default_shipping_address': default_shipping_address
            })

        default_billing_address_qs = Address.objects.filter(
            user=self.request.user,
            address_type="B",
            defaut=True
        )
        if default_billing_address_qs.exists():
            default_billing_address=default_billing_address_qs.first()
            context.update({
                'default_billing_address': default_billing_address
            })

        return render(self.request, template_name="orders/checkout-page.html", context=context)

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                use_default_shipping = form.cleaned_data.get('use_default_shipping')
                # check if the user has default shipping address or not
                if use_default_shipping:
                    default_shipping_address_qs = Address.objects.filter(
                        user=self.request.user,
                        defaut=True,
                        address_type="S"
                    )
                    if default_shipping_address_qs.exists():
                        shipping_address=default_shipping_address_qs.first()
                        order.shipping_address = shipping_address
                        order.save()
                        
                    else:
                        messages.info(self.request, "No default shipping address available")
                        return redirect("orders:checkout")
                else:
                    print("user is enterring a new shipping address")
                    shipping_address = form.cleaned_data.get('shipping_address')
                    shipping_address2 = form.cleaned_data.get('shipping_address2')
                    shipping_country = form.cleaned_data.get('shipping_country')
                    shipping_state = form.cleaned_data.get('shipping_state')
                    shipping_zip_code = form.cleaned_data.get('shipping_zip_code')

                    if is_valid_form([shipping_address,
                                    shipping_address2,
                                    shipping_country,
                                    shipping_state,
                                    shipping_zip_code]):

                        shipping_address = Address.objects.create(
                            user=self.request.user,
                            street_address=shipping_address,
                            apartment_address=shipping_address2,
                            country=shipping_country,
                            state=shipping_state,
                            zip_code=shipping_zip_code,
                            address_type='S'
                        )
                        shipping_address.save()
                        order.shipping_address = shipping_address
                        order.save()

                        set_default_shipping = form.cleaned_data.get("set_default_shipping")
                        if set_default_shipping:
                            shipping_address.defaut=True
                        shipping_address.save()
                    else:
                        messages.info(self.request, "Please enter all the shipping address data")
                        return redirect("orders:checkout")

                same_as_shipping_address =  form.cleaned_data.get("same_as_shipping_address")
                use_default_billing = form.cleaned_data.get('use_default_billing')

                # shipping address is same as the billing address
                if same_as_shipping_address:
                   
                    # cloning the billing address to a new object
                    if use_default_shipping:
                        billing_address_qs = Address.objects.filter(
                            user=self.request.user,
                            defaut=True,
                            address_type='B',
                            street_address=shipping_address.street_address,
                            apartment_address=shipping_address.apartment_address,
                            country=shipping_address.country,
                            state=shipping_address.state,
                            zip_code=shipping_address.zip_code,

                        )
                        if billing_address_qs.exists():
                            billing_address = billing_address_qs.first()
                        else:
                            billing_address= shipping_address
                            billing_address.pk= None
                            billing_address.save()
                            billing_address.address_type="B"
                            billing_address.save()
                            order.billing_address=billing_address
                            order.save()
                            billing_address_qs.update(defaut=False)
                        
                    
                # use the defaut billing address
                elif use_default_billing:
                    print("using default billing address")
                    default_billing_address_qs = Address.objects.filter(
                        user=self.request.user,
                        defaut=True,
                        address_type="B"
                    )
                    if default_billing_address_qs.exists():
                        billing_address=default_billing_address_qs.first()
                        order.billing_address = billing_address
                        order.save()
                        
                    else:
                        messages.info(self.request, "No default billing address available")
                        return redirect("orders:checkout")
                else:
                    # user is creating a new billing addresss
                    print("user is enterring a new billing address")
                    billing_address = form.cleaned_data.get('billing_address')
                    billing_address2 = form.cleaned_data.get('billing_address2')
                    billing_country = form.cleaned_data.get('billing_country')
                    billing_state = form.cleaned_data.get('billing_state')
                    billing_zip_code = form.cleaned_data.get('billing_zip_code')

                    if is_valid_form([billing_address,
                                    billing_address2,
                                    billing_country,
                                    billing_state,
                                    billing_zip_code]):

                        billing_address = Address.objects.create(
                            user=self.request.user,
                            street_address=billing_address,
                            apartment_address=billing_address2,
                            country=billing_country,
                            state=billing_state,
                            zip_code=billing_zip_code,
                            address_type='B'
                        )
                        billing_address.save()
                        order.billing_address = billing_address
                        order.save()

                        set_default_billing = form.cleaned_data.get("set_default_billing")
                        if set_default_billing:
                            billing_address.defaut=True
                        billing_address.save()
                    else:
                        messages.info(self.request, "Please enter all the billing address data")
                        return redirect("orders:checkout")
                payement_option = form.cleaned_data.get("payment_option")
                if payement_option == "S":
                    return redirect("orders:payment-stripe")
                elif payement_option == "P":
                    return redirect("orders:payment-stripe")
                else:
                    return redirect("orders:checkout")
        except ObjectDoesNotExist:
            messages.warning(self.request, "You dont have an active order")
            return redirect("orders:order-summary")
        return redirect("orders:checkout")
       


@login_required
def remove_single_item_from_cart(request, slug):
    item_qs = Item.objects.filter(slug=slug)
    item = None
    if item_qs.exists():
        item = item_qs.first()

    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs.first()
        if order.items.filter(item__slug=item.slug).exists():
            order_item_qs = order.items.filter(
                item__slug=item.slug, 
                user=request.user, 
                ordered=False, 
                active=True
            )
            if order_item_qs.exists():
                order_item = order_item_qs.first()
                if order_item.quantity > 1:
                    order_item.quantity -= 1
                elif order_item.quantity == 1:
                    order.items.remove(order_item)
                    order_item.active = False
                order_item.save()
                messages.warning(request, "This item was removed from your cart")

            else:
                messages.success(request, "This item was not in your cart")
        else:
            messages.warning(request, "You dont have an active order")
            # add a message to the  user saying user doent have an active order
    return redirect("orders:order-summary")


def get_coupon(request, code):
    coupon_qs = Coupon.objects.filter(code=code)
    if coupon_qs.exists():
        coupon = coupon_qs.first()
        return coupon
    messages.warning(request, "This Coupon Does not exists")
    return redirect("orders:checkout")


class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            code = form.cleaned_data.get('code')
            order_qs = Order.objects.filter(user=self.request.user, ordered=False)
            if order_qs.exists():
                order = order_qs.first()
                order.coupon = get_coupon(self.request, code)
                order.save()
                messages.success(self.request, "Coupon Added Successfully")
                return redirect("orders:checkout")
        return redirect("orders:checkout")


class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            "form": form
        }
        return render(self.request, template_name="orders/request_refund.html", context=context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST or None)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            
            # edit the order and store the refund
            order_qs = Order.objects.filter(ref_code=ref_code)
            if order_qs.exists():
                order = order_qs.first()
                refund, refund_created = Refund.objects.get_or_create(order=order)
                refund.reason = message
                refund.email = email
                refund.save()
                
                if refund_created:
                    order.refund_requested = True
                    order.save()
                    messages.success(self.request, "Your message was recieved")
                    
                else:
                    messages.warning(self.request, "You have already requested for refunding")
            else:
                messages.warning(self.request, "Invalid Reference Number please try again")
                return redirect("orders:request_refund")
            return redirect("/")
                
                

