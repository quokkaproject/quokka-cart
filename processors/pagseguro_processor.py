# coding: utf-8
import logging
from flask import redirect, request
from pagseguro import PagSeguro
from quokka.core.templates import render_template
from .base import BaseProcessor
from ..models import Cart

logger = logging.getLogger()


class PagSeguroProcessor(BaseProcessor):

    STATUS_MAP = {
        "1": "checked_out",
        "2": "analysing",
        "3": "confirmed",
        "4": "completed",
        "5": "refunding",
        "6": "refunded",
        "7": "cancelled"
    }

    def __init__(self, cart, *args, **kwargs):
        self.cart = cart
        self.config = kwargs.get('config')
        self._record = kwargs.get('_record')
        if not isinstance(self.config, dict):
            raise ValueError("Config must be a dict")
        email = self.config.get('email')
        token = self.config.get('token')
        self.pg = PagSeguro(email=email, token=token)
        self.cart and self.cart.addlog(
            "PagSeguro initialized {}".format(self.__dict__)
        )

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
                "amount": "%.2f" % item.unity_plus_extra,
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

        self.cart.addlog("pagSeguro validated {}".format(self.pg.data))
        return True  # all data is valid

    def process(self, *args, **kwargs):
        kwargs.update(self._record.config)
        kwargs.update(self.cart.config)
        response = self.pg.checkout(**kwargs)
        if not response.errors:
            self.cart.checkout_code = response.code
            #self.cart.status = 'checked_out'  # should set on redirect url
            self.cart.addlog("PagSeguro processed! {}".format(response.code))
            return redirect(response.payment_url)
        else:
            self.cart.addlog(
                'PagSeguro error processing {}'.format(
                    response.errors
                )
            )
            return render_template("cart/checkout_error.html",
                                   response=response, cart=self.cart)

    def notification(self):
        code = request.form.get('notificationCode')
        if not code:
            return "notification code not found"

        response = self.pg.check_notification(code)
        reference = getattr(response, 'reference', None)
        if not reference:
            return "reference not found"

        PREFIX = self.pg.config.get('REFERENCE_PREFIX', '') or ''
        PREFIX = PREFIX.replace('%s', '')

        status = getattr(response, 'status', None)
        transaction_code = getattr(response, 'code', None)

        # TODO: get grossAmount to populate a payment with methods
        try:
            self.cart = Cart.objects.get(
                reference_code=reference.replace(PREFIX, '')
            )
            self.cart.status = self.STATUS_MAP.get(
                str(status), self.cart.status
            )
            if transaction_code:
                self.cart.transaction_code = transaction_code
            msg = "Status changed to: %s" % self.cart.status
            self.cart.addlog(msg)
            return msg
        except Exception as e:
            msg = "Cart not found: {} - {}".format(reference, e)
            logger.error(msg)
            return msg

    def confirmation(self):  # redirect_url
        context = {}
        transaction_param = self.config.get(
            'transaction_param',
            self.pg.config.get('TRANSACTION_PARAM', 'transaction_id')
        )
        transaction_code = request.args.get(transaction_param)
        if transaction_code:
            context['transaction_code'] = transaction_code
            response = self.pg.check_transaction(transaction_code)
            reference = getattr(response, 'reference', None)
            if not reference:
                return render_template('cart/simple_confirmation.html',
                                       **context)
            PREFIX = self.pg.config.get('REFERENCE_PREFIX', '') or ''
            PREFIX = PREFIX.replace('%s', '')

            status = getattr(response, 'status', None)

            # TODO: get grossAmount to populate a payment with methods
            try:
                self.cart = Cart.objects.get(
                    reference_code=reference.replace(PREFIX, '')
                )
                self.cart.status = self.STATUS_MAP.get(
                    str(status), self.cart.status
                )
                if not self.cart.transaction_code:
                    self.cart.transaction_code = transaction_code
                msg = "Status changed to: %s" % self.cart.status
                self.cart.addlog(msg)
                context['cart'] = self.cart
                return render_template('cart/confirmation.html', **context)
            except Exception as e:
                msg = "Cart not found: {} - {}".format(reference, e)
                logger.error(msg)
        return render_template('cart/simple_confirmation.html', **context)
