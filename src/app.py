from fastapi import FastAPI

from documentation.tags import description, tags_metadata


app = FastAPI(
    title="Axiom App",
    description=description,
    summary="API endpoints for Axiom infrastructure framework",
    version="0.0.1",
    openapi_tags=tags_metadata,
    contact={
        "name": "App repository",
        "url": "https://github.com/Neakio/Axiom_API",
    },
    docs_url=None,
)