"""Keep products.search_vector in step with the data it indexes.

The vector covers the product's own name/description plus its subcategory,
category and variant names, so a change to any of those has to refresh it.
"""

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Category, Product, ProductVariant, Subcategory


def _refresh(product):
    """Refresh after the surrounding transaction commits, so the row we read
    back is the committed one (and nothing runs during a rolled-back save)."""
    transaction.on_commit(product.update_search_vector)


@receiver(post_save, sender=Product)
def product_saved(sender, instance, **kwargs):
    _refresh(instance)


@receiver([post_save, post_delete], sender=ProductVariant)
def variant_changed(sender, instance, **kwargs):
    _refresh(instance.product)


@receiver(post_save, sender=Subcategory)
def subcategory_renamed(sender, instance, **kwargs):
    for product in instance.products.select_related(
        "subcategory", "subcategory__category"
    ).prefetch_related("variants"):
        _refresh(product)


@receiver(post_save, sender=Category)
def category_renamed(sender, instance, **kwargs):
    products = Product.objects.filter(subcategory__category=instance).select_related(
        "subcategory", "subcategory__category"
    ).prefetch_related("variants")
    for product in products:
        _refresh(product)
