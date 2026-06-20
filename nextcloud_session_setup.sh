#!/bin/bash
# Sets session + token lifetimes to 24 hours and disables logout timeouts.
# Usage: nextcloud_session_setup.sh [nextcloud-path]

set -uo pipefail

NC="${1:-}"
if [ -z "$NC" ] || [ ! -d "$NC" ]; then
    echo "Usage: $0 <nextcloud-path>"
    echo "Example: $0 /var/www/html"
    exit 1
fi

CONTAINER=$(docker ps --format '{{.Names}} {{.Image}}' 2>/dev/null | grep -i nextcloud | head -1 | awk '{print $1}' || true)
if [ -z "$CONTAINER" ]; then
    echo "ERROR: No running Nextcloud container found."
    exit 1
fi
echo "Using container: $CONTAINER"

OCC="docker exec -u www-data $CONTAINER php /var/www/html/occ"

# Test occ
if ! $OCC --version &>/dev/null 2>&1; then
    echo "ERROR: occ not working inside container"
    echo "  Output: $($OCC --version 2>&1)"
    exit 1
fi

echo ""
echo "--- Session & Token Lifetime: 24h ---"
echo ""

set_session() {
    local key="$1" val="$2" type="$3"
    local before; before=$($OCC config:system:get "$key" 2>/dev/null | tail -1 || echo "(default)")
    $OCC config:system:set "$key" --value "$val" --type "$type" 2>/dev/null
    echo "  ${key}: ${before} → ${val}"
}

set_session session_lifetime                86400  integer
set_session session_relaxed_expiry          true   boolean
set_session session_keepalive               true   boolean
set_session auto_logout                     false  boolean
set_session remember_login_cookie_lifetime  86400  integer

# Token-related
set_session token_auth_enforced             false  boolean

echo ""
echo "Done. Config applied to $CONTAINER"
echo "  Session lifetime: 24h"
echo "  Remember-me cookie: 24h"
echo "  Auto logout: disabled"
