-- PostgreSQL initialization script for ESTYM_AI
-- Runs automatically on first container start

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable trigram extension for hybrid text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;
