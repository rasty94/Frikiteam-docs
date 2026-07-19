---
title: "Applied Cryptography: primitives, hashing and key management"
description: "Which cryptographic primitive to use for each problem: symmetric vs asymmetric vs hashing, password hashing with Argon2, authenticated encryption (AEAD), at-rest encryption with LUKS, key management and the mistakes that keep happening in production."
keywords: "criptografia aplicada, argon2, bcrypt, aead, aes-gcm, chacha20, ed25519, luks, dm-crypt, gestion de claves, kdf, hashing de contraseñas, nonce, timing attack"
date: 2026-07-19
tags: [cybersecurity, cryptography, hashing, encryption, key-management]
draft: false
updated: 2026-07-19
difficulty: intermediate
estimated_time: "16 min"
category: Cybersecurity
status: published
last_reviewed: 2026-07-19
prerequisites:
  - "Intermediate Linux"
  - "Basic DevOps knowledge"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

## Scope: what this document does cover

Most cryptography guides in a DevOps context start with TLS and end at Let's Encrypt. That ground is already covered in this repository and is not repeated here. This document is the **layer those guides take for granted**: which primitive solves which problem, why you'd pick one over another, and which mistakes have been repeating themselves in real code for years.

!!! info "Where the rest lives"
    - **TLS, certificate chains, Let's Encrypt, cipher suites, OCSP, HSTS** → [TLS Certificates](../networking/certificados_tls.md).
    - **VPNs and WireGuard in practice** → [Tailscale](../networking/tailscale.md), [NetBird](../networking/netbird.md) and [VPN to mesh migration](../networking/vpn_to_mesh_migration.md).
    - **Where to store keys and secrets** → [Secrets Management](gestion_secretos.md) and [Secrets in GitOps](secrets_gitops.md).

Here we talk about the decisions made *before* configuring any of those tools.

## Encrypting, hashing and encoding are not the same

This is the most expensive misunderstanding and also the most common. Three distinct operations, with distinct properties:

| Operation | Reversible? | Needs a key? | What it's for |
| --- | --- | --- | --- |
| **Encode** (base64, hex, URL-encoding) | Yes, by anyone | No | Move bytes over a channel expecting text |
| **Hash** (SHA-256, BLAKE2, Argon2) | No, by design | No (except HMAC) | Verify integrity or check passwords |
| **Encrypt** (AES-GCM, ChaCha20-Poly1305) | Yes, with the key | Yes | Hide the content from whoever lacks the key |

!!! danger "base64 is not encryption"
    A base64 Kubernetes `Secret` is plaintext with one extra step. Anyone with the YAML has the value. This point is developed in [Secrets in GitOps](secrets_gitops.md), and it's the whole reason SOPS, Sealed Secrets and ESO exist.

Practical corollary: if someone says "the password is encrypted in base64", it is not encrypted. If they say "we store the password AES-encrypted", it's probably also wrong — passwords are **hashed**, not encrypted, because nobody should ever be able to recover them.

## Primitives: when to use each one

### Symmetric encryption

The same key encrypts and decrypts. It's fast and it's what you use for real volumes of data.

- **AES-256-GCM**: the default standard. With hardware acceleration (AES-NI, present in any modern server CPU) it is extremely fast.
- **ChaCha20-Poly1305**: an alternative with equivalent or better performance **without** hardware acceleration. It's the typical choice on phones, routers and embedded devices. It's also what WireGuard uses.

Both are AEAD (see below), and that is the main reason to prefer them over older modes.

### Asymmetric encryption

Two keys: a public one you hand out, a private one that never leaves its place. It is slow compared to symmetric, so **it is almost never used to encrypt data directly**. It's used to agree on a symmetric key or to sign.

