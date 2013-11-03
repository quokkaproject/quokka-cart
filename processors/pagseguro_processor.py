# coding: utf-8
import logging
from flask import redirect
from pagseguro import PagSeguro
from quokka.core.templates import render_template
from .base import BaseProcessor

logger = logging.getLogger()


class PagSeguroProcessor(BaseProcessor):
    def __init__(self, cart, *args, **kwargs):
        self.cart = cart
        self.config = kwargs.get('config')
        if not isinstance(self.config, dict):
            raise ValueError("Config must be a dict")
        email = self.config.get('email')
        token = self.config.get('token')
        self.pg = PagSeguro(email=email, token=token)
        logger.debug("Processor initialized {}".format(self.__dict__))

    def validate(self, *args, **kwargs):
        self.pg.sender = self.cart.sender_data
        self.pg.shipping = self.cart.shipping_data
        self.pg.reference = self.cart.get_uid()
        extra_costs = self.cart.get_extra_costs()
        if extra_costs:
            self.pg.extra_amount = "%.2f" % extra_costs

        self.pg.items = [
            {
                "id": item.get_uid(),
                "description": u"{i.title} - {i.description}".format(i=item),
                "amount": "%.2f" % item.total,
                "weight": item.weight,
                "quantity": int(item.quantity)
            }
            for item in self.cart.items if item.total >= 0
        ]

        if hasattr(self.cart, 'redirect_url'):
            self.pg.redirect_url = self.cart.redirect_url
        else:
            self.pg.redirect_url = self.config.get('redirect_url')

        if hasattr(self.cart, 'notification_url'):
            self.pg.notification_url = self.cart.notification_url
        else:
            self.pg.notification_url = self.config.get('notification_url')

        logger.debug("Processor validated {}".format(self.__dict__))
        return True  # all data is valid

    def process(self, *args, **kwargs):
        response = self.pg.checkout()
        if not response.errors:
            self.cart.checkout_code = response.code
            self.cart.status = 'checked_out'
            self.cart.save()
            logger.debug("Processed! {}".format(response.code))
            return redirect(response.payment_url)
        else:
            logger.debug('Error processing {}'.format(response.errors))
            return render_template("cart/checkout_error.html",
                                   response=response)
