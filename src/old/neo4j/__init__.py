"""Neo4j converter package.

This package contains importers and exporters for Neo4j graph database format.
Provides Cypher query generation and graph database integration.
"""

try:
    # Import only the class, not any module-level instances
    from .neo4jExporter import Neo4jExporter
    # Skip the old exporter for now to avoid issues
    __all__ = ['Neo4jExporter']
except ImportError as e:
    print(f"Warning: Neo4j converters not available due to missing dependencies: {e}")
    __all__ = []