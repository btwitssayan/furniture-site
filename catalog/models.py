"""Models mirroring schema.sql one-for-one.

Table names, columns, nullability, defaults and CHECK constraints follow the
SQL file exactly. Django manages the tables via migrations, so the SQLite
column affinities differ slightly from the DDL (BooleanField -> `bool`,
DateTimeField -> `datetime` rather than INTEGER/TEXT), which SQLite treats
identically at runtime.
"""

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.db import models
from django.db.models import Value


class Category(models.Model):
    """Top-level shop categories: Sofas, Beds, Dining, etc."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    image_url = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "categories"
        verbose_name_plural = "categories"
        ordering = ["id"]

    def __str__(self):
        return self.name


class Subcategory(models.Model):
    """Category-specific filters such as 3-Seater, Sectional, Recliner."""

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="subcategories",
        db_column="category_id",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "subcategories"
        verbose_name_plural = "subcategories"
        ordering = ["category_id", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "slug"], name="uq_subcategory_category_slug"
            )
        ]

    def __str__(self):
        return f"{self.category.name} / {self.name}"


class Product(models.Model):
    """Main product catalogue table."""

    subcategory = models.ForeignKey(
        Subcategory,
        on_delete=models.PROTECT,
        related_name="products",
        db_column="subcategory_id",
    )

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)

    price = models.DecimalField(max_digits=12, decimal_places=2)
    compare_at_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Original price, shown struck through. Leave blank if not on sale.",
    )

    warranty_years = models.IntegerField(blank=True, null=True)

    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        help_text="Recalculated automatically from reviews.",
    )
    review_count = models.IntegerField(
        default=0, help_text="Recalculated automatically from reviews."
    )

    is_featured = models.BooleanField(
        default=False,
        help_text="Featured products appear in Bestsellers on the home page.",
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Postgres full-text search index. Populated by update_search_vector()
    # below, which the post_save signal in signals.py calls on every write.
    search_vector = SearchVectorField(null=True, editable=False)

    class Meta:
        db_table = "products"
        ordering = ["-is_featured", "id"]
        indexes = [
            models.Index(fields=["is_active"], name="idx_products_active"),
            models.Index(fields=["is_featured"], name="idx_products_featured"),
            GinIndex(fields=["search_vector"], name="idx_products_search"),
            # Backs the pg_trgm typo fallback in catalog.views.search.
            GinIndex(
                fields=["name"],
                name="idx_products_name_trgm",
                opclasses=["gin_trgm_ops"],
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gte=0), name="ck_product_price"
            ),
            models.CheckConstraint(
                condition=models.Q(compare_at_price__isnull=True)
                | models.Q(compare_at_price__gte=0),
                name="ck_product_compare_at_price",
            ),
            models.CheckConstraint(
                condition=models.Q(warranty_years__isnull=True)
                | models.Q(warranty_years__gte=0),
                name="ck_product_warranty_years",
            ),
            models.CheckConstraint(
                condition=models.Q(rating__gte=0) & models.Q(rating__lte=5),
                name="ck_product_rating",
            ),
            models.CheckConstraint(
                condition=models.Q(review_count__gte=0), name="ck_product_review_count"
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def category(self):
        return self.subcategory.category

    @property
    def is_on_sale(self):
        return self.compare_at_price is not None and self.compare_at_price > self.price

    @property
    def discount_percent(self):
        """Whole-number discount, e.g. 25 for '25% OFF'. None when not on sale."""
        if not self.is_on_sale:
            return None
        return round((self.compare_at_price - self.price) / self.compare_at_price * 100)

    @property
    def primary_image(self):
        images = list(self.images.all())
        if not images:
            return None
        for image in images:
            if image.is_primary:
                return image
        return images[0]

    @property
    def secondary_image(self):
        """Second image, used for the hover swap on product cards."""
        primary = self.primary_image
        others = [i for i in self.images.all() if i.pk != (primary and primary.pk)]
        return others[0] if others else primary

    @property
    def full_stars(self):
        return range(int(self.rating))

    @property
    def empty_stars(self):
        return range(5 - int(self.rating))

    def update_search_vector(self):
        """Rebuild this product's tsvector.

        The related names (category, subcategory, variants) are resolved in
        Python and passed as literals, because Postgres UPDATE cannot join.
        Weights: A the product name, B the taxonomy and finishes, C the prose.
        """
        subcategory = self.subcategory
        variants = " ".join(v.name for v in self.variants.all())
        vector = (
            SearchVector(Value(self.name), weight="A", config="english")
            + SearchVector(Value(subcategory.name), weight="B", config="english")
            + SearchVector(Value(subcategory.category.name), weight="B", config="english")
            + SearchVector(Value(variants), weight="B", config="english")
            + SearchVector(Value(self.description or ""), weight="C", config="english")
        )
        Product.objects.filter(pk=self.pk).update(search_vector=vector)

    def recalculate_rating(self):
        """Refresh the denormalised rating/review_count from product_reviews."""
        agg = self.reviews.aggregate(avg=models.Avg("rating"), n=models.Count("id"))
        rating = round(agg["avg"] or 0, 2)
        count = agg["n"]
        Product.objects.filter(pk=self.pk).update(rating=rating, review_count=count)
        self.rating = rating
        self.review_count = count


class ProductImage(models.Model):
    """One product can have multiple images."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images", db_column="product_id"
    )
    image_url = models.TextField()
    alt_text = models.TextField(blank=True, null=True)
    sort_order = models.IntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "product_images"
        ordering = ["-is_primary", "sort_order", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(sort_order__gte=0), name="ck_image_sort_order"
            ),
        ]

    def __str__(self):
        return self.alt_text or f"Image {self.pk}"


