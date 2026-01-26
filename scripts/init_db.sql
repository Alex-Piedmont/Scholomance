-- University Tech Transfer Database Schema
-- Version: 1.0
-- Purpose: Store scraped technology listings from university tech transfer offices

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- Main technologies table
CREATE TABLE IF NOT EXISTS technologies (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE,
    
    -- Core identifiers
    university VARCHAR(100) NOT NULL,
    tech_id VARCHAR(200) NOT NULL,
    
    -- Basic information
    title TEXT NOT NULL,
    description TEXT,
    url TEXT NOT NULL,
    
    -- Temporal tracking
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Raw data from source (preserves all original fields)
    raw_data JSONB,
    
    -- Derived/classified fields (populated by LLM or manual tagging)
    top_field VARCHAR(100),
    subfield VARCHAR(100),
    patent_geography TEXT[],
    keywords TEXT[],
    
    -- Status tracking
    classification_status VARCHAR(50) DEFAULT 'pending',
    classification_confidence DECIMAL(3,2),
    last_classified_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT unique_university_tech UNIQUE(university, tech_id)
);

-- Indexes for common queries
CREATE INDEX idx_technologies_university ON technologies(university);
CREATE INDEX idx_technologies_top_field ON technologies(top_field);
CREATE INDEX idx_technologies_subfield ON technologies(subfield);
CREATE INDEX idx_technologies_scraped_at ON technologies(scraped_at);
CREATE INDEX idx_technologies_classification_status ON technologies(classification_status);

-- GIN indexes for full-text search and array operations
CREATE INDEX idx_technologies_title_search ON technologies USING gin(to_tsvector('english', title));
CREATE INDEX idx_technologies_description_search ON technologies USING gin(to_tsvector('english', description));
CREATE INDEX idx_technologies_keywords ON technologies USING gin(keywords);
CREATE INDEX idx_technologies_patent_geography ON technologies USING gin(patent_geography);

-- JSONB index for raw_data queries
CREATE INDEX idx_technologies_raw_data ON technologies USING gin(raw_data);

-- Universities metadata table
CREATE TABLE IF NOT EXISTS universities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    code VARCHAR(20) UNIQUE NOT NULL,  -- Short code like 'stanford', 'gatech'
    base_url TEXT NOT NULL,
    scraper_config JSONB,
    last_scraped TIMESTAMP WITH TIME ZONE,
    total_technologies INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial universities
INSERT INTO universities (name, code, base_url) VALUES
    ('Stanford University', 'stanford', 'https://techfinder.stanford.edu'),
    ('Georgia Institute of Technology', 'gatech', 'https://licensing.research.gatech.edu/technology-licensing'),
    ('University of Georgia', 'uga', 'https://uga.flintbox.com/technologies')
ON CONFLICT (code) DO NOTHING;

-- Scrape logs table for tracking scraping runs
CREATE TABLE IF NOT EXISTS scrape_logs (
    id SERIAL PRIMARY KEY,
    university VARCHAR(100) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50),  -- 'running', 'completed', 'failed', 'partial'
    technologies_found INTEGER DEFAULT 0,
    technologies_new INTEGER DEFAULT 0,
    technologies_updated INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB
);

CREATE INDEX idx_scrape_logs_university ON scrape_logs(university);
CREATE INDEX idx_scrape_logs_started_at ON scrape_logs(started_at);

-- Classification logs table
CREATE TABLE IF NOT EXISTS classification_logs (
    id SERIAL PRIMARY KEY,
    technology_id INTEGER REFERENCES technologies(id) ON DELETE CASCADE,
    classified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    model VARCHAR(100),  -- Which model was used
    top_field VARCHAR(100),
    subfield VARCHAR(100),
    confidence DECIMAL(3,2),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_cost DECIMAL(10,6),
    raw_response JSONB
);

CREATE INDEX idx_classification_logs_technology_id ON classification_logs(technology_id);
CREATE INDEX idx_classification_logs_classified_at ON classification_logs(classified_at);

-- Field taxonomy table (for standardizing classifications)
CREATE TABLE IF NOT EXISTS field_taxonomy (
    id SERIAL PRIMARY KEY,
    top_field VARCHAR(100) NOT NULL,
    subfield VARCHAR(100),
    description TEXT,
    synonyms TEXT[],
    parent_id INTEGER REFERENCES field_taxonomy(id),
    level INTEGER DEFAULT 1,  -- 1 for top_field, 2 for subfield
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_field_subfield UNIQUE(top_field, subfield)
);

-- Insert some initial taxonomy (can be expanded)
INSERT INTO field_taxonomy (top_field, level) VALUES
    ('Robotics', 1),
    ('MedTech', 1),
    ('Agriculture', 1),
    ('Energy', 1),
    ('Computing', 1),
    ('Materials', 1),
    ('Biotechnology', 1),
    ('Electronics', 1)
ON CONFLICT DO NOTHING;

-- View for easy querying of classified technologies
CREATE OR REPLACE VIEW classified_technologies AS
SELECT 
    t.id,
    t.uuid,
    t.university,
    t.tech_id,
    t.title,
    t.description,
    t.url,
    t.top_field,
    t.subfield,
    t.patent_geography,
    t.keywords,
    t.scraped_at,
    t.classification_confidence,
    u.name as university_name
FROM technologies t
LEFT JOIN universities u ON t.university = u.code
WHERE t.classification_status = 'completed';

-- View for scraping statistics
CREATE OR REPLACE VIEW scraping_stats AS
SELECT 
    u.name as university,
    u.code,
    COUNT(t.id) as total_technologies,
    COUNT(CASE WHEN t.classification_status = 'completed' THEN 1 END) as classified_count,
    COUNT(CASE WHEN t.classification_status = 'pending' THEN 1 END) as pending_classification,
    MAX(t.scraped_at) as last_scraped,
    u.active
FROM universities u
LEFT JOIN technologies t ON u.code = t.university
GROUP BY u.id, u.name, u.code, u.active;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update updated_at
CREATE TRIGGER update_technologies_updated_at 
    BEFORE UPDATE ON technologies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE technologies IS 'Main table storing scraped technology listings from universities';
COMMENT ON COLUMN technologies.raw_data IS 'Complete raw data from source in JSONB format for flexibility';
COMMENT ON COLUMN technologies.classification_status IS 'Status of LLM classification: pending, in_progress, completed, failed';
COMMENT ON TABLE universities IS 'Registry of universities and their scraping configuration';
COMMENT ON TABLE scrape_logs IS 'Audit log of all scraping operations';
COMMENT ON TABLE classification_logs IS 'Detailed log of LLM classification operations including costs';

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_app_user;