- **Ed25519**: the modern choice for signatures. Short keys, fast, no parameters you can misconfigure. It's what you should generate for new SSH keys.
- **X25519**: key exchange (Diffie-Hellman over curve 25519). It's the mechanism behind WireGuard and behind modern TLS suites.
- **RSA**: still ubiquitous for compatibility. If you must use it, don't go below 2048 bits and prefer 4096 for long-lived keys. For everything else, elliptic curves.
- **ECDSA (P-256, P-384)**: common in TLS certificates. It works, but it's more fragile to implement than Ed25519 because a signature with a repeated nonce leaks the private key.

### Hashing

A one-way function. Two families that people constantly mix up:

- **General-purpose hashes** (SHA-256, SHA-512, BLAKE2, SHA-3): designed to be **fast**. Good for file integrity, deduplication, signatures, Merkle trees, content identifiers in Git.
- **Password hashes** (Argon2, scrypt, bcrypt): designed to be **slow and memory-hard**. Good only for passwords.

Using the first where the second belongs is a serious flaw, and it deserves its own section.

!!! warning "MD5 and SHA-1 are broken for cryptographic use"
    Both have demonstrated practical collisions. They remain acceptable as a checksum against accidental (non-malicious) corruption, but never for signatures, certificates or integrity verification against an attacker.

## Password hashing

### Why SHA-256 is wrong here

SHA-256 is fast, and that is exactly the problem. A modern GPU computes billions of SHA-256 per second. If your database gets stolen, an attacker runs entire dictionaries in minutes.

Password hashing algorithms invert the desired property: they are **deliberately slow** and, in the case of Argon2 and scrypt, **deliberately memory-hard**, which cancels much of the advantage of specialized hardware (GPU, FPGA, ASIC).

### The three candidates

- **Argon2id**: the default recommendation for new systems. It combines resistance to side-channel attacks and to attacks with specialized hardware.
- **scrypt**: also with configurable memory cost. A reasonable choice if Argon2 isn't available in your stack.
- **bcrypt**: the veteran, widely available and still acceptable. Its known limit is that it **truncates the input** (bytes beyond 72 are ignored in the usual implementations), which matters if you allow long passwords or if you pre-hash before bcrypt.

!!! warning "Parameters change over time"
    The correct work factor depends on the current year's hardware and on your login latency budget. Don't copy numbers from a blog (nor from this document). Consult the **current OWASP password storage guidance** and measure on your own hardware: if a login takes less than a few tens of milliseconds to compute the hash, the parameters are probably too low.

### Salt: not optional, and not something you manage

A salt is a random value unique **per password**, stored alongside the hash. It stops two users with the same password from sharing a hash and makes rainbow tables useless.

The good news: any serious password-hashing library generates the salt automatically and embeds it in the output string. If you're writing code to generate and concatenate salts by hand, you are almost certainly overcomplicating and getting it wrong.

```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

# argon2-cffi uses Argon2id and generates the salt for you.
# The defaults are updated across library versions;
# tune them by measuring on your hardware and following current OWASP guidance.
ph = PasswordHasher()

def register(password: str) -> str:
    # The resulting string includes algorithm, parameters, salt and hash.
    # Store that whole string: don't split the salt into another column.
    return ph.hash(password)

def verify(stored_hash: str, password: str) -> bool:
    try:
        ph.verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False
    if ph.check_needs_rehash(stored_hash):
        # Parameters have gone up since this hash was created.
        # Here you have the plaintext password: this is the moment to rehash.
        store_new_hash(ph.hash(password))
    return True
```

`check_needs_rehash` is the piece almost everyone skips, and it's the one that keeps your database current without mass migrations.

### Migrating old hashes without breaking logins

The real scenario: you have a table with thousands of `sha256(password)` and want to reach Argon2id. You can't recompute anything because you don't have the passwords.

There are two strategies, and it's worth understanding the trade-off of each.

**Lazy migration**: you mark each row with the algorithm it uses, and on the next successful login you rehash with the new one. It's simple and risk-free, but inactive users keep the weak hash indefinitely. You need a cut-off date and a policy for accounts that never come back.

**Wrapping**: you apply Argon2 **on top of the old hash**, without needing the password. You migrate 100% of the rows at once, in a single `UPDATE`, and from that moment nobody has weak hashes.

