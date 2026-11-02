# Bastille OS

A security-hardened Debian 13 live Linux. Boots from USB into RAM. No traces left on the host.

---

## What it is

Bastille is a live OS designed for people who need genuine security — not security theatre. It runs entirely in RAM, randomises its hostname on every boot, encrypts DNS, enforces a WireGuard kill switch, and provides a duress system that can silently destroy keys or brick UEFI under coercion.

It ships lean. The first-boot wizard lets you install the apps you actually want.

---

## Architecture

| Repo | What's in it |
|---|---|
| [`bastille-linux/bastille`](https://github.com/bastille-linux/bastille) | ISO build system — live-build config, hooks, security daemons |
| [`bastille-linux/apps`](https://github.com/bastille-linux/apps) | GTK4 native apps (Notes, Music, Calendar, Maps, Mail, Settings) |
| [`bastille-linux/security`](https://github.com/bastille-linux/security) | C security subsystems — duress, keyguard, USB inspector, gpggrid |
| [`bastille-linux/site`](https://github.com/bastille-linux/site) | Website and docs |

Apps are **not** baked into the ISO. The first-boot wizard fetches what you choose. Updates to apps don't require a new ISO.

---

## Security features

- **OpenRC init** — no systemd attack surface
- **seatd** — seat management without logind
- **WireGuard kill switch** — nftables blocks all traffic unless through `wg0`
- **dnscrypt-proxy** — encrypted DNS, locked to `127.0.0.1:53`
- **AppArmor + USBGuard** — mandatory access control + USB whitelisting
- **Duress system** — fake duress PIN (decoy session) + real duress PIN (key destruction / UEFI brick)
- **DSM (Device Stress Mode)** — crypto-erases NVMe, bricks UEFI via firmware write
- **RAM wipe on shutdown** — `/etc/init.d/bastille-ramwipe`
- **Hostname randomisation** — new hostname every boot
- **ME neutralisation** — Intel Management Engine mitigation on supported hardware
- **BFU eviction** — before-first-unlock LUKS key eviction

---

## Building

### CI (GitHub Actions)

Every push to `main` triggers builds for both architectures. Releases are created automatically at `bastille-linux/bastille`.

### Local (Docker)

```bash
# amd64
bash build-amd64-local.sh

# arm64 (on Apple Silicon or ARM host)
bash build-arm64-local.sh
```

Requires Docker with `--privileged` support.

---

## First boot

1. Boot from USB
2. Log in at the tuigreet console (`user` / no password by default — set one in the wizard)
3. Sway compositor starts automatically
4. First-boot wizard launches — choose your apps, set your PINs, configure WireGuard

---

## Repo structure

```
build/
  auto/config               — live-build configuration
  config/
    package-lists/          — packages baked into the ISO
    hooks/live/             — chroot hooks (numbered, run in order)
    includes.chroot/        — files dropped into the live filesystem
      etc/bastille/         — runtime config (duress PINs, keystore, actions)
      etc/init.d/           — OpenRC services
      usr/local/src/        — C security tool sources (compiled during build)
      usr/local/sbin/       — compiled binaries + shell helpers
src/                        — source mirrors for security tools (auditable)
.github/workflows/          — CI: amd64 + arm64 builds
```

---

## Threat model

Bastille is designed for:
- Journalists, activists, and researchers working in hostile environments
- People who need plausible deniability under physical coercion
- Anyone who cannot trust the host machine they boot from

It is **not** designed for:
- Daily driver use on untrusted hardware with no WireGuard config
- Replacing a hardened desktop OS for general use
- Scenarios where the attacker has unlimited pre-boot access

---

## Contributing

Security issues: open a private advisory on GitHub.  
Everything else: PRs welcome.
