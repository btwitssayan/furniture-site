"""Load the catalogue content that was hardcoded into the static pages.

Run with:  python manage.py seed_data
Pass --reset to wipe the catalogue tables first.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from catalog.models import (
    Category,
    Collection,
    CollectionProduct,
    Product,
    ProductImage,
    ProductReview,
    ProductVariant,
    Subcategory,
)

U = "https://images.unsplash.com/photo-{}?q=80&w={}&auto=format&fit=crop"


def img(photo_id, width=700):
    return U.format(photo_id, width)


# (name, slug, banner photo id, [subcategory names])
CATEGORIES = [
    ("Sofas", "sofas", "1493663284031-b7e3aefcae8e", ["3-Seater", "2-Seater", "Sectional", "Recliner"]),
    ("Beds", "beds", "1505693416388-ac5ce068fe85", ["King", "Queen", "Platform", "Storage"]),
    ("Dining", "dining", "1617104551722-3b2d51366400", ["Dining Tables", "Dining Chairs", "Sideboards"]),
    ("Chairs", "chairs", "1592078615290-033ee584e267", ["Lounge", "Accent", "Dining"]),
    ("Tables", "tables", "1533090161767-e6ffed986c88", ["Coffee Tables", "Side Tables", "Console"]),
    ("Wardrobes", "wardrobes", "1595428774223-ef52624120d2", ["Two-Door", "Three-Door", "Sliding"]),
    ("Office", "office", "1518455027359-f3f8164ba6bd", ["Desks", "Office Chairs", "Storage"]),
    ("Decor", "decor", "1524758631624-e2822e304c36", ["Lighting", "Rugs", "Mirrors"]),
]

# name, category slug, subcategory slug, price, compare_at, featured,
# warranty, [image photo ids], [variant names], description
PRODUCTS = [
    (
        "Nordic Lounge Chair", "chairs", "lounge", "14999", "19999", True, 5,
        ["1540574163026-643ea20ade25", "1506898667547-42e22a46e125", "1567016432779-094069958ea5"],
        ["Natural Ash", "Walnut Stain", "Ebony Black"],
        "Solid ash-wood frame with a hand-upholstered boucle seat. The Nordic Lounge Chair is "
        "built on a gently curved silhouette that supports the lower back through long reading "
        "sessions - finished by hand in our Pune workshop.",
    ),
    (
        "Oakwood Three-Seater Sofa", "sofas", "3-seater", "58499", None, True, 5,
        ["1555041469-a586c61ea9bc", "1567016376408-0226e4d0c1ea"],
        ["Natural Oak", "Walnut", "Charcoal"],
        "A generous three-seater on a solid oak frame, with feather-blend cushions that keep "
        "their shape season after season.",
    ),
    (
        "Solstice Dining Table", "dining", "dining-tables", "37800", "42000", True, 7,
        ["1615066390971-03e4e1c36ddf", "1617806118233-18e1de247200"],
        ["Natural Oak", "Smoked Oak"],
        "Seats six comfortably on a single-slab top with tapered legs and a hand-rubbed oil finish.",
    ),
    (
        "Alder Platform Bed", "beds", "platform", "64999", None, True, 10,
        ["1522708323590-d24dbb6b0267", "1505691938895-1758d7feb511"],
        ["Natural Alder", "Walnut"],
        "A low-profile platform bed with an upholstered headboard and a slatted base that needs "
        "no box spring.",
    ),
    (
        "Wishbone Accent Chair", "chairs", "accent", "11499", None, False, 3,
        ["1592078615290-033ee584e267", "1503602642458-232111445657"],
        ["Natural Ash", "Black Oak"],
        "A woven-cord seat on a steam-bent frame - light enough to move, sturdy enough to last.",
    ),
    (
        "Camden Three-Door Wardrobe", "wardrobes", "three-door", "49999", None, False, 7,
        ["1595428774223-ef52624120d2", "1616627782675-e5f4287a5f9c"],
        ["Natural Oak", "Ebony"],
        "Three full-height doors, an internal drawer bank and soft-close hinges throughout.",
    ),
    (
        "Foundry Writing Desk", "office", "desks", "22750", None, False, 5,
        ["1518455027359-f3f8164ba6bd", "1518444065439-e933c06ce9cd"],
        ["Natural Oak", "Blackened Steel"],
        "A compact writing desk with a cable channel and two shallow drawers sized for papers.",
    ),
    (
        "Ember Round Coffee Table", "tables", "coffee-tables", "13599", "15999", False, 5,
        ["1567016432779-094069958ea5", "1533090161767-e6ffed986c88"],
        ["Natural Oak", "Walnut"],
        "A round-top coffee table on a sculpted pedestal base, finished with a matte hard-wax oil.",
    ),
    (
        "Haven L-Shaped Sectional", "sofas", "sectional", "73600", "92000", False, 5,
        ["1567538096630-e0c55bd6374c", "1493663284031-b7e3aefcae8e"],
        ["Oatmeal Linen", "Slate Grey"],
        "A deep-seated corner sectional with a reversible chaise, so it fits either side of a room.",
    ),
    (
        "Linden Two-Seater Sofa", "sofas", "2-seater", "41250", None, False, 5,
        ["1550254478-ead40cc54513", "1550581190-9c1c48d21d6c"],
        ["Oatmeal Linen", "Forest Green"],
        "A tidy two-seater for smaller rooms, on tapered solid-wood legs.",
    ),
    (
        "Recline Wood-Frame Recliner", "sofas", "recliner", "67999", None, False, 5,
        ["1586023492125-27b2c045efd7", "1567016376408-0226e4d0c1ea"],
        ["Tan Leather", "Espresso"],
        "A manual recliner built into a solid wood frame - no bulky mechanism on show.",
    ),
    # --- one product minimum in every remaining subcategory, so no filter
    # --- chip on a category page ever lands on an empty grid.
    (
        "Rosewood King Bed", "beds", "king", "78999", "89999", False, 10,
        ["1505693416388-ac5ce068fe85", "1505691938895-1758d7feb511"],
        ["Rosewood", "Walnut"],
        "A full king frame in solid rosewood, with a tall panelled headboard and "
        "mortise-and-tenon joinery throughout.",
    ),
    (
        "Meadow Queen Bed", "beds", "queen", "52999", None, False, 7,
        ["1522708323590-d24dbb6b0267", "1616627782675-e5f4287a5f9c"],
        ["Natural Oak", "Sage"],
        "A softly rounded queen frame with an upholstered headboard, sized for smaller rooms.",
    ),
    (
        "Vault Storage Bed", "beds", "storage", "69999", "79999", False, 7,
        ["1505691938895-1758d7feb511", "1522708323590-d24dbb6b0267"],
        ["Natural Oak", "Charcoal"],
        "Four deep drawers built into the base, on full-extension runners rated to 40kg each.",
    ),
    (
        "Nord Dining Chair", "dining", "dining-chairs", "8499", None, False, 3,
        ["1592078615290-033ee584e267", "1503602642458-232111445657"],
        ["Natural Ash", "Walnut Stain"],
        "A stackable solid-ash dining chair with a contoured seat. Sold individually.",
    ),
    (
        "Larch Sideboard", "dining", "sideboards", "34500", None, False, 7,
        ["1616627782675-e5f4287a5f9c", "1595428774223-ef52624120d2"],
        ["Natural Larch", "Smoked Oak"],
        "Two cupboards and a central drawer bank, sized to sit beneath a wall-hung mirror.",
    ),
    (
        "Spindle Dining Chair", "chairs", "dining", "9250", None, False, 3,
        ["1503602642458-232111445657", "1592078615290-033ee584e267"],
        ["Natural Ash", "Ebony Black"],
        "A turned-spindle back on a solid seat - the classic kitchen chair, properly made.",
    ),
    (
        "Pebble Side Table", "tables", "side-tables", "6999", "8499", False, 5,
        ["1533090161767-e6ffed986c88", "1567016432779-094069958ea5"],
        ["Natural Oak", "Walnut"],
        "A small rounded side table that tucks under the arm of a sofa.",
    ),
    (
        "Halden Console Table", "tables", "console", "18999", None, False, 5,
        ["1567016432779-094069958ea5", "1533090161767-e6ffed986c88"],
        ["Natural Oak", "Blackened Steel"],
        "A narrow hallway console with a lower shelf, only 32cm deep.",
    ),
    (
        "Aspen Two-Door Wardrobe", "wardrobes", "two-door", "36999", None, False, 7,
        ["1616627782675-e5f4287a5f9c", "1595428774223-ef52624120d2"],
        ["Natural Oak", "Ivory"],
        "A two-door wardrobe with a full-width hanging rail and one adjustable shelf.",
    ),
    (
        "Glide Sliding Wardrobe", "wardrobes", "sliding", "58999", "64999", False, 7,
        ["1595428774223-ef52624120d2", "1616627782675-e5f4287a5f9c"],
        ["Natural Oak", "Mirrored"],
        "Soft-close sliding doors on a top-hung track, so nothing catches on the carpet.",
    ),
    (
        "Studio Task Chair", "office", "office-chairs", "16499", None, False, 5,
        ["1518444065439-e933c06ce9cd", "1518455027359-f3f8164ba6bd"],
        ["Natural Ash", "Charcoal"],
        "A height-adjustable task chair on a wooden shell, with a breathable woven back.",
    ),
    (
        "Archive Filing Cabinet", "office", "storage", "14250", None, False, 5,
        ["1518455027359-f3f8164ba6bd", "1518444065439-e933c06ce9cd"],
        ["Natural Oak", "Blackened Steel"],
        "Three lockable drawers sized for A4 suspension files, on a solid oak carcass.",
    ),
    (
        "Halo Arc Floor Lamp", "decor", "lighting", "12999", "15499", False, 2,
        ["1524758631624-e2822e304c36", "1616486338812-3dadae4b4ace"],
        ["Brass", "Matte Black"],
        "An arc floor lamp on a weighted wooden base, reaching over a sofa or reading chair.",
    ),
    (
        "Dune Handwoven Rug", "decor", "rugs", "18750", None, False, 3,
        ["1616486338812-3dadae4b4ace", "1631679706909-1844bbd07221"],
        ["Sand", "Charcoal"],
        "A flatweave wool rug, handwoven in Bhadohi. 170 x 240cm.",
    ),
    (
        "Arch Wall Mirror", "decor", "mirrors", "9999", None, False, 3,
        ["1631679706909-1844bbd07221", "1524758631624-e2822e304c36"],
        ["Natural Oak", "Walnut"],
        "An arched mirror in a solid wood frame, with concealed French-cleat mounting.",
    ),
]

COLLECTIONS = [
    (
        "The Earth Collection", "the-earth-collection", "1616486338812-3dadae4b4ace", True,
        "Reclaimed oak, hand-rubbed finishes and undyed linen - a collection built around what "
        "the earth already does best. Each piece is finished by hand in small batches.",
        ["nordic-lounge-chair", "oakwood-three-seater-sofa", "solstice-dining-table", "ember-round-coffee-table"],
    ),
    (
        "The Monochrome Line", "the-monochrome-line", "1618221195710-dd6b41faaea6", False,
        "Charred-oak finishes and matte black hardware for spaces that speak in a lower register.",
        ["camden-three-door-wardrobe", "foundry-writing-desk", "alder-platform-bed"],
    ),
    (
        "The Coastal Edit", "the-coastal-edit", "1631679706909-1844bbd07221", False,
        "Bleached ash and woven rattan pieces designed for rooms that live for sunlight.",
        ["wishbone-accent-chair", "linden-two-seater-sofa", "haven-l-shaped-sectional"],
    ),
]

REVIEWS = {
    "nordic-lounge-chair": [
        (5, "Exactly as pictured. The ash grain is beautiful and it is genuinely comfortable."),
        (5, "Took ten minutes to assemble and has not creaked once in six months."),
        (4, "Lovely chair, though the walnut finish is a touch darker than the photos."),
    ],
    "oakwood-three-seater-sofa": [
        (5, "Worth every rupee. The cushions have held their shape perfectly."),
        (5, "Delivery team assembled it in the room. Excellent service."),
    ],
    "solstice-dining-table": [
        (4, "Solid table, seats six easily. Shipping took a little longer than promised."),
        (5, "The single-slab top is stunning under a pendant light."),
    ],
    "alder-platform-bed": [(5, "No box spring needed and no midnight creaking. Great buy.")],
    "ember-round-coffee-table": [(5, "The pedestal base means no knees hitting legs. Well designed.")],
}


class Command(BaseCommand):
    help = "Seed the catalogue with the content from the original static pages."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all catalogue rows before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            CollectionProduct.objects.all().delete()
            Collection.objects.all().delete()
            ProductReview.objects.all().delete()
            ProductVariant.objects.all().delete()
            ProductImage.objects.all().delete()
            Product.objects.all().delete()
            Subcategory.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write("Cleared existing catalogue.")

        subcategories = {}
        wanted_subs = set()
        for name, slug, photo, sub_names in CATEGORIES:
            category, _ = Category.objects.update_or_create(
                slug=slug, defaults={"name": name, "image_url": img(photo, 800)}
            )
            for sub_name in sub_names:
                sub_slug = slugify(sub_name)
                subcategory, _ = Subcategory.objects.update_or_create(
                    category=category, slug=sub_slug, defaults={"name": sub_name}
                )
                subcategories[(slug, sub_slug)] = subcategory
                wanted_subs.add(subcategory.pk)

        # Drop subcategories left behind by an earlier run of an older spec,
        # but only when nothing points at them (the FK is ON DELETE RESTRICT).
        stale = Subcategory.objects.exclude(pk__in=wanted_subs).filter(products__isnull=True)
        removed = stale.count()
        stale.delete()
        if removed:
            self.stdout.write(f"Removed {removed} stale empty subcategor(ies).")
        self.stdout.write(f"Categories: {Category.objects.count()}")

        for (
            name, cat_slug, sub_slug, price, compare, featured, warranty,
            photos, variants, description,
        ) in PRODUCTS:
            product, _ = Product.objects.update_or_create(
                slug=slugify(name),
                defaults={
                    "name": name,
                    "subcategory": subcategories[(cat_slug, sub_slug)],
                    "description": description,
                    "price": Decimal(price),
                    "compare_at_price": Decimal(compare) if compare else None,
                    "warranty_years": warranty,
                    "is_featured": featured,
                },
            )
            product.images.all().delete()
            for i, photo in enumerate(photos):
                ProductImage.objects.create(
                    product=product,
                    image_url=img(photo),
                    alt_text=name if i == 0 else f"{name} detail {i}",
                    sort_order=i,
                    is_primary=(i == 0),
                )
            product.variants.all().delete()
            for variant_name in variants:
                ProductVariant.objects.create(product=product, name=variant_name)

            product.reviews.all().delete()
            for rating, text in REVIEWS.get(product.slug, []):
                ProductReview.objects.create(
                    product=product, rating=rating, review_text=text
                )
            product.recalculate_rating()
        self.stdout.write(f"Products: {Product.objects.count()}")

        for name, slug, photo, featured, description, product_slugs in COLLECTIONS:
            collection, _ = Collection.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": description,
                    "image_url": img(photo, 1000),
                    "is_featured": featured,
                },
            )
            CollectionProduct.objects.filter(collection=collection).delete()
            for i, product_slug in enumerate(product_slugs):
                product = Product.objects.filter(slug=product_slug).first()
                if product:
                    CollectionProduct.objects.create(
                        collection=collection, product=product, sort_order=i
                    )
        self.stdout.write(f"Collections: {Collection.objects.count()}")

        self.stdout.write(self.style.SUCCESS("Seed complete."))
