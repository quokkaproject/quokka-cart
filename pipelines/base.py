# coding: utf-8
from flask import session, request
from werkzeug.utils import import_string
from quokka.core.templates import render_template


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
            Pipeline = import_string(self.pipeline[index])
        except IndexError:
            raise PipelineOverflow("Pipeline overflow at %s" % index)

        if not issubclass(Pipeline, CartPipeline):
            raise ValueError("Pipelines should be subclass of CartPipeline")

        return Pipeline(self.cart, self.pipeline, index)


class CartItemPipeline(CartPipeline):
    pass


class CartProcessorPipeline(CartPipeline):
    pass


class StartPipeline(CartPipeline):
    def process(self):
        self.cart.addlog("StartPipeline")
        return self.go()


class TestPipeline(CartPipeline):
    def process(self):
        self.cart.addlog("TestPipeline")
        if not session.get('completed') == 3:
            session['completed'] = 3
            # TODO: REnder a form here
            # should use self.args to deal with forms
            return render_template('cart/test.html', cart=self.cart)
        return self.go()
