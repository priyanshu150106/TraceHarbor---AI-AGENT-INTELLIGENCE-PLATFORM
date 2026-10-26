-- TraceHarbor PostgreSQL Initialization Script
-- Executed on container startup via /docker-entrypoint-initdb.d

-- Enable pgvector extension on the primary database
CREATE EXTENSION IF NOT EXISTS vector;

-- Create test database if not exists
SELECT 'CREATE DATABASE traceharbor_test'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'traceharbor_test')\gexec

-- Connect to traceharbor_test and enable pgvector
\c traceharbor_test
CREATE EXTENSION IF NOT EXISTS vector;
