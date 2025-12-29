-- 1. Configuração inicial de extensões (se necessário, mas FTS é nativo)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; 

-- 2. Tabela de Sessões/Queries do Usuário
CREATE TABLE search_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_identifier TEXT NOT NULL, -- Pode ser ID do Telegram, Discord, etc.
    query_text TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Tabela de Produtos (Listings/URLs)
CREATE TABLE products (
    product_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identidade: URL. Recomenda-se normalizar (remover query params) na app
    url TEXT NOT NULL UNIQUE, 
    
    -- Dados Básicos
    domain TEXT NOT NULL, -- ex: amazon.com.br (útil para filtros)
    title TEXT NOT NULL,
    description TEXT,
    
    -- Flexibilidade: Atributos extraídos (Cor, Voltagem, Specs)
    -- Ex: {"color": "preto", "voltage": "220v", "brand": "brastemp"}
    specs JSONB DEFAULT '{}'::jsonb,
    
    -- Controle
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Coluna Computada para Full-Text Search (Português)
    -- Concatena Título + Descrição + Valores do JSONB para busca
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('portuguese', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('portuguese', coalesce(description, '')), 'B') ||
        setweight(jsonb_to_tsvector('portuguese', specs, '["all"]'), 'C')
    ) STORED
);

-- 4. Tabela de Histórico de Preços (Time Series)
CREATE TABLE price_history (
    history_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    
    -- Precisão Financeira
    price_amount NUMERIC(14, 2) NOT NULL,
    currency CHAR(3) DEFAULT 'BRL', -- ISO 4217
    
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Índices Estratégicos

-- Performance da Busca Textual (Essencial para o "Checar base histórica")
CREATE INDEX idx_products_search ON products USING GIN(search_vector);

-- Performance para buscar atributos específicos no JSON (ex: filtrar só geladeiras 220v)
CREATE INDEX idx_products_specs ON products USING GIN(specs);

-- Performance para recuperar histórico ordenado por data (Gráficos de preço)
CREATE INDEX idx_price_history_product_date ON price_history (product_id, scraped_at DESC);

-- 6. Trigger para atualização automática do 'last_updated_at'
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