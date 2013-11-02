# coding: utf-8


class BaseProcessor(object):
    def __init__(self, cart, *args, **kwargs):
        self.cart = cart

    def validate(self, *args, **kwargs):
        raise NotImplementedError()

    def process(self, *args, **kwargs):
        raise NotImplementedError()