class ProductVariant(models.Model):
    """Finishes such as Natural Ash, Walnut, Black Oak. Price may differ."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
        db_column="product_id",
    )
    name = models.CharField(max_length=120)
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Leave blank to use the product's own price.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "product_variants"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "name"], name="uq_variant_product_name"
            ),
            models.CheckConstraint(
                condition=models.Q(price__isnull=True) | models.Q(price__gte=0),
                name="ck_variant_price",
            ),
        ]

    def __str__(self):
        return self.name


class ProductReview(models.Model):
    """Individual customer reviews."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
        db_column="product_id",
    )
    rating = models.IntegerField()
    review_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "product_reviews"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name="ck_review_rating",
            ),
        ]

    def __str__(self):
        return f"{self.rating} stars on {self.product.name}"


class Collection(models.Model):
    """Curated groups such as Modern Living, New Arrivals, Best Sellers."""

    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=160, unique=True)
    description = models.TextField(blank=True, null=True)
    image_url = models.TextField(blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    products = models.ManyToManyField(
        Product, through="CollectionProduct", related_name="collections"
    )

    class Meta:
        db_table = "collections"
        ordering = ["-is_featured", "id"]

    def __str__(self):
        return self.name


class CollectionProduct(models.Model):
    """Many-to-many join between collections and products.

    schema.sql declares PRIMARY KEY (collection_id, product_id). Django does
    not support composite primary keys on a through model, so this carries an
    implicit `id` and enforces the same pairing with a UNIQUE constraint --
    identical behaviour, one extra column.
    """

    collection = models.ForeignKey(
        Collection, on_delete=models.CASCADE, db_column="collection_id"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, db_column="product_id"
    )
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "collection_products"
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["collection", "product"], name="uq_collection_product"
            ),
            models.CheckConstraint(
                condition=models.Q(sort_order__gte=0),
                name="ck_collection_product_sort_order",
            ),
        ]
        indexes = [
            models.Index(
                fields=["collection", "sort_order"], name="idx_coll_prod_coll_sort"
            ),
        ]

    def __str__(self):
        return f"{self.collection.name} - {self.product.name}"
