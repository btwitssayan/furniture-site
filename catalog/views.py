from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    TrigramWordSimilarity,
)
from django.db.models import Count, F, Prefetch, Q
from django.shortcuts import get_object_or_404, render

from .models import Category, Collection, Product, Subcategory


def _active_products():
    """Base queryset for every catalogue listing, with images preloaded."""
    return (
        Product.objects.filter(is_active=True)
        .select_related("subcategory", "subcategory__category")
        .prefetch_related("images")
    )


def home(request):
    return render(
        request,
        "catalog/home.html",
        {
            "nav": "home",
            "categories": Category.objects.filter(is_active=True),
            "featured_products": _active_products().filter(is_featured=True)[:4],
            "editorial_collection": Collection.objects.filter(
                is_active=True, is_featured=True
            ).first(),
        },
    )


def shop(request):
    """Full catalogue, narrowed by ?category=<slug> and then ?sub=<slug>.

    The two filters are tiered: the subcategory row only appears once a
    category is chosen, and a stale ?sub= from another category is ignored
    rather than returning an empty grid.
    """
    products = _active_products()

    active_category = None
    if request.GET.get("category"):
        active_category = Category.objects.filter(
            slug=request.GET["category"], is_active=True
        ).first()
        if active_category:
            products = products.filter(subcategory__category=active_category)

    subcategories = []
    active_subcategory = None
    if active_category:
        subcategories = list(
            active_category.subcategories.filter(is_active=True).annotate(
                product_count=Count("products", filter=Q(products__is_active=True))
            )
        )
        if request.GET.get("sub"):
            active_subcategory = next(
                (s for s in subcategories if s.slug == request.GET["sub"]), None
            )
            if active_subcategory:
                products = products.filter(subcategory=active_subcategory)

    return render(
        request,
        "catalog/shop.html",
        {
            "nav": "shop",
            "products": products,
            "product_count": products.count(),
            "categories": Category.objects.filter(is_active=True),
            "active_category": active_category,
            "subcategories": subcategories,
            "active_subcategory": active_subcategory,
        },
    )


def category_detail(request, slug):
    """One template serving every category page, optionally filtered by
    ?sub=<subcategory slug> for the chips (3-Seater, Sectional, ...)."""
    category = get_object_or_404(Category, slug=slug, is_active=True)
    products = _active_products().filter(subcategory__category=category)

    subcategories = list(
        category.subcategories.filter(is_active=True).annotate(
            product_count=Count("products", filter=Q(products__is_active=True))
        )
    )

    active_subcategory = None
    if request.GET.get("sub"):
        active_subcategory = next(
            (s for s in subcategories if s.slug == request.GET["sub"]), None
        )
        if active_subcategory:
            products = products.filter(subcategory=active_subcategory)

    return render(
        request,
        "catalog/category_detail.html",
        {
            "nav": "shop",
            "category": category,
            "products": products,
            "product_count": products.count(),
            "subcategories": subcategories,
            "active_subcategory": active_subcategory,
        },
    )


def product_detail(request, slug):
    product = get_object_or_404(
        _active_products().prefetch_related("variants", "reviews"), slug=slug
    )
    related = (
        _active_products()
        .filter(subcategory__category=product.subcategory.category)
        .exclude(pk=product.pk)[:4]
    )
    if related.count() < 4:
        related = _active_products().exclude(pk=product.pk)[:4]

    return render(
        request,
        "catalog/product_detail.html",
        {
            "nav": "shop",
            "product": product,
            "variants": product.variants.filter(is_active=True),
            "related_products": related,
        },
    )


#: Minimum pg_trgm word-similarity for the typo fallback. Measured against
#: this catalogue, real typos ("wardrove", "lampp", "dinning") score ~0.64-0.67
#: while unrelated words sit well below 0.4.
TRIGRAM_THRESHOLD = 0.4


def search(request):
    """Postgres full-text search over the catalogue.

    Primary path is the GIN-indexed `search_vector` with ts_rank ordering.
    If that finds nothing (usually a typo -- "sofaa", "wardrove") it falls
    back to pg_trgm similarity on the product name so the user still gets
    something useful instead of an empty page.
    """
    query_text = (request.GET.get("q") or "").strip()
    products, fuzzy = [], False

    if query_text:
        query = SearchQuery(query_text, config="english", search_type="websearch")
        products = (
            _active_products()
            .filter(search_vector=query)
            .annotate(rank=SearchRank(F("search_vector"), query))
            .order_by("-rank", "-is_featured", "name")
        )

        if not products.exists():
            fuzzy = True
            # Word similarity, not plain similarity: it scores the query
            # against individual words in the name, so a short typo still
            # matches a long product name ("lampp" -> Halo Arc Floor Lamp).
            products = (
                _active_products()
                .annotate(similarity=TrigramWordSimilarity(query_text, "name"))
                .filter(similarity__gte=TRIGRAM_THRESHOLD)
                .order_by("-similarity")
            )

    return render(
        request,
        "catalog/search.html",
        {
            "nav": "shop",
            "query": query_text,
            "products": products,
            "product_count": len(products) if isinstance(products, list) else products.count(),
            "fuzzy": fuzzy,
        },
    )


def collection_list(request):
    return render(
        request,
        "catalog/collection_list.html",
        {"nav": "collections", "collections": Collection.objects.filter(is_active=True)},
    )


def collection_detail(request, slug):
    collection = get_object_or_404(
        Collection.objects.prefetch_related(
            Prefetch(
                "products",
                queryset=_active_products(),
            )
        ),
        slug=slug,
        is_active=True,
    )
    return render(
        request,
        "catalog/collection_detail.html",
        {"nav": "collections", "collection": collection, "products": collection.products.all()},
    )


def about(request):
    return render(request, "catalog/about.html", {"nav": "about"})


def contact(request):
    return render(request, "catalog/contact.html", {"nav": "contact"})