```python
import hashlib
from argon2 import PasswordHasher

ph = PasswordHasher()

def wrap(sha256_hex: str) -> str:
    # Bulk migration: does not require the user's password.
    return ph.hash(sha256_hex)

def verify_wrapped(stored_hash: str, password: str) -> bool:
    # Reproduce the legacy hash and verify it against the wrapper.
    legacy = hashlib.sha256(password.encode()).hexdigest()
    try:
        ph.verify(stored_hash, legacy)
        return True
    except Exception:
        return False
```

!!! warning "Wrapping has an operational cost"
    You end up with two live formats in production and a column indicating which is which. Document the schema, mark each row, and plan the move to pure Argon2 on the next login. If you don't track which row is in which format, the migration becomes irreversible out of confusion, not cryptography.

## AEAD: encrypting without authenticating is a flaw

Encrypting hides the content. **It does not stop the attacker from modifying it.** With older modes like CBC without a MAC, an attacker who can't read the message can still alter bits of the ciphertext in a controlled way, and the receiver will decrypt garbage without noticing — or something worse than garbage.

AEAD (*Authenticated Encryption with Associated Data*) solves this: it encrypts and authenticates in the same operation. If a single bit has changed, decryption **fails** instead of returning tampered data.

Unless you have a very specific reason and know exactly what you're doing, your symmetric encryption must be AEAD: **AES-GCM** or **ChaCha20-Poly1305**.

### Nonces: the trap that sinks the system

A nonce (*number used once*) accompanies every encryption operation. The rule is literal: **never repeat a nonce with the same key**.

With AES-GCM, reusing a nonce is not a theoretical weakness. It allows recovering plaintext information and, worse, recovering the authentication key, at which point the attacker can **forge valid messages**. It's a catastrophic failure, not a gradual one.

Two safe ways to generate them: random with a CSPRNG, or a counter that never resets. The counter is tempting and it's exactly what breaks when you restore a backup, clone a VM or restart a container with no persistent state.

```python
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Generate and store this key with a secret manager, not in the code.
key = AESGCM.generate_key(bit_length=256)
aesgcm = AESGCM(key)

def encrypt(message: bytes, context: bytes) -> bytes:
    nonce = os.urandom(12)  # 96 bits, random, a fresh one per message
    # 'context' is associated data: it is authenticated but NOT encrypted.
    # It ties the message to its destination (tenant ID, version, etc.).
    ct = aesgcm.encrypt(nonce, message, context)
    return nonce + ct  # the nonce is not secret: it travels with the message

def decrypt(blob: bytes, context: bytes) -> bytes:
    nonce, ct = blob[:12], blob[12:]
    # Raises InvalidTag if the message or the context has been altered.
    return aesgcm.decrypt(nonce, ct, context)
```

!!! tip "If you encrypt a lot with the same key, use XChaCha20-Poly1305"
    AES-GCM's 96-bit nonce gives a limited margin for random nonces: past a certain volume of messages under the same key, the collision probability stops being negligible. XChaCha20-Poly1305 (available in libsodium) uses a 192-bit nonce, where a random collision is a non-issue. The alternative is to rotate the key more often.

The *associated data* in the last parameter is an underused tool: it lets you tie a ciphertext to its legitimate context. An encrypted record from tenant A cannot be decrypted as if it belonged to tenant B, even if an attacker moves it around in the database.

## At-rest encryption: what it protects and what it doesn't

### Disk encryption: LUKS/dm-crypt

LUKS is the de facto standard on Linux for full-block encryption. It encrypts the whole device, transparently to the filesystem.

