# coding: utf-8
from flask import session, request
from werkzeug.utils import import_string
from quokka.core.templates import render_template
from quokka.utils import get_current_user


class PipelineOverflow(Exception):
    pass


class CartPipeline(object):

    def __init__(self, cart, pipeline, index=0):
        self.cart = cart  # Cart object
        self.pipeline = pipeline   # pipeline ordered list []
        self.index = index  # current index in pipeline index
        self.update_args()

    def update_args(self):
        self.args = session.get('cart_pipeline_args', {})
        self.args.update(request.form.copy())
        session['cart_pipeline_args'] = self.args.copy()

    def del_sessions(self):
        if session.get('cart_pipeline_index'):
            del session['cart_pipeline_index']
        if session.get('cart_pipeline_args'):
            del session['cart_pipeline_args']

    def render(self, *args, **kwargs):
        return render_template(*args, **kwargs)

    def _preprocess(self):
        try:
            ret = self.process()  # the only overridable method
            if not ret:
                ret = self.go()
            if isinstance(ret, CartPipeline):
                session['cart_pipeline_index'] = ret.index
                return ret._preprocess()
            else:
                session['cart_pipeline_index'] = self.index
                return ret
        except PipelineOverflow as e:
            ret = self.cart.checkout()
            self.del_sessions()
            return ret
        except Exception as e:
            self.del_sessions()
            self.cart.addlog(
                u"{e} {p.index} {p} cart: {p.cart.id}".format(p=self, e=e)
            )
            return render_template('cart/pipeline_error.html',
                                   pipeline=self,
                                   error=e)

    def process(self):
        return NotImplementedError("Should be implemented")

    def go(self, index=None, name=None):
        index = index or self.index + 1
        try:
            pipeline = import_string(self.pipeline[index])
        except IndexError:
            raise PipelineOverflow("pipeline overflow at %s" % index)

        if not issubclass(pipeline, CartPipeline):
            raise ValueError("Pipelines should be subclass of CartPipeline")

        return pipeline(self.cart, self.pipeline, index)


class CartItemPipeline(CartPipeline):
    pass


class CartProcessorPipeline(CartPipeline):
    pass


class StartPipeline(CartPipeline):
    """
    This is the first pipeline executed upon cart checkout
    it only checks if user has email and name
    """
    def process(self):
        self.cart.addlog("StartPipeline")
        user = get_current_user()
        if not all([user.name, user.email]):
            confirm = request.form.get('cart_complete_information')

            name = request.form.get("name") or user.name or ""
            email = request.form.get("email") or user.email

            valid_name = len(name.split()) > 1

            if not confirm or not valid_name:
                return self.render('cart/complete_information.html',
                                   valid_name=valid_name,
                                   name=name)

            user.name = name
            user.email = email
            user.save()

        return self.go()


class TestPipeline(CartPipeline):
    def process(self):
        self.cart.addlog("TestPipeline")
        if not session.get('completed') == 3:
            session['completed'] = 3
            return render_template('cart/test.html', cart=self.cart)
        return self.go()
