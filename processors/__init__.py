# coding: utf-8
import logging
from .base import BaseProcessor
from quokka.core.templates import render_template

logger = logging.getLogger()


class Dummy(BaseProcessor):
    def validate(self, *args, **kwargs):
        items = self.cart.items
        logger.info(items)
        return True

    def process(self, *args, **kwargs):
        logger.info("Cheking out %s" % self.cart.id)
        self.cart.addlog("Dummy processor %s" % self.cart.id)
        return render_template('cart/dummy.html', cart=self.cart)
