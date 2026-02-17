# Business logic orchestration layer.
# Services coordinate between repositories, LLM calls, and external APIs.
# They contain no direct database queries — that responsibility belongs to repositories.
#
# Available services:
# - IndexingService: RAG indexing pipeline (fetch → chunk → embed → store in Weaviate)
