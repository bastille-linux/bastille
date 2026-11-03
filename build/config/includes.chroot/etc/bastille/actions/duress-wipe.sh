#!/bin/bash
# Bastille duress action: the Duress PIN.
# Wipe key material (RAM keys, VPN config, session keys), then cut power.
# Called detached by pam_thl_duress, so the login the coercer sees still succeeds.
set -u
/etc/bastille/actions/wipe-keys.sh || true
exec /etc/bastille/actions/emergency-poweroff.sh
