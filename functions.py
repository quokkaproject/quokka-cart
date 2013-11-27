# coding: utf-8

from flask import session
from .models import Cart


def get_current_cart():
    if session.get('cart_id'):
        return Cart.get_cart()
