# Quokka Cart | Version 0.1.0dev

A Shopping cart for [Quokka CMS](http://www.quokkaproject.org)

<p align="center">
<img src="http://quokkaproject.org/images/cart_checkout.png" alt="quokka cart" />
</p>


Features
=============

### What Quokka-cart does:

- Generic shopping cart management (manages itenms, prices, quantities)
- Executes **pipelines** (functions to dinamycally configure the checkout)
- Executes a decoupled **processor** for checkout
- Expose urls for checkout, history and receive carrier notifications
- Expose simple API to manage the cart (/additem, /setitem, /removeitem etc..)

### What Quokka-cart does not:

- A complete e-commerce solution (for that take a look at Quokka-commerce which uses quokka-cart)


How to install
===============

Go to your quokka modules folder and clone it.

```bash
$ cd quokka/quokka/modules
$ git clone https://github.com/pythonhub/quokka-cart.git cart
$ ls
__init__.py accounts media posts cart ...
```

Now you have **cart** folder as a Quokka module, restart your server and it will be available in yout application and in admin under "Cart" menu.


Product
=======

Cart
====

Checkout Pipeline
========

Processor
=========


- http://github.com/pythonhub/quokka-cart  
-  by Bruno Rocha <rochacbruno@gmail.com>


[![Bitdeli Badge](https://d2weczhvl823v0.cloudfront.net/pythonhub/quokka-cart/trend.png)](https://bitdeli.com/free "Bitdeli Badge")

