-- Technology Assessments table
CREATE TABLE IF NOT EXISTS technology_assessments (
    id SERIAL PRIMARY KEY,
    technology_id INTEGER NOT NULL REFERENCES technologies(id) ON DELETE CASCADE,
    assessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    model VARCHAR(100) NOT NULL,
    assessment_tier VARCHAR(20) NOT NULL,  -- 'full', 'limited'

    composite_score DECIMAL(3,2),

    trl_gap_score DECIMAL(3,2),
    trl_gap_confidence DECIMAL(3,2),
    trl_gap_reasoning TEXT,
    trl_gap_details JSONB,

    false_barrier_score DECIMAL(3,2),
    false_barrier_confidence DECIMAL(3,2),
    false_barrier_reasoning TEXT,
    false_barrier_details JSONB,

    alt_application_score DECIMAL(3,2),
    alt_application_confidence DECIMAL(3,2),
    alt_application_reasoning TEXT,
    alt_application_details JSONB,

    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_cost DECIMAL(10,6),
    raw_response JSONB
);

CREATE INDEX idx_assessments_technology_id ON technology_assessments(technology_id);
CREATE INDEX idx_assessments_composite_score ON technology_assessments(composite_score DESC NULLS LAST);
CREATE INDEX idx_assessments_assessed_at ON technology_assessments(assessed_at);

-- Add assessment columns to technologies table
ALTER TABLE technologies
    ADD COLUMN IF NOT EXISTS assessment_status VARCHAR(50) DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS composite_opportunity_score DECIMAL(3,2),
    ADD COLUMN IF NOT EXISTS last_assessed_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX IF NOT EXISTS idx_technologies_assessment_status ON technologies(assessment_status);
CREATE INDEX IF NOT EXISTS idx_technologies_composite_score ON technologies(composite_opportunity_score DESC NULLS LAST);
