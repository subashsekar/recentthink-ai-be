"""Request and response Pydantic schemas.

Two layers of schemas live under this package. Import them from their specific
modules (the package ``__init__`` is intentionally kept free of eager imports to
avoid pulling the ORM models in as a side effect):

- Database-layer schemas (``app.schemas.user``, ``app.schemas.refresh_token``)
  model the repository boundary and may contain internal fields such as
  ``password_hash``.
- API-facing schemas (``app.schemas.responses``) are the only schemas that
  should ever be returned from HTTP endpoints; they never expose credential
  material.
"""
