# coding: utf-8


class BaseProcessor(object):
    def __init__(self, cart, *args, **kwargs):
        self.cart = cart
        self.config = kwargs.get('config', {})
        self._record = kwargs.get('_record')

    def validate(self, *args, **kwargs):
        raise NotImplementedError()

    def process(self, *args, **kwargs):
        raise NotImplementedError()

    def notification(self):
        return "notification"

    def confirmation(self):
        return "confirmation"
