#!/usr/bin/env python
"""Tests for scvmm mapping resolver."""

import pytest

from scvmm.models import (
    MatchType,
    SiteMapping,
    EnvironmentMapping,
    OrganizationConfig,
)
from scvmm.mapping import MappingResolver


class TestMappingResolverSites:
    """Tests for site mapping resolution."""

    def test_resolve_site_exact_match(self):
        config = OrganizationConfig(
            site_mappings=[
                SiteMapping(code="cluster-boi-01", name="Boise", match_type=MatchType.EXACT),
                SiteMapping(code="boi", name="Boise Alt", match_type=MatchType.PREFIX),
            ]
        )
        resolver = MappingResolver(config)

        # Exact match should take precedence over prefix match
        assert resolver.resolve_site("cluster-boi-01") == "Boise"

    def test_resolve_site_prefix_match(self):
        config = OrganizationConfig(
            site_mappings=[
                SiteMapping(code="boi", name="Boise", match_type=MatchType.PREFIX),
                SiteMapping(code="ptl", name="Portland", match_type=MatchType.PREFIX),
            ]
        )
        resolver = MappingResolver(config)

        assert resolver.resolve_site("boi-cluster-01") == "Boise"
        assert resolver.resolve_site("ptl-cluster-02") == "Portland"

    def test_resolve_site_prefix_match_case_insensitive(self):
        config = OrganizationConfig(
            site_mappings=[
                SiteMapping(code="boi", name="Boise", match_type=MatchType.PREFIX),
            ]
        )
        resolver = MappingResolver(config)

        assert resolver.resolve_site("BOI-CLUSTER-01") == "Boise"
        assert resolver.resolve_site("BoI-cluster") == "Boise"

    def test_resolve_site_regex_match(self):
        config = OrganizationConfig(
            site_mappings=[
                SiteMapping(
                    code=r"^cluster-boi-\d{2}$",
                    name="Boise",
                    match_type=MatchType.REGEX,
                ),
                SiteMapping(
                    code=r"^cluster-ptl-\d{2}$",
                    name="Portland",
                    match_type=MatchType.REGEX,
                ),
            ]
        )
        resolver = MappingResolver(config)

        assert resolver.resolve_site("cluster-boi-01") == "Boise"
        assert resolver.resolve_site("cluster-ptl-99") == "Portland"

    def test_resolve_site_matching_hierarchy(self):
        """Test that exact match > prefix match > regex match > default."""
        config = OrganizationConfig(
            site_mappings=[
                SiteMapping(code="exact-cluster", name="Exact", match_type=MatchType.EXACT),
                SiteMapping(code="prefix", name="Prefix", match_type=MatchType.PREFIX),
                SiteMapping(code=r".*cluster.*", name="Regex", match_type=MatchType.REGEX),
            ],
            default_site="Default Site",
        )
        resolver = MappingResolver(config)

        # Exact match takes precedence
        assert resolver.resolve_site("exact-cluster") == "Exact"

        # Prefix match when no exact match
        assert resolver.resolve_site("prefix-something") == "Prefix"

        # Regex match when no exact or prefix match
        assert resolver.resolve_site("my-cluster-name") == "Regex"

        # Default when nothing matches
        assert resolver.resolve_site("unknown-vm") == "Default Site"

    def test_resolve_site_first_match_wins(self):
        """Test that first matching mapping wins."""
        config = OrganizationConfig(
            site_mappings=[
                SiteMapping(code="boi", name="Boise", match_type=MatchType.PREFIX),
                SiteMapping(code="boi", name="Boise Alt", match_type=MatchType.PREFIX),
            ]
        )
        resolver = MappingResolver(config)

        # First match wins
        assert resolver.resolve_site("boi-cluster") == "Boise"

    def test_resolve_site_no_mappings(self):
        config = OrganizationConfig(default_site="Unknown")
        resolver = MappingResolver(config)

        assert resolver.resolve_site("any-cluster") == "Unknown"

    def test_resolve_site_empty_cluster_name(self):
        config = OrganizationConfig(default_site="Unknown")
        resolver = MappingResolver(config)

        assert resolver.resolve_site("") == "Unknown"
        assert resolver.resolve_site(None) == "Unknown"

    def test_resolve_site_invalid_regex(self):
        """Test that invalid regex patterns are skipped during initialization."""
        config = OrganizationConfig(
            site_mappings=[
                SiteMapping(
                    code="[invalid(regex",  # Invalid regex
                    name="Invalid",
                    match_type=MatchType.REGEX,
                ),
                SiteMapping(code="boi", name="Boise", match_type=MatchType.PREFIX),
            ],
            default_site="Default",
        )
        # Should not raise, but log the error
        resolver = MappingResolver(config)

        # The invalid regex should be skipped, but prefix match should still work
        assert resolver.resolve_site("boi-cluster") == "Boise"


