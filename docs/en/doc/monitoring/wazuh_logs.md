---
title: "Observability: Centralized Logging with Wazuh"
description: "Integrating application logs into the Wazuh SIEM: agent configuration, security analysis and auditing"
keywords: "wazuh, logs, siem, security, monitoring"
tags: [monitoring, logs, wazuh, siem, security]
updated: 2026-01-25
difficulty: intermediate
estimated_time: 1 min
category: Monitoring
status: published
last_reviewed: 2026-01-25
prerequisites: ["Basic DevOps knowledge"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Observability: Centralized Logging with Wazuh

Guide to integrating application logs into the Wazuh SIEM platform.

## Overview

Integration of structured (JSON) logs for security analysis and auditing.

## Agent Configuration

Add the following block to `ossec.conf`:

```xml
<localfile>
  <location>/var/log/app/output.json</location>
  <log_format>json</log_format>
  <label key="app_name">frikiteam-service</label>
</localfile>
```

## References

- [Wazuh Documentation](https://documentation.wazuh.com/)
