PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- =========================================================
-- 1. CATEGORIES
-- Top-level shop categories: Sofas, Beds, Dining, etc.
-- =========================================================
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    image_url TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- 2. SUBCATEGORIES
-- Category-specific filters such as 3-Seater, Sectional,
-- Recliner, etc.
-- =========================================================
CREATE TABLE subcategories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),

    FOREIGN KEY (category_id)
        REFERENCES categories(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    UNIQUE (category_id, slug)
);

-- =========================================================
-- 3. PRODUCTS
-- Main product catalogue table.
-- =========================================================
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subcategory_id INTEGER NOT NULL,

    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    description TEXT,

    price NUMERIC NOT NULL CHECK (price >= 0),
    compare_at_price NUMERIC CHECK (
        compare_at_price IS NULL OR compare_at_price >= 0
    ),

    warranty_years INTEGER CHECK (
        warranty_years IS NULL OR warranty_years >= 0
    ),

    rating NUMERIC NOT NULL DEFAULT 0 CHECK (
        rating >= 0 AND rating <= 5
    ),
    review_count INTEGER NOT NULL DEFAULT 0 CHECK (
        review_count >= 0
    ),

    is_featured INTEGER NOT NULL DEFAULT 0 CHECK (is_featured IN (0, 1)),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (subcategory_id)
        REFERENCES subcategories(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

-- =========================================================
-- 4. PRODUCT IMAGES
-- One product can have multiple images.
-- =========================================================
CREATE TABLE product_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,

    image_url TEXT NOT NULL,
    alt_text TEXT,

    sort_order INTEGER NOT NULL DEFAULT 0 CHECK (sort_order >= 0),
    is_primary INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),

    FOREIGN KEY (product_id)
        REFERENCES products(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

-- =========================================================
-- 5. PRODUCT VARIANTS
-- Current use case: finishes such as Natural Ash, Walnut,
-- Black Oak. Price can differ per variant.
-- =========================================================
CREATE TABLE product_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,

    name TEXT NOT NULL,
    price NUMERIC CHECK (
        price IS NULL OR price >= 0
    ),

    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),

    FOREIGN KEY (product_id)
        REFERENCES products(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    UNIQUE (product_id, name)
);

-- =========================================================
-- 6. PRODUCT REVIEWS
-- Individual customer reviews.
-- =========================================================
CREATE TABLE product_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,

    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_text TEXT,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (product_id)
        REFERENCES products(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

-- =========================================================
-- 7. COLLECTIONS
-- Curated groups such as Modern Living, New Arrivals,
-- Best Sellers, Scandinavian Collection, etc.
-- =========================================================
CREATE TABLE collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,

    description TEXT,
    image_url TEXT,

    is_featured INTEGER NOT NULL DEFAULT 0 CHECK (is_featured IN (0, 1)),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- 8. COLLECTION_PRODUCTS
-- Many-to-many relationship between collections and products.
-- =========================================================
CREATE TABLE collection_products (
    collection_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,

    sort_order INTEGER NOT NULL DEFAULT 0 CHECK (sort_order >= 0),

    PRIMARY KEY (collection_id, product_id),

    FOREIGN KEY (collection_id)
        REFERENCES collections(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    FOREIGN KEY (product_id)
        REFERENCES products(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

-- =========================================================
-- INDEXES
-- Improve common catalogue/filter queries.
-- =========================================================
CREATE INDEX idx_subcategories_category_id
    ON subcategories(category_id);

CREATE INDEX idx_products_subcategory_id
    ON products(subcategory_id);

CREATE INDEX idx_products_active
    ON products(is_active);

CREATE INDEX idx_products_featured
    ON products(is_featured);

CREATE INDEX idx_product_images_product_id
    ON product_images(product_id);

CREATE INDEX idx_product_variants_product_id
    ON product_variants(product_id);

CREATE INDEX idx_product_reviews_product_id
    ON product_reviews(product_id);

CREATE INDEX idx_collection_products_product_id
    ON collection_products(product_id);

CREATE INDEX idx_collection_products_collection_id_sort
    ON collection_products(collection_id, sort_order);

COMMIT;
