CREATE EXTENSION IF NOT EXISTS vector;



CREATE TABLE search_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_identifier TEXT NOT NULL, 
    query_text TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE products (
    product_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    url TEXT NOT NULL UNIQUE, 
    
    domain TEXT NOT NULL, 
    title TEXT NOT NULL,
    description TEXT,
    
    specs JSONB DEFAULT '{}'::jsonb,
    
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('portuguese', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('portuguese', coalesce(description, '')), 'B') ||
        setweight(jsonb_to_tsvector('portuguese', specs, '["all"]'), 'C')
    ) STORED
);

CREATE TABLE price_history (
    history_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    
    price_amount NUMERIC(14, 2) NOT NULL,
    currency CHAR(3) DEFAULT 'BRL',
    
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_products_search ON products USING GIN(search_vector);

CREATE INDEX idx_products_specs ON products USING GIN(specs);

CREATE INDEX idx_price_history_product_date ON price_history (product_id, scraped_at DESC);

CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_products_timestamp
BEFORE UPDATE ON products
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();


ALTER TABLE products 
ADD COLUMN IF NOT EXISTS embedding vector(384), 
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;


CREATE INDEX IF NOT EXISTS idx_products_embedding 
ON products USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_products_active ON products(is_active);

DROP INDEX IF EXISTS idx_price_history_product_date;
CREATE INDEX idx_price_history_product_date ON price_history (product_id, scraped_at DESC);



CREATE TABLE price_alerts (
    alert_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    chat_id BIGINT NOT NULL, 
    target_price NUMERIC(14, 2) NOT NULL, 
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_checked_at TIMESTAMPTZ
);

CREATE INDEX idx_alerts_active ON price_alerts(is_active) WHERE is_active = TRUE;