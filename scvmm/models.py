#!/usr/bin/env python
"""Configuration models for orb-worker-scvmm."""

import re
from enum import Enum
from typing import Optional, List, Dict

from pydantic import BaseModel, Field, field_validator


class MatchType(str, Enum):
    """Matching strategy for cluster name patterns."""

    EXACT = "exact"
    PREFIX = "prefix"
    REGEX = "regex"


class SiteMapping(BaseModel):
    """Configuration for mapping cluster names to sites/locations."""

    code: str = Field(
        ..., description="Code or pattern to match cluster names against"
    )
    name: str = Field(..., description="Site name (e.g., 'Boise', 'Portland')")
    match_type: MatchType = Field(
        default=MatchType.PREFIX,
        description="How to match the code against cluster names: 'exact', 'prefix', or 'regex'",
    )
    description: Optional[str] = Field(
        default=None, description="Optional description of this site"
    )

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Ensure code is not empty."""
        if not v or not v.strip():
            raise ValueError("Code cannot be empty")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is not empty."""
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v


class EnvironmentMapping(BaseModel):
    """Configuration for mapping cluster names to environment/groups."""

    code: str = Field(
        ..., description="Code or pattern to match cluster names against"
    )
    name: str = Field(
        ..., description="Environment/group name (e.g., 'Production Clusters')"
    )
    match_type: MatchType = Field(
        default=MatchType.PREFIX,
        description="How to match the code against cluster names: 'exact', 'prefix', or 'regex'",
    )
    description: Optional[str] = Field(
        default=None, description="Optional description of this environment"
    )

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Ensure code is not empty."""
        if not v or not v.strip():
            raise ValueError("Code cannot be empty")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is not empty."""
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v


class VLANMapping(BaseModel):
    """Configuration for mapping VLAN IDs to NetBox VLAN attributes."""

    vid: int = Field(
        ..., description="VLAN ID from SCVMM (1-4094)"
    )
    name: str = Field(
        ..., description="NetBox VLAN name (required)"
    )
    status: Optional[str] = Field(
        default=None,
        description="NetBox VLAN status: 'active', 'planned', or 'deprecated' (defaults to 'active' if not specified)"
    )
    role: Optional[str] = Field(
        default=None, description="NetBox VLAN role"
    )
    description: Optional[str] = Field(
        default=None, description="VLAN description"
    )
    tags: Optional[List[str]] = Field(
        default=None, description="List of NetBox tags to apply to this VLAN"
    )
    vlan_group: Optional[str] = Field(
        default=None, description="NetBox VLAN Group name"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is not empty."""
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Ensure status is a valid NetBox status."""
        if v is None:
            return v
        valid_statuses = ("active", "planned", "deprecated")
        if v.lower() not in valid_statuses:
            raise ValueError(
                f"Status must be one of: {', '.join(valid_statuses)}"
            )
        return v.lower()

    @field_validator("vid")
    @classmethod
    def validate_vid(cls, v: int) -> int:
        """Ensure VID is positive."""
        if v <= 0:
            raise ValueError("VLAN ID must be a positive integer")
        return v


class WinRMConfig(BaseModel):
    """WinRM connection configuration for SCVMM server."""

    port: int = Field(
        default=5985, description="WinRM port (default: 5985 for HTTP, 5986 for HTTPS)"
    )
    protocol: str = Field(
        default="http",
        description="Protocol: 'http' or 'https'",
    )
    path: str = Field(
        default="/wsman", description="WinRM service path (default: /wsman)"
    )
    transport: str = Field(
        default="ntlm",
        description="Transport/authentication method: 'ntlm', 'kerberos', 'basic', 'certificate'",
    )
    server_certificate_validation: str = Field(
        default="ignore",
        description="Certificate validation: 'ignore', 'validate', or 'self-signed'",
    )

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Ensure port is in valid range."""
        if not (1 <= v <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v

    @field_validator("protocol")
    @classmethod
    def validate_protocol(cls, v: str) -> str:
        """Ensure protocol is valid."""
        if v.lower() not in ("http", "https"):
            raise ValueError("Protocol must be 'http' or 'https'")
        return v.lower()

    @field_validator("transport")
    @classmethod
    def validate_transport(cls, v: str) -> str:
        """Ensure transport method is valid."""
        valid_transports = ("ntlm", "kerberos", "basic", "certificate")
        if v.lower() not in valid_transports:
            raise ValueError(
                f"Transport must be one of: {', '.join(valid_transports)}"
            )
        return v.lower()

    @field_validator("server_certificate_validation")
    @classmethod
    def validate_cert_validation(cls, v: str) -> str:
        """Ensure certificate validation mode is valid."""
        valid_modes = ("ignore", "validate", "self-signed")
        if v.lower() not in valid_modes:
            raise ValueError(
                f"Certificate validation must be one of: {', '.join(valid_modes)}"
            )
        return v.lower()


class OrganizationConfig(BaseModel):
    """Organization-specific configuration for cluster naming conventions and mappings."""

    site_mappings: List[SiteMapping] = Field(
        default_factory=list, description="List of site/location mappings"
    )
    environment_mappings: List[EnvironmentMapping] = Field(
        default_factory=list,
        description="List of environment/group mappings",
    )
    vlan_mappings: List[VLANMapping] = Field(
        default_factory=list,
        description="List of VLAN ID to NetBox attribute mappings",
    )
    default_site: str = Field(
        default="Unknown",
        description="Default site name when cluster doesn't match any mapping",
    )
    default_group: str = Field(
        default="",
        description="Default environment group when cluster doesn't match any mapping",
    )

    @field_validator("default_site")
    @classmethod
    def validate_default_site(cls, v: str) -> str:
        """Ensure default_site is defined."""
        return v.strip()

    @field_validator("default_group")
    @classmethod
    def validate_default_group(cls, v: str) -> str:
        """Ensure default_group is defined."""
        return v.strip()


class CompiledOrganizationConfig(BaseModel):
    """Pre-compiled organization config with regex patterns ready for quick matching."""

    site_mappings: List[dict] = Field(
        description="Compiled site mappings with regex patterns"
    )
    environment_mappings: List[dict] = Field(
        description="Compiled environment mappings with regex patterns"
    )
    vlan_mappings: Dict[int, dict] = Field(
        description="Compiled VLAN mappings, keyed by VID for fast lookup"
    )
    default_site: str
    default_group: str
