# coding: utf-8

import logging

from flask.ext.script import Command, Option
from .models import Cart


logger = logging.getLogger(__name__)


class ListCart(Command):
    "prints a list of carts"

    command_name = 'list_carts'

    option_list = (
        Option('--title', '-t', dest='title'),
    )

    def run(self, title=None):

        carts = Cart.objects
        if title:
            carts = carts(title=title)

        for cart in carts:
            logger.info('Cart: {}'.format(cart))
