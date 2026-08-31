-- Coverage items + pipeline decisions (created in production 2026-08-25).
-- Idempotent: IF NOT EXISTS throughout. Do not DROP or recreate these tables.
-- Coverage rows are independent finds, not TTO listings. technologies.uuid
-- is an optional join only; unmatched items keep technology_uuid NULL.

CREATE TABLE IF NOT EXISTS coverage_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  technology_uuid uuid,
  university text,
  headline text NOT NULL,
  summary text,
  capability text,
  sources jsonb NOT NULL DEFAULT '[]',
  source_class text NOT NULL
    CHECK (source_class IN ('newspaper_tv', 'specialist')),
  independence_note text,
  coverage_date date,
  packet_week date,
  match_status text NOT NULL DEFAULT 'unmatched'
    CHECK (match_status IN ('matched', 'unmatched', 'candidate')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pipeline_decisions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  coverage_item_id uuid NOT NULL
    REFERENCES coverage_items (id) ON DELETE CASCADE,
  technology_uuid uuid,
  user_story text NOT NULL,
  status text NOT NULL
    CHECK (status IN ('greenlit', 'hold', 'proceed', 'archive', 'dropped')),
  blocker text,
  signed_off_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_coverage_items_technology_uuid ON coverage_items (technology_uuid);
CREATE INDEX IF NOT EXISTS idx_coverage_items_packet_week ON coverage_items (packet_week);
CREATE INDEX IF NOT EXISTS idx_coverage_items_university ON coverage_items (university);
CREATE INDEX IF NOT EXISTS idx_pipeline_decisions_coverage_item_id ON pipeline_decisions (coverage_item_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_decisions_technology_uuid ON pipeline_decisions (technology_uuid);
CREATE INDEX IF NOT EXISTS idx_pipeline_decisions_status ON pipeline_decisions (status);

COMMENT ON TABLE coverage_items IS 'Weekly independent-coverage finds. Not TTO listings; optional join to technologies.uuid.';
COMMENT ON TABLE pipeline_decisions IS 'Hold/proceed/archive decisions for coverage items. Not columns on technologies.';
