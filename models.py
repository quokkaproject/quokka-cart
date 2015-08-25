# coding: utf-8
import datetime
import logging
from werkzeug.utils import import_string
from flask import session, current_app
from quokka.utils.translation import _l
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

    def get_summary(self):
        summary = getattr(self, 'summary', None)
        if not summary:
            try:
                return self.get_description()[:255]
            except:
                pass
        return summary

    def get_extra_value(self):
        return getattr(self, 'extra_value', None)

    def get_uid(self):
        return str(self.id)

    def set_status(self, *args, **kwargs):
        pass

    def remove_item(self, *args, **kwargs):
        pass


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

    def set_status(self, status, *args, **kwargs):
        kwargs['item'] = self
        if self.reference and hasattr(self.reference, 'set_status'):
            self.reference.set_status(status, *args, **kwargs)
        if self.product and hasattr(self.product, 'set_status'):
            self.product.set_status(status, *args, **kwargs)

    def get_main_image_url(self, thumb=False, default=None):
        try:
            return self.product.get_main_image_url(thumb, default)
        except:
            return None

    @classmethod
    def normalize(cls, kwargs):
        new = {}
        for k, v in kwargs.items():
            field = cls._fields.get(k)
            if not field:
                continue
            new[k] = field.to_python(v)
        return new

    def __unicode__(self):
        return u"{i.title} - {i.total_value}".format(i=self)

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
    module = db.StringField(max_length=255)
    requires = db.ListField(db.StringField(max_length=255))
    description = db.StringField()
    title = db.StringField()
    image = db.ReferenceField(Image, reverse_delete_rule=db.NULLIFY)
    link = db.StringField(max_length=255)
    config = db.DictField(default=lambda: {})
    pipeline = db.ListField(db.StringField(max_length=255), default=[])

    def import_processor(self):
        return import_string(self.module)

    def get_instance(self, *args, **kwargs):
        if 'config' not in kwargs:
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
                'identifier': 'dummy',
                'published': True,
                'title': "Test"
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

    belongs_to = db.ReferenceField('User',
                                   # default=get_current_user,
                                   reverse_delete_rule=db.NULLIFY)
    items = db.ListField(db.EmbeddedDocumentField(Item))
    payment = db.ListField(db.EmbeddedDocumentField(Payment))
    status = db.StringField(choices=STATUS, default='pending')
    total = db.FloatField(default=0)
    extra_costs = db.DictField(default=lambda: {})
    sender_data = db.DictField(default=lambda: {})
    shipping_data = db.DictField(default=lambda: {})
    shipping_cost = db.FloatField(default=0)
    tax = db.FloatField(default=0)
    processor = db.ReferenceField(Processor,
                                  default=Processor.get_default_processor,
                                  reverse_delete_rule=db.NULLIFY)
    reference_code = db.StringField()  # Reference code for filtering
    checkout_code = db.StringField()  # The UID for transaction checkout
    transaction_code = db.StringField()  # The UID for transaction
    requires_login = db.BooleanField(default=True)
    continue_shopping_url = db.StringField(
        default=lambda: current_app.config.get(
            'CART_CONTINUE_SHOPPING_URL', '/'
        )
    )
    pipeline = db.ListField(db.StringField(), default=[])
    log = db.ListField(db.StringField(), default=[])
    config = db.DictField(default=lambda: {})

    search_helper = db.StringField()

    meta = {
        'ordering': ['-created_at']
    }

    def send_response(self, response, identifier):
        if self.reference and hasattr(self.reference, 'get_response'):
            self.reference.get_response(response, identifier)

        for item in self.items:
            if hasattr(item, 'get_response'):
                item.get_response(response, identifier)

    def set_tax(self, tax, save=False):
        """
        set tax and send to references
        """
        try:
            tax = float(tax)
            self.tax = tax
            self.set_reference_tax(tax)
        except Exception as e:
            self.addlog("impossible to set tax: %s" % str(e))

    def set_status(self, status, save=False):
        """
        THis method will be called by the processor
        which will pass a valid status as in STATUS
        so, this method will dispatch the STATUS to
        all the items and also the 'reference' if set
        """
        if self.status != status:
            self.status = status

        self.set_reference_statuses(status)

        if save:
            self.save()

    def set_reference_statuses(self, status):
        if self.reference and hasattr(self.reference, 'set_status'):
            self.reference.set_status(status, cart=self)

        for item in self.items:
            item.set_status(status, cart=self)

    def set_reference_tax(self, tax):
        if self.reference and hasattr(self.reference, 'set_tax'):
            self.reference.set_tax(tax)

        for item in self.items:
            if hasattr(item, 'set_tax'):
                item.set_tax(tax)

    def addlog(self, msg, save=True):
        try:
            self.log.append(u"{0},{1}".format(datetime.datetime.now(), msg))
            logger.debug(msg)
            save and self.save()
        except UnicodeDecodeError as e:
            logger.info(msg)
            logger.error(str(e))

    @property
    def uid(self):
        return self.get_uid()

    def get_uid(self):
        try:
            return self.reference.get_uid() or str(self.id)
        except Exception:
            self.addlog("Using self.id as reference", save=False)
            return str(self.id)

    def __unicode__(self):
        return u"{o.uid} - {o.processor.identifier}".format(o=self)

    def get_extra_costs(self):
        if self.extra_costs:
            return sum(self.extra_costs.values())

    @classmethod
    def get_cart(cls, no_dereference=False, save=True):
        """
        get or create a new cart related to the session
        if there is a current logged in user it will be set
        else it will be set during the checkout.
        """
        session.permanent = current_app.config.get(
            "CART_PERMANENT_SESSION", True)
        try:
            cart = cls.objects(id=session.get('cart_id'), status='pending')

            if not cart:
                raise cls.DoesNotExist('A pending cart not found')

            if no_dereference:
                cart = cart.no_dereference()

            cart = cart.first()

            save and cart.save()

        except (cls.DoesNotExist, db.ValidationError):
            cart = cls(status="pending")
            cart.save()
            session['cart_id'] = str(cart.id)
            session.pop('cart_pipeline_index', None)
            session.pop('cart_pipeline_args', None)

        return cart

    def assign(self):
        self.belongs_to = self.belongs_to or get_current_user()

    def save(self, *args, **kwargs):
        self.total = sum([item.total for item in self.items])
        self.assign()
        self.reference_code = self.get_uid()
        self.search_helper = self.get_search_helper()
        if not self.id:
            self.published = True
        super(Cart, self).save(*args, **kwargs)
        self.set_reference_statuses(self.status)

    def get_search_helper(self):
        if not self.belongs_to:
            return ""
        user = self.belongs_to
        return " ".join([
            user.name or "",
            user.email or ""
        ])

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
            self.addlog("Cannot add item without an uid %s" % kwargs)
            return

        item = self.get_item(uid)

        kwargs = Item.normalize(kwargs)

        if not item:
            # items should only be added if there is a product (for safety)
            if not kwargs.get('product'):
                self.addlog("there is no product to add item")
                return
            allowed = ['product', 'quantity']
            item = self.items.create(
                **{k: v for k, v in kwargs.items() if k in allowed}
            )
            self.addlog("New item created %s" % item, save=False)
        else:
            # update only allowed attributes
            item = self.items.update(
                {k: v for k, v in kwargs.items() if k in item.allowed_to_set},
                uid=item.uid
            )
            self.addlog("Item updated %s" % item, save=False)

            if int(kwargs.get('quantity', "1")) == 0:
                self.addlog("quantity is 0, removed %s" % kwargs, save=False)
                self.remove_item(**kwargs)

        self.save()
        self.reload()
        return item

    def remove_item(self, **kwargs):
        deleted = self.items.delete(**kwargs)
        print self.reference
        if self.reference and hasattr(self.reference, 'remove_item'):
            self.reference.remove_item(**kwargs)
            print self.reference
        return deleted

    def checkout(self, processor=None, *args, **kwargs):
        self.set_processor(processor)
        processor_instance = self.processor.get_instance(self, *args, **kwargs)
        if processor_instance.validate():
            response = processor_instance.process()
            self.status = 'checked_out'
            self.save()
            session.pop('cart_id', None)
            return response
        else:
            self.addlog("Cart did not validate")
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
