# coding: utf-8

from flask.ext.script import Command, Option
from .models import Cart


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
            print(cart)  # noqa
