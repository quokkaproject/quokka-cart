# coding: utf-8
import datetime
import logging
from werkzeug.utils import import_string
from flask import session, current_app
from flask.ext.babel import lazy_gettext as _l
from quokka.utils import get_current_user, lazy_str_setting
from quokka.core.templates import render_template
from quokka.core.db import db
from quokka.core.models import Publishable, Ordered, Dated, Content
from quokka.modules.media.models import Image

logger = logging.getLogger()


class BaseProductReference(object):
    def get_title(self):
        return getattr(self, 'title', None)

    def get_description(self):
        return getattr(self, 'description', None)

    def get_unity_value(self):
        return getattr(self, 'unity_value', None)

    def get_weight(self):
        return getattr(self, 'weight', None)

    def get_dimensions(self):
        return getattr(self, 'dimensions', None)

    def get_extra_value(self):
        return getattr(self, 'extra_value', None)

    def get_uid(self):
        return str(self.id)


class BaseProduct(BaseProductReference, Content):
    description = db.StringField(required=True)
    unity_value = db.FloatField()
    weight = db.FloatField()
    dimensions = db.StringField()
    extra_value = db.FloatField()

    meta = {
        'allow_inheritance': True
    }


class Item(Ordered, Dated, db.EmbeddedDocument):
    product = db.ReferenceField(Content)
    reference = db.GenericReferenceField()  # customized product
    """
    Must implement all the BaseProduct methods/ its optional
    if None, "product" will be considered
    """
    uid = db.StringField()
    title = db.StringField(required=True, max_length=255)
    description = db.StringField(required=True)
    link = db.StringField()
    quantity = db.FloatField(default=1)
    unity_value = db.FloatField(required=True)
    total_value = db.FloatField()
    weight = db.FloatField()
    dimensions = db.StringField()
    extra_value = db.FloatField()
    allowed_to_set = db.ListField(db.StringField(), default=['quantity'])
    pipeline = db.ListField(db.StringField(), default=[])

    @classmethod
    def normalize(cls, kwargs):
        new = {}
        for k, v in kwargs.items():
            field = cls._fields[k]
            new[k] = field.to_python(v)
        return new

    def __unicode__(self):
        return u"{i.uid} {i.title}".format(i=self)

    def get_uid(self):
        try:
            return self.product.get_uid()
        except:
            return self.uid

    @property
    def unity_plus_extra(self):
        return float(self.unity_value or 0) + float(self.extra_value or 0)

    @property
    def total(self):
        self.clean()
        self.total_value = self.unity_plus_extra * float(self.quantity or 1)
        return self.total_value

    def clean(self):
        mapping = [
            ('title', 'get_title'),
            ('description', 'get_description'),
            ('link', 'get_absolute_url'),
            ('unity_value', 'get_unity_value'),
            ('weight', 'get_weight'),
            ('dimensions', 'get_dimensions'),
            ('extra_value', 'get_extra_value'),
            ('uid', 'get_uid'),
        ]

        references = [self.reference, self.product]

        for ref in references:
            if not ref:
                continue
            for attr, method in mapping:
                current = getattr(self, attr, None)
                if current is not None:
                    continue
                setattr(self, attr, getattr(ref, method, lambda: None)())


class Payment(db.EmbeddedDocument):
    uid = db.StringField()
    payment_system = db.StringField()
    method = db.StringField()
    value = db.FloatField()
    extra_value = db.FloatField()
    date = db.DateTimeField()
    confirmed_at = db.DateTimeField()
    status = db.StringField()


class Processor(Publishable, db.DynamicDocument):
    identifier = db.StringField(max_length=100, unique=True)
    module = db.StringField()
    requires = db.ListField(db.StringField())
    description = db.StringField()
    title = db.StringField()
    image = db.ReferenceField(Image)
    link = db.StringField()
    config = db.DictField(default=lambda: {})
    pipeline = db.ListField(db.StringField(), default=[])

    def import_processor(self):
        return import_string(self.module)

    def get_instance(self, *args, **kwargs):
        if not 'config' in kwargs:
            kwargs['config'] = self.config
        kwargs['_record'] = self
        return self.import_processor()(*args, **kwargs)

    def clean(self, *args, **kwargs):
        for item in (self.requires or []):
            import_string(item)
        super(Processor, self).clean(*args, **kwargs)

    def __unicode__(self):
        return self.identifier

    @classmethod
    def get_instance_by_identifier(cls, identifier, cart=None):
        processor = cls.objects.get(identifier=identifier)
        return processor.get_instance(cart=cart)

    @classmethod
    def get_default_processor(cls):
        default = lazy_str_setting(
            'CART_DEFAULT_PROCESSOR',
            default={
                'module': 'quokka.modules.cart.processors.Dummy',
                'identifier': 'dummy'
            }
        )

        try:
            return cls.objects.get(identifier=default['identifier'])
        except:
            return cls.objects.create(**default)

    def save(self, *args, **kwargs):
        self.import_processor()
        super(Processor, self).save(*args, **kwargs)


