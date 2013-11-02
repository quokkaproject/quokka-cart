#coding: utf-8

from .base import BaseProcessor


class Dummy(BaseProcessor):
    def validate(self, *args, **kwargs):
        items = self.cart.items
        print(items)

    def process(self, *args, **kwargs):
        print("Cheking out %s" % self.cart.id)
