"""Rebuild products.search_vector for the whole catalogue.

Run after a bulk import, after restoring a dump, or any time rows were written
in a way that bypassed the post_save signals (loaddata, bulk_update, raw SQL):

    python manage.py rebuild_search
"""

from django.core.management.base import BaseCommand

from catalog.models import Product


class Command(BaseCommand):
    help = "Recompute the Postgres full-text search vector for every product."

    def handle(self, *args, **options):
        products = Product.objects.select_related(
            "subcategory", "subcategory__category"
        ).prefetch_related("variants")

        count = 0
        for product in products:
            product.update_search_vector()
            count += 1

        missing = Product.objects.filter(search_vector__isnull=True).count()
        self.stdout.write(self.style.SUCCESS(f"Reindexed {count} product(s)."))
        if missing:
            self.stdout.write(
                self.style.WARNING(f"{missing} product(s) still have no vector.")
            )