class Cart(Publishable, db.DynamicDocument):
    STATUS = (
        ("pending", _l("Pending")),  # not checked out
        ("checked_out", _l("Checked out")),  # not confirmed (payment)
        ("analysing", _l("Analysing")),  # Analysing payment
        ("confirmed", _l("Confirmed")),  # Payment confirmed
        ("completed", _l("Completed")),  # Payment completed (money released)
        ("refunding", _l("Refunding")),  # Buyer asks refund
        ("refunded", _l("Refunded")),  # Money refunded to buyer
        ("cancelled", _l("Cancelled")),  # Cancelled without processing
        ("abandoned", _l("Abandoned")),  # Long time no update
    )
    reference = db.GenericReferenceField()
    """reference must implement set_status(**kwargs) method
    arguments: status(str), value(float), date, uid(str), msg(str)
    and extra(dict).
    Also reference must implement get_uid() which will return
    the unique identifier for this transaction"""

    belongs_to = db.ReferenceField('User', default=get_current_user)
    items = db.ListField(db.EmbeddedDocumentField(Item))
    payment = db.ListField(db.EmbeddedDocumentField(Payment))
    status = db.StringField(choices=STATUS, default='pending')
    total = db.FloatField(default=0)
    extra_costs = db.DictField(default=lambda: {})
    sender_data = db.DictField(default=lambda: {})
    shipping_data = db.DictField(default=lambda: {})
    shippping_cost = db.FloatField(default=0)
    processor = db.ReferenceField(Processor,
                                  required=True,
                                  default=Processor.get_default_processor)
    reference_code = db.StringField()  # Reference code for filtering
    checkout_code = db.StringField()  # The UID for transaction checkout
    transaction_code = db.StringField()  # The UID for transaction
    requires_login = db.BooleanField(default=True)
    continue_shopping_url = db.StringField(default="/")
    pipeline = db.ListField(db.StringField(), default=[])
    log = db.ListField(db.StringField(), default=[])
    config = db.DictField(default=lambda: {})

    def addlog(self, msg, save=True):
        self.log.append(u"{0},{1}".format(datetime.datetime.now(), msg))
        logger.debug(msg)
        save and self.save()

    @property
    def uid(self):
        return self.get_uid()

    def get_uid(self):
        try:
            return self.reference.get_uid() or str(self.id)
        except:
            return str(self.id)

    def __unicode__(self):
        return u"{o.uid} - {o.processor.identifier}".format(o=self)

    def get_extra_costs(self):
        if self.extra_costs:
            return sum(self.extra_costs.values())

    @classmethod
    def get_cart(cls):
        """
        get or create a new cart related to the session
        if there is a current logged in user it will be set
        else it will be set during the checkout.
        """
        session.permanent = current_app.config.get(
            "CART_PERMANENT_SESSION", True)
        try:
            cart = cls.objects.get(
                id=session.get('cart_id'),
                status='pending'
            )
            cart.save()
        except (cls.DoesNotExist, db.ValidationError):
            cart = cls(status="pending")
            cart.save()
            session['cart_id'] = str(cart.id)
        return cart

    def assign(self):
        self.belongs_to = self.belongs_to or get_current_user()

    def save(self, *args, **kwargs):
        self.total = sum([item.total for item in self.items])
        self.assign()
        super(Cart, self).save(*args, **kwargs)
        if not self.reference_code:
            self.reference_code = self.get_uid()
            self.save()

    def get_item(self, uid):
        # MongoEngine/mongoengine#503
        return self.items.get(uid=uid)

    def set_item(self, **kwargs):
        if 'product' in kwargs:
            if not isinstance(kwargs['product'], Content):
                try:
                    kwargs['product'] = Content.objects.get(
                        id=kwargs['product'])
                except Content.DoesNotExist:
                    kwargs['product'] = None

        uid = kwargs.get(
            'uid',
            kwargs['product'].get_uid() if kwargs.get('product') else None
        )

        if not uid:
            logger.warning("Cannot add item without an uid %s" % kwargs)
            return

        item = self.get_item(uid)

        kwargs = Item.normalize(kwargs)

        if not item:
            # items should only be added if there is a product (for safety)
            if not kwargs.get('product'):
                return
            allowed = ['product', 'quantity']
            item = self.items.create(
                **{k: v for k, v in kwargs.items() if k in allowed}
            )
        else:
            # update only allowed attributes
            item = self.items.update(
                {k: v for k, v in kwargs.items() if k in item.allowed_to_set},
                uid=item.uid
            )

            if int(kwargs.get('quantity', "1")) == 0:
                self.remove_item(**kwargs)

        self.save()
        self.reload()
        return item

    def remove_item(self, **kwargs):
        return self.items.delete(**kwargs)

    def checkout(self, processor=None, *args, **kwargs):
        self.set_processor(processor)
        processor_instance = self.processor.get_instance(self, *args, **kwargs)
        if processor_instance.validate():
            return processor_instance.process()
        else:
            raise Exception("Cart did not validate")  # todo: specialize this

    def get_items_pipeline(self):
        if not self.items:
            return []

        return reduce(
            lambda x, y: x + y, [item.pipeline for item in self.items]
        )

    def build_pipeline(self):
        items = ['quokka.modules.cart.pipelines:StartPipeline']
        items.extend(current_app.config.get('CART_PIPELINE', []))
        items.extend(self.get_items_pipeline())
        items.extend(self.pipeline)
        items.extend(self.processor and self.processor.pipeline or [])
        return items

    def process_pipeline(self):
        if not self.items:
            return render_template('cart/empty_cart.html',
                                   url=self.continue_shopping_url)

        pipelines = self.build_pipeline()
        index = session.get('cart_pipeline_index', 0)
        Pipeline = import_string(pipelines[index])
        return Pipeline(self, pipelines, index)._preprocess()

    def set_processor(self, processor=None):
        if not self.processor:
            self.processor = Processor.get_default_processor()
            self.save()

        if not processor:
            return

        if isinstance(processor, Processor):
            self.processor = processor
            self.save()
            return

        try:
            self.processor = Processor.objects.get(id=processor)
        except:
            self.processor = Processor.objects.get(identifier=processor)

        self.save()

    def get_available_processors(self):
        return Processor.objects(published=True)
