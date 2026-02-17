"""
FastAPI dependency injection.

Design decisions
----------------
Why dependency injection (not global imports):
    FastAPI's Depends() system provides request-scoped dependencies that are
    easy to override in tests. Instead of importing a global db_client, each
    endpoint declares what it needs:

        @app.get("/jobs")
        async def list_jobs(repo: JobRepository = Depends(get_job_repository)):
            ...

    In tests, you override the dependency with a mock:
        app.dependency_overrides[get_job_repository] = lambda: MockJobRepo()

    This pattern decouples endpoint logic from infrastructure and is the
    standard approach in production FastAPI applications.

Dependencies to be added in later modules
------------------------------------------
    - get_current_user    (Module 7: Auth — extracts user from JWT token)
    - get_db_session      (Module 2: Database — provides MongoDB session)
    - get_settings        (Module 1: already available from src.core.config)
    - get_*_repository    (Module 2: Database — repository instances)
    - get_model_manager   (Module 3: LLM — provides configured ModelManager)
"""

# Dependencies will be implemented as their respective modules are built.
# This file serves as the central registry for all FastAPI dependencies.