```bash
# Format a device with LUKS2 (destroys existing data)
sudo cryptsetup luksFormat --type luks2 /dev/sdb1

# Open it: creates /dev/mapper/data
sudo cryptsetup open /dev/sdb1 data
sudo mkfs.ext4 /dev/mapper/data
sudo mount /dev/mapper/data /mnt/data

# Inspect header, algorithm and key slots
sudo cryptsetup luksDump /dev/sdb1

# Add a second passphrase (recovery key) and then rotate the first
sudo cryptsetup luksAddKey /dev/sdb1
sudo cryptsetup luksChangeKey /dev/sdb1 -S 0

# Back up the header: without it the data is unrecoverable
sudo cryptsetup luksHeaderBackup /dev/sdb1 --header-backup-file luks-header.img

# Close
sudo umount /mnt/data && sudo cryptsetup close data
```

!!! danger "The LUKS header is a single point of failure"
    It contains the wrapped key material. If it gets corrupted, no passphrase works and the whole volume is lost. Back up the header and keep it **encrypted and off the disk it protects** — it's as sensitive as a private key. See [Secure Backup](backup_seguro.md).

### What disk encryption does NOT protect

This is where many people's intuition fails, and where audits get signed off with a checkbox that doesn't mean what it seems:

- **With the system booted and the volume mounted, it protects nothing.** The key is in RAM and the filesystem is in the clear for any process with permissions. An attacker with RCE on your server sees the data just as if there were no encryption.
- **It does not protect against a system administrator**, nor against a root compromise.
- **It does not protect against the hypervisor** nor against the cloud provider, which controls the machine underneath.
- **It does not protect backups**: if the backup process reads files from the mounted volume, it takes the data in the clear unless you encrypt the backup separately.

What it does protect, and it's not nothing: **powered-off disks**. Laptop theft, hardware decommissioning, a datacenter disk going out for RMA, an unmounted array. That is its real threat model.

### Application-level encryption

Encrypting specific fields within the application before storing them protects what the disk doesn't: the data stays encrypted against the DBA, against a database dump, against replicas, backups and audit logs, and against an attacker who reaches the database but not the service holding the key.

The price is real and must be accepted before you start:

- **You lose queries over those fields.** No `WHERE`, no `LIKE`, no sorting, no useful indexes over encrypted data. For exact-equality search you can index a deterministic HMAC of the value (with a different key), accepting that it leaks which rows share a value.
- **Key management becomes your problem**, including rotation with historical data already encrypted.
- **An implementation mistake is yours**, not the kernel's.

