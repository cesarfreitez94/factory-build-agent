"""Odoo version-aware knowledge layer.

Provides the VersionKnowledgeResolver that loads and merges knowledge entries
from versioned JSON layers (base/, v17/, v18/, etc.) into a unified queryable
dictionary. Used by agents to consult Odoo patterns, deprecations, and
novelties for a specific Odoo version.
"""

from fba.odoo_versions.version_resolver import VersionKnowledgeResolver

__all__ = ["VersionKnowledgeResolver"]
