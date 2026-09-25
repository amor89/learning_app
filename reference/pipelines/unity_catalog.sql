-- Catalog structure
-- research_prod (catalog)
--   research_bronze      write: pipeline service principal only
--   research_silver      write: pipeline service principal; read: analytics team
--   research_gold        write: pipeline service principal; read: all approved users
--   research_governance  write: governance team only; read: all pipelines

-- Table properties set on every Delta table
ALTER TABLE research_silver.nat_respondents
SET TBLPROPERTIES (
    'owner'               = 'data.engineering@example.org',
    'tracker_id'          = 'TRK-AUD-001',
    'grain'               = 'one row per respondent per wave',
    'layer'               = 'silver',
    'data_classification' = 'restricted',
    'pii'                 = 'true',
    'created_date'        = '2025-01-15'
);

-- Row-level security for PII
CREATE ROW ACCESS POLICY restrict_respondent_data
    ON research_silver.nat_respondents
    USING (
        is_member('research_approved_analysts')
        OR current_user() = 'pipeline-svc@example.org'
    );
