#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
from flask import request, jsonify, redirect
from flask.views import MethodView
from quokka.core.templates import render_template

from .models import Cart

import logging
logger = logging.getLogger()


class BaseView(MethodView):
    def get(self):
        # by default redirects to /cart on get
        return self.redirect()

    def as_json(self, **kwargs):
        format = request.args.get('format')
        if request.is_xhr or format == 'json':
            for k, v in kwargs.items():
                if hasattr(v, 'to_json'):
                    kwargs[k] = json.loads(v.to_json())
            try:
                return jsonify(kwargs)
            except:
                return jsonify({"result": str(kwargs)})

    def render(self, *args, **kwargs):
        return self.as_json(**kwargs) or render_template(*args, **kwargs)

    def redirect(self, *args, **kwargs):
        next = request.values.get('next', '/cart')
        return self.as_json(**kwargs) or redirect(next)


class CartView(BaseView):

    def get(self):
        context = {"cart": Cart.get_cart()}
        return self.render('cart/cart.html', **context)


class SetItemView(BaseView):
    def post(self):
        cart = Cart.get_cart()
        print request.form
        params = {k: v for k, v in request.form.items() if not k == "next"}
        item = cart.set_item(**params)
        return self.redirect(item=item)


class RemoveItemView(BaseView):
    def post(self):
        cart = Cart.get_cart()
        params = {k: v for k, v in request.form.items() if not k == "next"}
        item = cart.remove_item(**params)
        return self.redirect(item=item)


class SetProcessorView(BaseView):
    def post(self):
        cart = Cart.get_cart()
        processor = request.form.get('processor')
        cart.set_processor(processor)
        return self.redirect(processor=cart.processor.identifier)


# class SetStatusView(BaseView):
#     def post(self):
#         pass  # to be implemented


# class ConfigureView(BaseView):
#     pass


class CheckoutView(BaseView):
    def post(self):
        pass


class HistoryView(BaseView):
    pass
