#!/usr/bin/env bash
#
# Release the project and bump version number in the process.

set -e

cd "$(dirname "$0")"

FORCE=false

usage() {
    echo "Usage: $0 [options] VERSION [PRERELEASE_TYPE]"
    echo
    echo "VERSION:"
    echo "  major: bump major version number"
    echo "  minor: bump minor version number"
    echo "  patch: bump patch version number"
    echo "  stable: bump to next stable version (e.g., 1.0.0)"
    echo "  rc: bump pre-release version number (e.g., 1.0.0rc1)"
    echo "  beta: bump pre-release version number (e.g., 1.0.0b1)"
    echo "  alpha: bump pre-release version number (e.g., 1.0.0a1)"
    echo
    echo "PRERELEASE_TYPE (optional):"
    echo "  alpha: create alpha prerelease (e.g., 1.2.4a1 from 1.2.3)"
    echo "  beta: create beta prerelease (e.g., 1.2.4b1 from 1.2.3)"
    echo "  rc: create release candidate (e.g., 1.2.4rc1 from 1.2.3)"
    echo
    echo "Examples:"
    echo "  $0 patch              # Bump patch: 1.2.3 -> 1.2.4"
    echo "  $0 patch alpha        # Bump patch + alpha: 1.2.3 -> 1.2.4a1"
    echo "  $0 minor beta         # Bump minor + beta: 1.2.3 -> 1.3.0b1"
    echo "  $0 major rc           # Bump major + rc: 1.2.3 -> 2.0.0rc1"
    echo "  $0 alpha              # Bump alpha: 1.0.0a1 -> 1.0.0a2"
    echo
    echo "Options:"
    echo "  -f, --force:  force release"
    echo "  -h, --help:   show this help message"
    exit 1
}

# parse args
while [ "$#" -gt 0 ]; do
    case "$1" in
    -f | --force)
        FORCE=true
        shift
        ;;
    -h | --help)
        usage
        ;;
    *)
        break
        ;;
    esac
done

# check if version is specified
if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    usage
fi

VERSION="$1"
PRERELEASE_TYPE="${2:-}"

# Validate VERSION argument
valid_version=false
for v in major minor patch stable rc beta alpha; do
    if [ "$VERSION" = "$v" ]; then
        valid_version=true
        break
    fi
done

if [ "$valid_version" = false ]; then
    echo "Error: invalid VERSION '$VERSION'"
    usage
fi

# Validate PRERELEASE_TYPE if provided
if [ -n "$PRERELEASE_TYPE" ]; then
    valid_prerelease=false
    for p in alpha beta rc; do
        if [ "$PRERELEASE_TYPE" = "$p" ]; then
            valid_prerelease=true
            break
        fi
    done
    
    if [ "$valid_prerelease" = false ]; then
        echo "Error: invalid PRERELEASE_TYPE '$PRERELEASE_TYPE'"
        usage
    fi
    
    # Cannot combine prerelease bump with prerelease specifier
    if [ "$VERSION" = "alpha" ] || [ "$VERSION" = "beta" ] || [ "$VERSION" = "rc" ]; then
        echo "Error: cannot specify PRERELEASE_TYPE with VERSION=$VERSION"
        echo "Use 'release.sh $PRERELEASE_TYPE' or 'release.sh patch $PRERELEASE_TYPE' for next version"
        exit 1
    fi
    
    # Cannot combine stable with prerelease
    if [ "$VERSION" = "stable" ]; then
        echo "Error: cannot specify PRERELEASE_TYPE with VERSION=stable"
        exit 1
    fi
fi

# check if git is clean and force is not enabled
if ! git diff-index --quiet HEAD -- && [ "$FORCE" = false ]; then
    echo "Error: git is not clean. Please commit all changes first."
    exit 1
fi

if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install uv from https://docs.astral.sh/uv/"
    exit 1
fi

echo "Would bump version:"
if [ -n "$PRERELEASE_TYPE" ]; then
    uv version --bump "$VERSION" --bump "$PRERELEASE_TYPE" --dry-run
else
    uv version --bump "$VERSION" --dry-run
fi

# prompt for confirmation
if [ "$FORCE" = false ]; then
    read -p "Do you want to release? [yY] " -n 1 -r
    echo
else
    REPLY="y"
fi
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -n "$PRERELEASE_TYPE" ]; then
        # Bump version and add prerelease suffix in a single command
        uv version --bump "$VERSION" --bump "$PRERELEASE_TYPE"
    else
        # Just bump the specified version
        uv version --bump "$VERSION"
    fi

    new_version=$(uv version --short)

    # commit changes
    git add pyproject.toml uv.lock
    git commit -m "bump version to $new_version"
    git tag -a "v$new_version" -m "v$new_version"

    # push changes
    git push origin stable
    git push origin "v$new_version"
else
    echo "Aborted."
    exit 1
fi
