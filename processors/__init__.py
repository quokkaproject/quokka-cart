#coding: utf-8
import logging
from .base import BaseProcessor

logger = logging.getLogger()


class Dummy(BaseProcessor):
    def validate(self, *args, **kwargs):
        items = self.cart.items
        logger.info(items)
        return True

    def process(self, *args, **kwargs):
        logger.info("Cheking out %s" % self.cart.id)
