from django.contrib import admin
from django.utils.html import format_html

from .forms import CategoryForm, CollectionForm, ProductImageForm
from .models import (
    Category,
    Collection,
    CollectionProduct,
    Product,
    ProductImage,
    ProductReview,
    ProductVariant,
    Subcategory,
)


def _thumb(url, size=44):
    if not url:
        return "-"
    return format_html(
        '<img src="{}" style="width:{}px;height:{}px;object-fit:cover;'
        'border-radius:4px;" />',
        url,
        size,
        size,
    )


class SubcategoryInline(admin.TabularInline):
    model = Subcategory
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    form = CategoryForm
    list_display = ("preview", "name", "slug", "product_count", "is_active")
    list_display_links = ("preview", "name")
    list_editable = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")
    inlines = [SubcategoryInline]

    @admin.display(description="")
    def preview(self, obj):
        return _thumb(obj.image_url)

    @admin.display(description="Products")
    def product_count(self, obj):
        return Product.objects.filter(subcategory__category=obj).count()


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "slug", "is_active")
    list_filter = ("category", "is_active")
    list_editable = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    form = ProductImageForm
    extra = 1
    fields = ("upload", "image_url", "alt_text", "sort_order", "is_primary", "preview")
    readonly_fields = ("preview",)

    @admin.display(description="Preview")
    def preview(self, obj):
        return _thumb(obj.image_url, 60)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


class CollectionProductInline(admin.TabularInline):
    model = CollectionProduct
    extra = 1
    autocomplete_fields = ("product",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "preview",
        "name",
        "category_name",
        "subcategory",
        "price_display",
        "rating",
        "review_count",
        "is_featured",
        "is_active",
    )
    list_display_links = ("preview", "name")
    list_editable = ("is_featured", "is_active")
    list_filter = ("is_active", "is_featured", "subcategory__category", "subcategory")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("subcategory",)
    inlines = [ProductImageInline, ProductVariantInline]
    readonly_fields = ("rating", "review_count", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "slug", "subcategory", "description")}),
        (
            "Pricing",
            {
                "fields": ("price", "compare_at_price", "warranty_years"),
                "description": "Set 'Compare at price' above 'Price' to show the "
                "sale badge and struck-through price on the storefront.",
            },
        ),
        ("Visibility", {"fields": ("is_featured", "is_active")}),
        (
            "Computed",
            {
                "fields": ("rating", "review_count", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("subcategory", "subcategory__category")
            .prefetch_related("images")
        )

    @admin.display(description="")
    def preview(self, obj):
        image = obj.primary_image
        return _thumb(image.image_url if image else None)

    @admin.display(description="Category", ordering="subcategory__category__name")
    def category_name(self, obj):
        return obj.subcategory.category.name

    @admin.display(description="Price", ordering="price")
    def price_display(self, obj):
        if obj.is_on_sale:
            return format_html(
                '<span style="text-decoration:line-through;color:#999">{}</span> '
                "<strong>{}</strong> ({}% off)",
                f"Rs {obj.compare_at_price:,.0f}",
                f"Rs {obj.price:,.0f}",
                obj.discount_percent,
            )
        return f"Rs {obj.price:,.0f}"


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "rating", "short_text", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("product__name", "review_text")
    autocomplete_fields = ("product",)

    @admin.display(description="Review")
    def short_text(self, obj):
        if not obj.review_text:
            return "-"
        return obj.review_text[:80] + ("..." if len(obj.review_text) > 80 else "")

    def save_model(self, request, obj, form, change):
        """Keep products.rating / review_count in step with the reviews."""
        super().save_model(request, obj, form, change)
        obj.product.recalculate_rating()

    def delete_model(self, request, obj):
        product = obj.product
        super().delete_model(request, obj)
        product.recalculate_rating()

    def delete_queryset(self, request, queryset):
        products = {review.product for review in queryset}
        super().delete_queryset(request, queryset)
        for product in products:
            product.recalculate_rating()


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    form = CollectionForm
    list_display = ("preview", "name", "slug", "item_count", "is_featured", "is_active")
    list_display_links = ("preview", "name")
    list_editable = ("is_featured", "is_active")
    list_filter = ("is_featured", "is_active")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [CollectionProductInline]

    @admin.display(description="")
    def preview(self, obj):
        return _thumb(obj.image_url)

    @admin.display(description="Products")
    def item_count(self, obj):
        return obj.products.count()
