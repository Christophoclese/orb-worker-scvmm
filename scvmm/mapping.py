#!/usr/bin/env python
"""Mapping resolver for cluster name to site/environment resolution."""

import logging
import re
from typing import Optional

from scvmm.models import OrganizationConfig, MatchType

logger = logging.getLogger(__name__)


class MappingResolver:
    """Resolves cluster names to sites and environment groups based on configuration.

    Implements hierarchical matching strategy:
    1. Exact match (full cluster name match)
    2. Prefix match (substring matching, case-insensitive)
    3. Regex match (pattern matching)
    """

    def __init__(self, config: Optional[OrganizationConfig] = None):
        """Initialize resolver with organization configuration.

        Args:
            config: OrganizationConfig with site and environment mappings.
                   If None, creates default empty config.
        """
        self.config = config or OrganizationConfig()
        self.logger = logger

        # Pre-compile regex patterns for performance
        self._compile_site_patterns()
        self._compile_environment_patterns()

    def _compile_site_patterns(self) -> None:
        """Pre-compile regex patterns for site mappings."""
        self.site_mappings_compiled = []
        for mapping in self.config.site_mappings:
            compiled = {
                "code": mapping.code,
                "name": mapping.name,
                "match_type": mapping.match_type,
                "description": mapping.description,
                "regex": None,
            }

            if mapping.match_type == MatchType.REGEX:
                try:
                    compiled["regex"] = re.compile(mapping.code, re.IGNORECASE)
                except re.error as e:
                    self.logger.error(
                        f"Invalid regex pattern in site mapping '{mapping.code}': {e}"
                    )
                    continue

            self.site_mappings_compiled.append(compiled)

    def _compile_environment_patterns(self) -> None:
        """Pre-compile regex patterns for environment mappings."""
        self.environment_mappings_compiled = []
        for mapping in self.config.environment_mappings:
            compiled = {
                "code": mapping.code,
                "name": mapping.name,
                "match_type": mapping.match_type,
                "description": mapping.description,
                "regex": None,
            }

            if mapping.match_type == MatchType.REGEX:
                try:
                    compiled["regex"] = re.compile(mapping.code, re.IGNORECASE)
                except re.error as e:
                    self.logger.error(
                        f"Invalid regex pattern in environment mapping '{mapping.code}': {e}"
                    )
                    continue

            self.environment_mappings_compiled.append(compiled)

    def resolve_site(self, cluster_name: str) -> str:
        """Resolve cluster name to site/location.

        Uses hierarchical matching strategy:
        1. Exact match (full cluster name)
        2. Prefix match (substring, case-insensitive)
        3. Regex match (pattern)

        Args:
            cluster_name: The cluster name to resolve.

        Returns:
            Site name from matching mapping, or default_site if no match.
        """
        if not cluster_name:
            self.logger.debug("Empty cluster name provided for site resolution")
            return self.config.default_site

        cluster_lower = cluster_name.lower()
        self.logger.debug(f"Resolving site for cluster: {cluster_name}")

        # 1. Try exact match
        for mapping in self.site_mappings_compiled:
            if mapping["match_type"] == MatchType.EXACT:
                if cluster_lower == mapping["code"].lower():
                    self.logger.debug(
                        f"Site resolved via exact match: {cluster_name} → {mapping['name']} "
                        f"(pattern: {mapping['code']})"
                    )
                    return mapping["name"]

        # 2. Try prefix match
        for mapping in self.site_mappings_compiled:
            if mapping["match_type"] == MatchType.PREFIX:
                if mapping["code"].lower() in cluster_lower:
                    self.logger.debug(
                        f"Site resolved via prefix match: {cluster_name} → {mapping['name']} "
                        f"(pattern: {mapping['code']})"
                    )
                    return mapping["name"]

        # 3. Try regex match
        for mapping in self.site_mappings_compiled:
            if mapping["match_type"] == MatchType.REGEX and mapping["regex"]:
                if mapping["regex"].search(cluster_name):
                    self.logger.debug(
                        f"Site resolved via regex match: {cluster_name} → {mapping['name']} "
                        f"(pattern: {mapping['code']})"
                    )
                    return mapping["name"]

        # No match found, use default
        self.logger.debug(
            f"No site mapping found for cluster: {cluster_name}, using default: {self.config.default_site}"
        )
        return self.config.default_site

    def resolve_group(self, cluster_name: str) -> str:
        """Resolve cluster name to environment group/category.

        Uses hierarchical matching strategy:
        1. Exact match (full cluster name)
        2. Prefix match (substring, case-insensitive)
        3. Regex match (pattern)

        Args:
            cluster_name: The cluster name to resolve.

        Returns:
            Environment group name from matching mapping, or default_group if no match.
        """
        if not cluster_name:
            self.logger.debug("Empty cluster name provided for group resolution")
            return self.config.default_group

        cluster_lower = cluster_name.lower()
        self.logger.debug(f"Resolving group for cluster: {cluster_name}")

        # 1. Try exact match
        for mapping in self.environment_mappings_compiled:
            if mapping["match_type"] == MatchType.EXACT:
                if cluster_lower == mapping["code"].lower():
                    self.logger.debug(
                        f"Group resolved via exact match: {cluster_name} → {mapping['name']} "
                        f"(pattern: {mapping['code']})"
                    )
                    return mapping["name"]

        # 2. Try prefix match
        for mapping in self.environment_mappings_compiled:
            if mapping["match_type"] == MatchType.PREFIX:
                if mapping["code"].lower() in cluster_lower:
                    self.logger.debug(
                        f"Group resolved via prefix match: {cluster_name} → {mapping['name']} "
                        f"(pattern: {mapping['code']})"
                    )
                    return mapping["name"]

        # 3. Try regex match
        for mapping in self.environment_mappings_compiled:
            if mapping["match_type"] == MatchType.REGEX and mapping["regex"]:
                if mapping["regex"].search(cluster_name):
                    self.logger.debug(
                        f"Group resolved via regex match: {cluster_name} → {mapping['name']} "
                        f"(pattern: {mapping['code']})"
                    )
                    return mapping["name"]

        # No match found, use default
        self.logger.debug(
            f"No group mapping found for cluster: {cluster_name}, using default: {self.config.default_group}"
        )
        return self.config.default_group
