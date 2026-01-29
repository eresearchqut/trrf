import logging

logger = logging.getLogger(__name__)

_schema_cache = None


def get_cached_schema():
    global _schema_cache

    if _schema_cache is None:
        from report.schema import create_dynamic_schema

        logger.info("Creating dynamic GraphQL schema (cache miss)")
        _schema_cache = create_dynamic_schema()

    return _schema_cache


def invalidate_schema_cache():
    global _schema_cache

    if _schema_cache is not None:
        logger.info("Invalidating GraphQL schema cache")
    _schema_cache = None
