#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask.views import MethodView
from quokka.core.templates import render_template

from .models import Cart

import logging
logger = logging.getLogger()


class CartView(MethodView):

    def get_context(self):
        cart = Cart.get_cart()
        context = {
            "cart": cart
        }
        return context

    def get(self):
        context = self.get_context()
        return render_template('cart/cart.html', **context)