The reasonable rule: disk encryption **always** (it's nearly free), and application-level encryption **selective**, only for the fields that truly justify it — tokens, third-party keys, health data, identity documents.

## Key management: the real problem

Choosing AES-256 is the easy part and the one that matters least. Nobody breaks AES: they come in through the key. The serious question is where it lives, who can read it, and what happens the day it leaks.

This document doesn't repeat the tool catalog: Vault, AWS Secrets Manager and Kubernetes Secrets are compared in [Secrets Management](gestion_secretos.md), and the specific case of secrets versioned in Git in [Secrets in GitOps](secrets_gitops.md). What follows are the cryptographic concepts those guides take as known.

### Key derivation (KDF)

A KDF turns input material into a cryptographic key. Two distinct cases that must not be confused:

- **From a password to a key**: low-entropy input, you need a **slow** KDF with a salt: Argon2id, scrypt or PBKDF2. It's what LUKS does with your passphrase.
- **From a key to several keys**: already high-entropy input, a **fast** KDF is enough: HKDF. Good for deriving per-purpose subkeys from a master key.

```python
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

master = os.urandom(32)  # master key: from the KMS/HSM, never hardcoded

def subkey(purpose: str) -> bytes:
    # 'info' separates domains: the same master produces independent
    # keys for encryption, for HMAC, for tokens...
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=purpose.encode(),
    ).derive(master)

data_key = subkey("data-encryption-v1")
index_key = subkey("search-index-hmac-v1")
```

Deriving per-purpose subkeys is a cheap habit that avoids the mistake of reusing the same key to encrypt and to sign, and turns rotation into a change of version suffix.

### Rotation: the version suffix

Rotating a key without planning ahead is painful, because the data encrypted with the old key is still there. The solution is as simple as it is awkward to retrofit: **tag each ciphertext with the identifier of the key that encrypted it**. A version byte at the start of the blob is enough.

With that, rotation is: generate the new key, encrypt everything new with it, keep accepting the old one for decryption, and re-encrypt the old data in the background. Without the version identifier this is impossible and you end up with a big-bang migration.

!!! warning "Rotating the key does not rotate the secret"
    If a credential has leaked, re-encrypting it with a new key is useless: the attacker already has the plaintext value. You have to **change the credential** at the source system. These are two distinct operations and they're often confused.

### Custody: HSM and KMS

The goal is for the key to **never be in a file nor in an environment variable**. An HSM (hardware) or a managed KMS (AWS KMS, GCP KMS, Azure Key Vault) hold the key and expose operations, not the material: you ask "encrypt this" and get the result back, but you can't export the key.

The usual pattern with these services is **envelope encryption**: you generate a random data key, encrypt the data with it locally (fast), and ask the KMS to encrypt that data key. You store the encrypted data and the encrypted data key together. To read, the KMS decrypts the data key and you decrypt the content. That way only the master key lives in the KMS and you don't send gigabytes through its API.

## Common mistakes in production

### Rolling your own crypto

The most repeated rule and the most ignored. Don't write your own cipher, nor your own mode of operation, nor "AES but with an extra round just in case". Cryptographic failures don't show up as bugs: the code works perfectly, encrypts, decrypts, passes the tests, and is insecure.

Use `cryptography` in Python, libsodium in C/C++/Rust, your platform's standard library. And within those libraries, prefer the high-level APIs: `cryptography` deliberately separates its `hazmat` ("hazardous materials") layer precisely because misusing it is easy.

### ECB mode

Encrypting each block independently makes **identical plaintext blocks produce identical ciphertext blocks**. The structure of the data shows through the encryption: it's the classic example of the ECB-encrypted image where you can still see the picture. It is never the right answer. Use AEAD.

### Comparing secrets with `==`

Comparing bytes with the usual operator exits the loop as soon as it finds a difference. Execution time depends on how many leading bytes match, and an attacker who can measure it reconstructs the value byte by byte. It applies to API tokens, HMAC signatures, verification codes and session cookies.

### Weak randomness

`random` in Python, `Math.random()` in JavaScript or `rand()` in C are **predictable** generators by design: they're meant for simulations, not security. With enough observed outputs the internal state is reconstructed and the next ones are predicted. For anything that must be unpredictable — tokens, nonces, salts, keys, temporary passwords, session identifiers — use a CSPRNG.

```python
import hmac
import secrets

# CORRECT: CSPRNG. On Linux it is fed by getrandom()//dev/urandom.
token = secrets.token_urlsafe(32)
key = secrets.token_bytes(32)

# CORRECT: constant-time comparison.
def token_valid(received: str, expected: str) -> bool:
    return hmac.compare_digest(received, expected)

# WRONG, so it's clear what to avoid:
#   import random; token = random.randint(0, 10**12)   # predictable
#   if received == expected:                            # timing attack
```

!!! note "/dev/urandom is the correct answer on Linux"
    The old debate of `/dev/random` versus `/dev/urandom` has been settled for years in current kernels: `urandom` is cryptographically secure once the pool has been initialized, and it does not block. The only delicate case is early boot of a system with no entropy — a freshly cloned VM, an embedded device with no RTC — and there the answer is `getrandom()`, which does wait for initialization. See [Linux Hardening](hardening_linux.md).

### Others that keep recurring

- **Keys in the repository or in the Dockerfile's environment variables.** They stay in the history and in the image layers.
- **Logging sensitive data** after decrypting it. The encryption is undone on the next line.
- **Reusing the same key for everything.** Derive per-purpose subkeys with HKDF.
- **Trusting a `Content-Type` or a filename** to decide whether something is encrypted. Use an explicit format identifier.
- **Not verifying the signature** on decryption because "it already works". If you ignore the authentication error, you don't have AEAD, you have encryption without integrity.

## Quick reference table: what to use for what

| I need to... | Use | Don't use | Note |
| --- | --- | --- | --- |
| Store user passwords | Argon2id (or scrypt / bcrypt) | SHA-256, MD5, reversible encryption | Automatic salt; check parameters with OWASP |
| Encrypt data at rest in the app | AES-256-GCM or ChaCha20-Poly1305 | AES-CBC without MAC, ECB | Unique nonce per message |
| Encrypt a disk or volume | LUKS2 / dm-crypt | — | Doesn't protect a running system |
| Encrypt a huge number of messages with one key | XChaCha20-Poly1305 | AES-GCM with random nonce | 192-bit nonce, no collision risk |
| Verify a file's integrity | SHA-256, BLAKE2 | MD5, SHA-1 | Fast on purpose |
| Authenticate a message with a shared key | HMAC-SHA256 | Hash of concatenated key | Compare with `compare_digest` |
| Sign (public key) | Ed25519 | RSA-1024, DSA | Short keys, no parameters to break |
| New SSH key | Ed25519 | RSA < 3072, DSA, ECDSA | `ssh-keygen -t ed25519` |
| Key exchange | X25519 | DH with small groups | Basis of WireGuard and modern TLS |
| Derive a key from a password | Argon2id, scrypt, PBKDF2 | SHA-256 iterated by hand | Slow KDF, with salt |
| Derive subkeys from a key | HKDF | Slice up the master key | Separate domains with `info` |
| Session or API token | `secrets` / CSPRNG | `random`, timestamps, UUIDv1 | At least 128 bits of entropy |
| Compare a secret | `hmac.compare_digest` | `==` | Constant time |
| Protect traffic between services | mTLS or WireGuard | Custom crypto over TCP | See related links |
| Store the master key | KMS / HSM / Vault | File, env var, repo | Envelope encryption |

## What this document does not cover

Honesty about the limits, so nobody assumes coverage that isn't there:

- **TLS configuration on servers**, chains, ACME and renewal: it's all in [TLS Certificates](../networking/certificados_tls.md).
- **VPN deployment**: in the [Tailscale](../networking/tailscale.md), [NetBird](../networking/netbird.md) and [mesh migration](../networking/vpn_to_mesh_migration.md) guides.
- **Secrets management tools**: in [Secrets Management](gestion_secretos.md) and [Secrets in GitOps](secrets_gitops.md).
- **Internal PKI and private CAs**, code signing, and post-quantum cryptography: not covered in this repository as of today.
- **Concrete numeric parameters** for Argon2 or for rotation: they change with hardware and with the year. This document tells you what to measure and where to look, deliberately not giving you a number that ages badly.

## Related links

- [TLS Certificates](../networking/certificados_tls.md) — TLS, chains of trust, Let's Encrypt and secure server configuration.
- [Tailscale](../networking/tailscale.md) and [NetBird](../networking/netbird.md) — mesh VPN over WireGuard.
- [VPN to mesh networking migration](../networking/vpn_to_mesh_migration.md) — from OpenVPN and IPsec to WireGuard.
- [Secrets Management](gestion_secretos.md) — Vault, AWS Secrets Manager and Kubernetes Secrets.
- [Secrets in GitOps](secrets_gitops.md) — SOPS, Sealed Secrets and External Secrets Operator.
- [Linux Hardening](hardening_linux.md) — hardening of the base system.
- [Secure Backup](backup_seguro.md) — encrypted copies and restore verification.

## References

- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/) — see the Password Storage and Cryptographic Storage sheets for up-to-date parameters.
- [`cryptography` (Python)](https://cryptography.io/) — recommended library, with explicit separation of dangerous APIs.
- [argon2-cffi](https://argon2-cffi.readthedocs.io/) — Python bindings to the reference Argon2 implementation.
- [libsodium](https://doc.libsodium.org/) — high-level API that's hard to misuse, with XChaCha20-Poly1305.
- [cryptsetup / LUKS](https://gitlab.com/cryptsetup/cryptsetup) — reference documentation for dm-crypt and LUKS.
