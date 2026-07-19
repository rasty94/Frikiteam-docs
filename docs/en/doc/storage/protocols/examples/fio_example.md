---
title: "fio Example — I/O Testing"
date: 2025-12-07
tags: [storage, fio, benchmarks]
draft: true
updated: 2026-07-18
difficulty: intermediate
estimated_time: 1 min
category: Storage
status: published
last_reviewed: 2026-01-25
prerequisites: ["Basic DevOps knowledge"]
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Example: using `fio` to measure IOPS and latency

This example shows a minimal `fio` job to measure IOPS on 4k random read/write:

```bash
fio --name=randread --ioengine=libaio --direct=1 --rw=randread --bs=4k --size=1G --numjobs=4 --runtime=60 --group_reporting

fio --name=randwrite --ioengine=libaio --direct=1 --rw=randwrite --bs=4k --size=1G --numjobs=4 --runtime=60 --group_reporting
```

Quick interpretation:

- High `IOPS` and low `latency` is desirable for database workloads.
- Adjust `numjobs`, `bs` and `direct` to match your use case.
