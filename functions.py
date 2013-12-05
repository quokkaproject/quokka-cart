# coding: utf-8

from flask import session
from .models import Cart


def get_current_cart(*args, **kwargs):
    if session.get('cart_id'):
        return Cart.get_cart(*args, **kwargs)
