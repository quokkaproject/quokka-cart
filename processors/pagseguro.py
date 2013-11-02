# coding: utf-8
from flask import current_app, redirect
from pagseguro import PagSeguro
from quokka.core.templates import render_template
from .base import BaseProcessor


class PagSeguroProcessor(BaseProcessor):
    def __init__(self, cart, *args, **kwargs):
        self.cart = cart
        email = current_app.config.get('PAGSEGURO_EMAIL')
        token = current_app.config.get('PAGSEGURO_TOKEN')
        self.pg = PagSeguro(email=email, token=token)

    def validate(self, *args, **kwargs):
        self.pg.sender = self.cart.sender_data
        self.pg.shipping = self.cart.shipping_data
        try:
            self.pg.reference = self.cart.reference.get_uid()
        except:
            self.pg.reference = self.cart.get_uid()

        try:
            self.pg.extra_amount = sum(self.cart.extra_costs.values())
        except:
            self.pg.extra_amount = None

        self.pg.items = [
            {
                "id": item.get_uid(),
                "description": u"{i.title} - {i.description}".format(i=item),
                "amount": item.total,
                "weight": item.weight,
                "quantity": item.quantity
            }
            for item in self.cart.items if item.total >= 0
        ]

        if hasattr(self.cart, 'redirect_url'):
            self.pg.redirect_url = self.cart.redirect_url
        else:
            self.pg.redirect_url = current_app.config.get(
                'PAGSEGURO_REDIRECT_URL')

        if hasattr(self.cart, 'notification_url'):
            self.pg.notification_url = self.cart.notification_url
        else:
            self.pg.notification_url = current_app.config.get(
                'PAGSEGURO_NOTIFICATION_URL')

    def process(self, *args, **kwargs):
        response = self.pg.checkout()
        if not response.errors:
            return redirect(response.payment_url)
        else:
            return render_template("cart/checkout_error.html",
                                   response=response)
