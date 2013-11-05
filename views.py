#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
from flask import request, jsonify, redirect, url_for, session, current_app
from flask.views import View, MethodView
from quokka.core.templates import render_template
from quokka.utils import get_current_user
from flask.ext.security import current_user
from flask.ext.security.utils import url_for_security
from .models import Cart, Processor

import logging
logger = logging.getLogger()


class BaseView(MethodView):

    requires_login = False

    def needs_login(self, **kwargs):
        if not current_user.is_authenticated():
            next = kwargs.get('next', request.values.get('next', '/cart'))
            return redirect(url_for_security('login', next=next))

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
        if not session.get('cart_id'):
            return self.render(
                'cart/empty_cart.html',
                url=current_app.config.get('CART_CONTINUE_URL', '/')
            )

        cart = Cart.get_cart()
        context = {"cart": cart}

        if cart.items:
            template = 'cart/cart.html'
        else:
            template = 'cart/empty_cart.html'
            context['url'] = cart.continue_shopping_url

        return self.render(template, **context)


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


class CheckoutView(BaseView):
    def post(self):
        cart = Cart.get_cart()
        return (cart.requires_login and self.needs_login()) \
            or cart.process_pipeline()


class HistoryView(BaseView):
    def get(self):
        context = {
            "carts": Cart.objects(belongs_to=get_current_user())
        }
        return self.needs_login(next=url_for('cart.history')) or self.render(
            'cart/history.html', **context
        )


class ProcessorView(View):
    methods = ['GET', 'POST']

    def get_processor(self, identifier):
        return Processor.get_instance_by_identifier(identifier)


class NotificationView(ProcessorView):
    def dispatch_request(self, identifier):
        processor = self.get_processor(identifier)
        return processor.notification()


class ConfirmationView(ProcessorView):
    def dispatch_request(self, identifier):
        processor = self.get_processor(identifier)
        return processor.confirmation()
