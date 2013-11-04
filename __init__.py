# coding: utf-8

from quokka.core.app import QuokkaModule
module = QuokkaModule("cart", __name__,
                      template_folder="templates", static_folder="static")

from .views import CartView, SetItemView, RemoveItemView, SetProcessorView, \
    CheckoutView, HistoryView
module.add_url_rule('/cart/', view_func=CartView.as_view('cart'))
module.add_url_rule('/cart/setitem/', view_func=SetItemView.as_view('setitem'))
module.add_url_rule('/cart/removeitem/',
                    view_func=RemoveItemView.as_view('removeitem'))
module.add_url_rule('/cart/setprocessor/',
                    view_func=SetProcessorView.as_view('setprocessor'))
module.add_url_rule('/cart/checkout/',
                    view_func=CheckoutView.as_view('checkout'))
module.add_url_rule('/cart/history/', view_func=HistoryView.as_view('history'))

"""
Every url accepts ajax requests, and so do not redirect anything.
in ajax request it will return JSON as response
/cart
    - if there is a cart, but it is checked_out, create a new one
    - show a link to cart history if any
    - show the cart to the user
    - context is "cart"
    - renders cart/cart.html template
    - list items and has form for quantity and extra info
    - different things can be done via api ex: config shipping
/cart/setitem
    - receives a POST with item information
    - if "uid" is present ans item exists it will be updated else created
    - "product" reference is passed as an "id" and converted to a reference
    - receive quantity, weight etc..
    - if "next" is present redirect to there else redirect to "/cart"
/cart/removeitem
    - receives a POST with item_id or product_id
    - use 'next' to redirect or '/cart'
/cart/setprocessor
    - receives a POST with processor identifier or id
/cart/setstatus
    - user can set only from abandoned to pending
    - if there is a current 'pending' cart it will be set to 'abandoned'
    - admin can set to any status
/cart/configure
    - requires logged in user as cart owner
    - receive a POST
    - "property" can be shipping_data, sender_data, extra_costs, shipping_cost
/cart/checkout
   - if cart.requires_login:
       if user is not logged in it will redirect user to login page
   - Do the checkout process if the cart is "pending"
       else clean cart from session and redirect to history
   - if the processor has a pipeline in record or in class it will executed
       - record: pipeline
       - class: pre_pipeline, pos_pipeline
   - every method in pipeline  must act like a view
     and it will have self.cart, self.config and flask request and session
     to deal
   - they should return a redirect, a rendered template, or self.continue()
     which will continue to the next method in the pipeline and set state
     to jump to a specific method in pipeline you can do continue('method')
   - if None is returned or pipeline is empty/iterated,
     so the processor.process() method will be executed
/cart/history
   - show the cart history for the current user
   - context is carts
   - user must be logged in
"""
# module.add_url_rule('/cart/<slug>/', view_func=DetailView.as_view('detail'))
