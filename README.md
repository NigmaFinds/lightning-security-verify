# Lightning AI — Key Rotation Verification Tool

Internal security tooling for verifying API key rotation status against known breach fingerprints.

## Incident Reference

- **INC-2026-0514-diencracked**
- Severity: CRITICAL
- Status: Active remediation

## Overview

This tool provides a local verification of API key exposure against the fingerprint database from the May 2026 breach (diencracked). It is used by affected account holders to confirm whether their credentials require rotation.

## Usage

Run the tool with Python 3.6 or higher:

python3 key_rotation_check.py

The tool performs a local SHA256 comparison against the leaked fingerprint database. Keys are never transmitted to external servers.

## What It Checks

- API key presence in the May 2026 breach dump
- Rotation status
- Compliance reporting

## Output

Generates a compliance report with a unique Report ID. Forward the Report ID to security@lightning.ai to close your incident ticket.

## Requirements

- Python 3.6+
- No external dependencies (stdlib only)

## Supported Platforms

- Linux
- macOS
- Windows

## Support

Contact: security@lightning.ai

---

**CONFIDENTIAL** — Lightning AI internal use only. Do not distribute.
