# Bastille OS daily-driver plan

## Primary goal

Turn Bastille OS from a security-focused live-image prototype into an installable, recoverable, hardware-compatible desktop that can be used every day without silently breaking networking, updates, power management, or user data.

## Phase 0 — documentation and architecture discovery

**How this serves the primary goal:** Establishes the actual runtime contracts before changing security-sensitive boot, networking, and installer code.

Read the repository's build, installer, service, desktop, and CI documentation and reconcile the intended OpenRC architecture with the files that still assume systemd. Record exact package names, service dependencies, boot paths, and supported hardware assumptions.

Verification: every finding has a source path and line; no API or package name is accepted solely because it sounds plausible.

## Phase 1 — make the image build reproducibly

**How this serves the primary goal:** A daily-driver distro cannot be tested or shipped until the image build is deterministic and green.

Fix stale package references, architecture-specific package handling, generated-file drift, hook ordering, and CI diagnostics. Add static checks for shell/Python/config syntax and a package-reference consistency check.

Verification: both CI architecture builds complete; all hooks pass; the generated image contains the expected init system and required binaries.

## Phase 2 — reconcile networking and service supervision

**How this serves the primary goal:** Reliable networking is essential for normal work, and a contradictory kill switch currently risks making the system unusable or falsely secure.

Make dnscrypt-proxy, NetworkManager, WireGuard, nftables, and the network guard agree on resolver address, service identity, interface discovery, VPN endpoint ports, captive-portal behavior, and OpenRC supervision. Remove or replace systemd-only commands and assumptions.

Verification: offline boot, DHCP, Wi-Fi, VPN-up, VPN-down, DNS failure, captive portal, and manual recovery scenarios are testable with a documented matrix.

## Phase 3 — produce a real installed system

**How this serves the primary goal:** Installation must result in a persistent OS rather than a live image with hidden live-only dependencies.

Harden the installer and first-boot flow: account creation, locale/timezone/keyboard setup, firmware selection, Secure Boot policy, bootloader registration, encrypted swap/zram, dual-boot safety, failed-install cleanup, and recovery boot. Unify the setup wizard's app/profile choices with the installer backend.

Verification: install to a disposable UEFI disk, reboot without the USB, unlock root, log in, update, and recover from an interrupted installation.

## Phase 4 — laptop and peripheral support

**How this serves the primary goal:** Daily use depends more on batteries, displays, audio, Wi-Fi, Bluetooth, cameras, printers, and docks than on showcase security features.

Add broad firmware coverage, power management, PipeWire session integration, Bluetooth audio, touchpad/display handling, printer/scanner support, webcam/microphone controls, firmware updates, and clear capability detection. Preserve security profiles by making risky hardware features explicit rather than silently unavailable.

Verification: maintain a hardware compatibility matrix covering common Intel/AMD laptops, Wi-Fi, graphics, external displays, suspend policy, Bluetooth audio, webcam, microphone, and printer workflows.

## Phase 5 — updates, backup, recovery, and application lifecycle

**How this serves the primary goal:** A daily-driver installation must survive upgrades, failed boots, lost media, and ordinary data-management needs.

Implement signed metadata verification, atomic updates with rollback, a rescue/recovery environment, user backup/restore, persistence health checks, Flatpak lifecycle management, and consistent application catalog metadata.

Verification: update failure leaves the previous bootable version intact; restore recovers a test home directory; unsigned or mismatched artifacts are rejected.

## Phase 6 — security validation and release readiness

**How this serves the primary goal:** The system should be trustworthy without relying on untested claims or catastrophic defaults.

Add integration tests and fuzzing targets for privileged helpers, duress and wipe actions, USB authorization, keyguard, firmware audit, and update verification. Document the threat-model tradeoffs between live and installed modes, publish reproducible build metadata, and define supported versus best-effort hardware.

Verification: clean build, static analysis, unit tests, disposable-VM boot tests, installer tests, network tests, artifact signature checks, and a release checklist all pass.

## Explicit deferrals

Firmware flashing/ME neutralization remains opt-in and hardware-gated; no claim of universal firmware mitigation; no destructive wipe or firmware-bricking behavior is expanded until independently tested.

The installer now records a hardware family profile so support can be tested
against ThinkPads, modern Windows/UEFI laptops, Intel MacBooks, and unknown
hardware separately. LibreWolf and Zen are permitted as optional privacy
browsers; Tor remains an explicit high-anonymity choice rather than a default.
