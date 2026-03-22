-- ReadmitIQ PostgreSQL initialization
-- Additional indexes and extensions beyond SQLAlchemy auto-create

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- for fuzzy MRN search

-- Performance indexes (SQLAlchemy creates base indexes; these are supplemental)
-- Will run after tables are created by FastAPI startup

DO $$ BEGIN
  RAISE NOTICE 'ReadmitIQ database initialized';
END $$;
