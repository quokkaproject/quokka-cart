# coding: utf-8


class BaseProcessor(object):
    def __init__(self, cart, *args, **kwargs):
        self.cart = cart

    def validate(self, *args, **kwargs):
        raise NotImplementedError()

    def process(self, *args, **kwargs):
        raise NotImplementedError()


class Dummy(BaseProcessor):
    def validate(self, *args, **kwargs):
        items = self.cart.items
        print(items)

    def process(self, *args, **kwargs):
        print("Cheking out %s" % self.cart.id)
