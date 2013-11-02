# coding: utf-8

from quokka.core.app import QuokkaModule
module = QuokkaModule("cart", __name__,
                      template_folder="templates", static_folder="static")

from .views import CartView
module.add_url_rule('/cart/', view_func=CartView.as_view('cart'))
# module.add_url_rule('/cart/<slug>/', view_func=DetailView.as_view('detail'))