class TestMappingResolverGroups:
    """Tests for environment group mapping resolution."""

    def test_resolve_group_exact_match(self):
        config = OrganizationConfig(
            environment_mappings=[
                EnvironmentMapping(
                    code="production", name="Production", match_type=MatchType.EXACT
                ),
                EnvironmentMapping(code="prd", name="Prod", match_type=MatchType.PREFIX),
            ]
        )
        resolver = MappingResolver(config)

        assert resolver.resolve_group("production") == "Production"

    def test_resolve_group_prefix_match(self):
        config = OrganizationConfig(
            environment_mappings=[
                EnvironmentMapping(code="prd", name="Production", match_type=MatchType.PREFIX),
                EnvironmentMapping(code="dev", name="Development", match_type=MatchType.PREFIX),
            ]
        )
        resolver = MappingResolver(config)

        assert resolver.resolve_group("prd-cluster") == "Production"
        assert resolver.resolve_group("dev-cluster") == "Development"

    def test_resolve_group_regex_match(self):
        config = OrganizationConfig(
            environment_mappings=[
                EnvironmentMapping(
                    code=r"^(prd|prod)-",
                    name="Production",
                    match_type=MatchType.REGEX,
                ),
                EnvironmentMapping(
                    code=r"^(dev|development)-",
                    name="Development",
                    match_type=MatchType.REGEX,
                ),
            ]
        )
        resolver = MappingResolver(config)

        assert resolver.resolve_group("prd-cluster") == "Production"
        assert resolver.resolve_group("prod-cluster") == "Production"
        assert resolver.resolve_group("dev-cluster") == "Development"
        assert resolver.resolve_group("development-cluster") == "Development"

    def test_resolve_group_case_insensitive(self):
        config = OrganizationConfig(
            environment_mappings=[
                EnvironmentMapping(code="prd", name="Production", match_type=MatchType.PREFIX),
            ]
        )
        resolver = MappingResolver(config)

        assert resolver.resolve_group("PRD-CLUSTER") == "Production"
        assert resolver.resolve_group("PrD-cluster") == "Production"

    def test_resolve_group_matching_hierarchy(self):
        """Test that exact match > prefix match > regex match > default."""
        config = OrganizationConfig(
            environment_mappings=[
                EnvironmentMapping(
                    code="exact-group", name="Exact", match_type=MatchType.EXACT
                ),
                EnvironmentMapping(code="prefix", name="Prefix", match_type=MatchType.PREFIX),
                EnvironmentMapping(
                    code=r".*group.*", name="Regex", match_type=MatchType.REGEX
                ),
            ],
            default_group="Uncategorized",
        )
        resolver = MappingResolver(config)

        # Exact match
        assert resolver.resolve_group("exact-group") == "Exact"

        # Prefix match
        assert resolver.resolve_group("prefix-name") == "Prefix"

        # Regex match
        assert resolver.resolve_group("my-group-cluster") == "Regex"

        # Default
        assert resolver.resolve_group("unknown") == "Uncategorized"

    def test_resolve_group_no_mappings(self):
        config = OrganizationConfig(default_group="Unclassified")
        resolver = MappingResolver(config)

        assert resolver.resolve_group("any-cluster") == "Unclassified"

    def test_resolve_group_empty_cluster_name(self):
        config = OrganizationConfig(default_group="Unknown")
        resolver = MappingResolver(config)

        assert resolver.resolve_group("") == "Unknown"
        assert resolver.resolve_group(None) == "Unknown"


class TestMappingResolverInitialization:
    """Tests for resolver initialization."""

    def test_resolver_with_none_config(self):
        resolver = MappingResolver(None)
        assert resolver.config.default_site == "Unknown"
        assert resolver.config.default_group == ""

    def test_resolver_with_empty_config(self):
        config = OrganizationConfig()
        resolver = MappingResolver(config)
        assert resolver.config.default_site == "Unknown"

    def test_resolver_pattern_compilation(self):
        """Test that regex patterns are pre-compiled during initialization."""
        config = OrganizationConfig(
            site_mappings=[
                SiteMapping(
                    code=r"^cluster-[a-z]+-\d{2}$",
                    name="Site",
                    match_type=MatchType.REGEX,
                ),
            ]
        )
        resolver = MappingResolver(config)

        # Should succeed on valid patterns
        assert resolver.resolve_site("cluster-abc-01") == "Site"


class TestMappingResolverRealWorldScenarios:
    """Test real-world configuration scenarios."""

    def test_darigold_naming_convention(self):
        """Test with Darigold's actual naming convention."""
        config = OrganizationConfig(
            site_mappings=[
                SiteMapping(code="boi", name="Boise", match_type=MatchType.PREFIX),
                SiteMapping(code="boz", name="Bozeman", match_type=MatchType.PREFIX),
                SiteMapping(code="ptl", name="Portland", match_type=MatchType.PREFIX),
                SiteMapping(code="dhq", name="Darigold HQ", match_type=MatchType.PREFIX),
            ],
            environment_mappings=[
                EnvironmentMapping(
                    code="prd", name="Production Clusters", match_type=MatchType.PREFIX
                ),
                EnvironmentMapping(
                    code="dev", name="Development Clusters", match_type=MatchType.PREFIX
                ),
                EnvironmentMapping(
                    code="inf", name="Infrastructure Clusters", match_type=MatchType.PREFIX
                ),
            ],
        )
        resolver = MappingResolver(config)

        # Test site resolution
        assert resolver.resolve_site("boi-prd-cluster-01") == "Boise"
        assert resolver.resolve_site("ptl-dev-cluster-01") == "Portland"
        assert resolver.resolve_site("dhq-inf-cluster-01") == "Darigold HQ"

        # Test group resolution
        assert resolver.resolve_group("boi-prd-cluster-01") == "Production Clusters"
        assert resolver.resolve_group("ptl-dev-cluster-01") == "Development Clusters"
        assert resolver.resolve_group("dhq-inf-cluster-01") == "Infrastructure Clusters"
