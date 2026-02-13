-- Y-Connect WhatsApp Bot - Database Initialization Script
-- This script creates the database schema for government schemes

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create schemes table
CREATE TABLE IF NOT EXISTS schemes (
    scheme_id VARCHAR(100) PRIMARY KEY,
    scheme_name VARCHAR(500) NOT NULL,
    scheme_name_translations JSONB,
    description TEXT,
    description_translations JSONB,
    category VARCHAR(100),
    authority VARCHAR(100),
    applicable_states TEXT[],
    eligibility_criteria JSONB,
    benefits TEXT,
    benefits_translations JSONB,
    application_process TEXT,
    application_process_translations JSONB,
    official_url VARCHAR(500),
    helpline_numbers TEXT[],
    status VARCHAR(20) DEFAULT 'active',
    start_date DATE,
    end_date DATE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_document_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for schemes table
CREATE INDEX IF NOT EXISTS idx_schemes_category ON schemes(category);
CREATE INDEX IF NOT EXISTS idx_schemes_status ON schemes(status);
CREATE INDEX IF NOT EXISTS idx_schemes_states ON schemes USING GIN(applicable_states);
CREATE INDEX IF NOT EXISTS idx_schemes_last_updated ON schemes(last_updated);

-- Create scheme_documents table
CREATE TABLE IF NOT EXISTS scheme_documents (
    document_id VARCHAR(100) PRIMARY KEY,
    scheme_id VARCHAR(100) REFERENCES schemes(scheme_id) ON DELETE CASCADE,
    language VARCHAR(10) NOT NULL,
    content TEXT NOT NULL,
    document_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for scheme_documents table
CREATE INDEX IF NOT EXISTS idx_scheme_documents_scheme_id ON scheme_documents(scheme_id);
CREATE INDEX IF NOT EXISTS idx_scheme_documents_language ON scheme_documents(language);
CREATE INDEX IF NOT EXISTS idx_scheme_documents_type ON scheme_documents(document_type);

-- Create function to update last_updated timestamp
CREATE OR REPLACE FUNCTION update_last_updated_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update last_updated
DROP TRIGGER IF EXISTS update_schemes_last_updated ON schemes;
CREATE TRIGGER update_schemes_last_updated
    BEFORE UPDATE ON schemes
    FOR EACH ROW
    EXECUTE FUNCTION update_last_updated_column();

-- Insert sample scheme for testing (optional)
INSERT INTO schemes (
    scheme_id,
    scheme_name,
    scheme_name_translations,
    description,
    category,
    authority,
    applicable_states,
    status,
    official_url
) VALUES (
    'test-scheme-001',
    'Test Government Scheme',
    '{"hi": "परीक्षण सरकारी योजना", "en": "Test Government Scheme"}',
    'This is a test scheme for initial setup verification',
    'test',
    'central',
    ARRAY['ALL'],
    'active',
    'https://example.gov.in/test-scheme'
) ON CONFLICT (scheme_id) DO NOTHING;

-- Grant permissions (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_app_user;

-- Display table information
SELECT 
    'Database initialization complete!' as message,
    COUNT(*) as scheme_count 
FROM schemes;
