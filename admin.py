# coding : utf -8
# from flask.ext.htmlbuilder import html
# from flask.ext.admin.babel import lazy_gettext
from quokka import admin
from quokka.modules.posts.admin import PostAdmin
from quokka.core.admin.models import ModelAdmin
from quokka.utils.translation import _, _l
from quokka.core.widgets import TextEditor, PrepopulatedText
from .models import Cart, Processor


class ProductAdmin(PostAdmin):
    column_list = ('title', 'slug', 'channel',
                   'unity_value', 'weight',
                   'published', 'created_at',
                   'available_at', 'view_on_site')
    column_searchable_list = ['title', 'summary', 'description']
    form_columns = [
        'title', 'slug', 'channel', 'related_channels', 'summary',
        'description', 'unity_value', 'weight', 'dimensions', 'extra_value',
        'published', 'show_on_channel',
        'available_at', 'available_until',
        'tags', 'contents', 'values', 'template_type'
    ]
    form_widget_args = {
        'description': {
            'rows': 20,
            'cols': 20,
            'class': 'text_editor',
            'style': "margin: 0px; width: 725px; height: 360px;"
        },
        'summary': {
            'style': 'width: 400px; height: 100px;'
        },
        'title': {'style': 'width: 400px'},
        'slug': {'style': 'width: 400px'},
    }


class CartAdmin(ModelAdmin):
    roles_accepted = ('admin', 'editor')
    column_filters = ('status', 'created_at', 'total', 'tax',
                      'reference_code', 'transaction_code')
    column_searchable_list = ('transaction_code', 'checkout_code',
                              'reference_code', 'search_helper')
    column_list = ("belongs_to", 'total', 'tax', 'status', 'created_at',
                   'processor',
                   "reference_code", 'items', 'published')
    form_columns = ('created_at', 'belongs_to', 'processor', 'status',
                    'total', 'extra_costs', 'reference_code', 'checkout_code',
                    'sender_data', 'shipping_data', 'tax', 'shipping_cost',
                    'transaction_code',
                    # 'requires_login',
                    # 'continue_shopping_url', 'pipeline', 'config',
                    # 'items',
                    'payment', 'published')

    form_subdocuments = {
        'items': {
            'form_subdocuments': {
                None: {
                    'form_columns': ['uid', 'title', 'description',
                                     'link', 'quantity', 'unity_value',
                                     'total_value', 'weight', 'dimensions',
                                     'extra_value']
                }
            }
        }
    }

    column_formatters = {
        'created_at': ModelAdmin.formatters.get('datetime'),
        'available_at': ModelAdmin.formatters.get('datetime'),
        'items': ModelAdmin.formatters.get('ul'),
        'status': ModelAdmin.formatters.get('status'),
        'reference_code': ModelAdmin.formatters.get('get_url')
    }

    column_formatters_args = {
        'ul': {
            'items': {
                'placeholder': u"{item.title} - {item.total_value}",
                'style': "min-width:200px;max-width:300px;"
            }
        },
        'status': {
            'status': {
                'labels': {
                    'confirmed': 'success',
                    'checked_out': 'warning',
                    'cancelled': 'important',
                    'completed': 'success'
                },
                'style': 'min-height:18px;'
            }
        },
        'get_url': {
            'reference_code': {
                'attribute': 'reference',
                'method': 'get_admin_url'
            }
        }
    }

    def after_model_change(self, form, model, is_created):
        if not is_created and model.reference:
            model.reference.published = model.published
            if model.tax:
                model.set_reference_tax(float(model.tax))
            model.reference.save()


class ProcessorAdmin(ModelAdmin):
    roles_accepted = ('admin', 'developer')
    column_list = ('identifier', 'title', 'module', 'published')
    form_args = {
        "description": {"widget": TextEditor()},
        "identifier": {"widget": PrepopulatedText(master='title')}
    }
    form_columns = ('title', 'identifier', 'description', 'module',
                    'requires', 'image', 'link', 'config', 'pipeline',
                    'published')
    form_ajax_refs = {
        'image': {'fields': ['title', 'long_slug', 'summary']}
    }

    form_widget_args = {
        'config': {'cols': 40, 'rows': 10, 'style': 'width:500px;'}
    }

admin.register(Cart, CartAdmin, category=_("Cart"), name=_l("Cart"))
admin.register(Processor, ProcessorAdmin, category=_("Cart"),
               name=_l("Processor"))
