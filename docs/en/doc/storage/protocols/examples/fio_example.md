---
title: "fio — measuring IOPS, latency and bandwidth without fooling yourself"
description: "How to measure storage with fio instead of dd: the anatomy of a job, the four canonical profiles, reading latency percentiles, mistakes that invalidate a test, and comparing NFS with iSCSI."
keywords: "fio, iops, latency, p99, percentiles, benchmark, storage, nfs, iscsi, direct io, iodepth, numjobs, libaio"
tags: ['storage', 'benchmarks', 'performance']
date: 2025-12-07
updated: 2026-09-02
difficulty: intermediate
estimated_time: 18 min
category: Storage
status: published
last_reviewed: 2026-09-02
prerequisites:
  - "A test device or mount point where you can destroy data"
  - "[Storage protocols and metrics](../protocols.md)"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# fio — measuring IOPS, latency and bandwidth without fooling yourself

## The problem

Someone asks "how fast is this disk?" and the answer arrives in the shape of a `dd`:

```bash
dd if=/dev/zero of=/mnt/data/test bs=1M count=1024
# 1073741824 bytes copied, 0.9 s, 1.2 GB/s
```

That number does not describe the disk. It describes how fast the kernel copied a gigabyte into the page cache and handed control back before half of it had touched the physical medium. Even if you add `oflag=direct`, you are still measuring **one** thing: sequential write, one thread, queue depth 1, a single block size and no latency statistics whatsoever. No real workload looks like that.

`fio` (Flexible I/O Tester) exists for precisely the opposite: describing the access pattern you care about and measuring it with statistics you can defend in front of someone who knows the subject.

!!! warning "fio really does write"
    Pointing `filename=` at a block device **destroys its contents**. Use an empty device, a file inside a test filesystem, or `readonly=1` if you are only going to read. Double-check the path before hitting Enter.

## 📋 Table of Contents

- [Why dd is not enough](#why-dd-is-not-enough)
- [Anatomy of a job](#anatomy-of-a-job)
- [The four canonical profiles](#the-four-canonical-profiles)
- [Reading the output](#reading-the-output)
- [Mistakes that invalidate a measurement](#mistakes-that-invalidate-a-measurement)
- [Comparing network protocols](#comparing-network-protocols)
- [Saving results as JSON](#saving-results-as-json)
- [Report template](#report-template)
- [Troubleshooting](#troubleshooting)
- [Best practices](#best-practices)
- [References](#references)

## Why dd is not enough

| Aspect | `dd` | `fio` |
|---|---|---|
| Access pattern | Sequential only | Sequential, random or mixed |
| Concurrency | One thread, queue 1 | `numjobs` × `iodepth` |
| Page cache | On unless `oflag=direct` | Explicit `direct=1` |
| Latency | Not measured | Average, deviation and percentiles |
| Duration | Depends on size | `runtime` + `time_based` |
| Machine-readable output | No | JSON |

`dd` is still good for what it was written to do: copy blocks. As a measuring tool it only answers "how long does it take to copy this?", which is almost never the question.

## Anatomy of a job

A job file is an INI: `[global]` sets what is common and every named section is an independent job.

```ini
# base.fio
[global]
ioengine=libaio
direct=1
time_based=1
runtime=60
ramp_time=10
group_reporting=1
filename=/mnt/testing/fio.dat
size=16G

[randread-4k]
rw=randread
bs=4k
iodepth=32
numjobs=4
```

You run it with `fio base.fio`. The parameters that really move the result are few:

| Parameter | What it does | Why it matters |
|---|---|---|
| `rw` | Pattern: `read`, `write`, `randread`, `randwrite`, `randrw` | It is the difference between measuring bandwidth and measuring IOPS |
| `bs` | Block size | 4k measures operations; 1M measures throughput. They are not the same test |
| `iodepth` | Requests in flight per job | At queue 1 you measure latency; at a deep queue you measure the IOPS ceiling |
| `numjobs` | Concurrent processes | Real parallelism; it multiplies the total queue |
| `direct` | `1` bypasses the page cache | Without it you are measuring RAM |
| `ioengine` | How requests are submitted | It decides whether `iodepth` means anything |
| `runtime` + `time_based` | Fixed duration | Without `time_based`, the job ends once it has walked `size` |
| `ramp_time` | Discards the first seconds | Keeps the warm-up out of the average |

Three details that get overlooked over and over again:

**`iodepth` only has an effect with an asynchronous engine.** With `ioengine=sync` or `psync` each thread submits one request and waits; the effective queue is 1 per job, no matter how big an `iodepth=64` you write. Parallelism then comes only from `numjobs`.

**`libaio` on Linux needs `direct=1`.** The kernel's native AIO is not really asynchronous over buffered I/O, so `ioengine=libaio` with `direct=0` degenerates into synchronous behaviour and the queue goes back to 1. This is the combination that produces those "weird" results nobody can explain.

**The total queue is `numjobs × iodepth`.** Four jobs at `iodepth=32` keep 128 requests in flight. Comparing two systems means matching that figure, not just one of the two numbers.

!!! tip "io_uring as an alternative"
    On kernels and fio builds that support it, `ioengine=io_uring` lowers the per-operation cost compared with `libaio`. Check availability before using it in a job you want to repeat on another machine:
    ```bash
    fio --enghelp | grep -i uring
    ```
    If the goal is to compare two systems, use the same engine on both. Switching engines between runs changes the result all on its own.

## The four canonical profiles

Four tests cover most decisions. Save them as a file and do not improvise them on the command line: a job file is reproducible, a command three screens wide is not.

```ini
# profiles.fio — run one at a time with: fio --section=randread-4k profiles.fio
[global]
ioengine=libaio
direct=1
time_based=1
group_reporting=1
filename=/mnt/testing/fio.dat
size=64G

# 1. Sequential read — bandwidth ceiling
[seqread-1M]
rw=read
bs=1M
iodepth=16
numjobs=1
runtime=60
ramp_time=10

# 2. Sequential write — ingest, backups, restores
[seqwrite-1M]
rw=write
bs=1M
iodepth=16
numjobs=1
runtime=60
ramp_time=10

# 3. Random read 4k — the profile of a database reading
[randread-4k]
rw=randread
bs=4k
iodepth=32
numjobs=4
runtime=120
ramp_time=15

# 4. Random write 4k — the hard test, and the one most often faked
[randwrite-4k]
rw=randwrite
bs=4k
iodepth=32
numjobs=4
runtime=300
ramp_time=60
```

Run the sections **one at a time** with `--section=`. Launching them all together makes them compete for the same device and none of them measures what it claims to measure.

The long `runtime` of the fourth profile is not a whim: sustained random write is where an SSD exhausts its fast cache and drops to its steady-state performance. Sixty seconds usually measure the cache; five minutes start to measure the disk.

## Reading the output

fio prints four blocks per I/O direction: IOPS, bandwidth, latencies and percentiles.

!!! note "Illustrative output"
    The following fragment is **made up to explain the format**. The actual values depend entirely on the hardware, the filesystem, the protocol and the job parameters: do not use them as a reference for anything, and do not compare them with yours.

```text
randread-4k: (groupid=0, jobs=4): err= 0: pid=1234
  read: IOPS=XXXk, BW=YYYMiB/s (ZZZMB/s)(...)
    slat (usec): min=..., max=..., avg=..., stdev=...
    clat (usec): min=..., max=..., avg=A, stdev=S
     lat (usec): min=..., max=..., avg=B, stdev=S
    clat percentiles (usec):
     |  1.00th=[  p1], 50.00th=[ p50], 90.00th=[ p90],
     | 95.00th=[ p95], 99.00th=[ p99], 99.90th=[p999]
```

- **IOPS** — operations per second. The figure that matters with small blocks and random access.
- **BW** — bandwidth. The figure that matters with large blocks and sequential access. It is roughly `IOPS × bs`: if the job is 4k, a high bandwidth would be suspicious.
- **slat** (*submission latency*) — how long the request takes to get into the queue. If it is noticeable, the bottleneck is on the host, not in the storage.
- **clat** (*completion latency*) — from the queue until completion: the latency of the device or the protocol. **lat** is the total as seen by the application, roughly `slat + clat`.

### Why the 99th percentile weighs more than the average

The average hides exactly the behaviour that makes a user complain. An excellent average latency is perfectly compatible with one operation in a hundred taking an order of magnitude longer, and an HTTP request that touches storage twenty times has a high probability of hitting that tail at least once. The perceived latency of a service is set by its high percentile, not by its average.

Minimum practice: always publish p50, p95 and p99 together. If p99 is far above p50, something is saturating intermittently — a cache being flushed, SSD *garbage collection*, network contention — and that "something" is the finding, not noise to be averaged away. And to measure clean latency use `iodepth=1` with `numjobs=1`: with a deep queue you are measuring the waiting time you created yourself, not the device's.

## Mistakes that invalidate a measurement

| Mistake | Symptom | Fix |
|---|---|---|
| No `direct=1` | Impossibly high figures, microsecond latencies | `direct=1` in `[global]` |
| File smaller than RAM | The second run flies | `size` ≥ 2× RAM, or `direct=1` |
| SSD not preconditioned | Performance that drops mid-test | Long `ramp_time` and a `runtime` of minutes |
| *Thin provisioned* volume | Instant reads of blocks never written | Fill the volume before reading |
| Compressible data | Inflated figures on arrays with compression | `refill_buffers`, `buffer_compress_percentage` |
| Other load on the machine | Results that do not repeat | Measure at rest and repeat three times |

The **page cache** is failure number one and the easiest to fix: `direct=1` and done. The rest deserves detail.

**File smaller than RAM.** A `size=1G` on a machine with 64 GB of RAM fits entirely in cache. The first pass measures the disk; the second measures memory. If for whatever reason you cannot use `direct=1`, drop the cache between runs:

```bash
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
```

**Preconditioning.** A freshly formatted SSD has all its blocks free and absorbs writes at the speed of its fast cache. When that cache fills up and the controller has to recycle blocks, performance drops to its steady-state value — the only one that holds up in production. That is why the random write profile carries a `runtime` of minutes and a generous `ramp_time`: you want to measure after the drop, not before.

**Thin provisioning and sparse files.** A block that has never been written is nowhere: the storage layer returns zeros without touching the medium, so measuring random read on a freshly created volume measures the speed at which zeros are generated. Fill it first with a sequential write pass and measure afterwards.

**Compressible data.** fio writes patterns that compress extremely well. On an array with inline compression or deduplication that yields figures you will never see with real data:

```ini
[global]
refill_buffers=1
buffer_compress_percentage=50
dedupe_percentage=20
```

## Comparing network protocols

The same four profiles over an NFS mount point and over an iSCSI LUN describe two different behaviours. Qualitatively, and without numbers because they depend entirely on the specific setup:

- **iSCSI** presents a block device. The filesystem is local, so metadata does not cross the network and the random 4k pattern looks more like that of the underlying disk, with the network latency added on top.
- **NFS** presents a remote filesystem. Metadata operations (open, close, `stat`) are network round trips, so workloads with many small files suffer more than those with one large file. Write behaviour depends heavily on `sync` versus `async` in the export and on the use of `wsize`/`rsize`.
- **In both**, the network latency is added to every operation, and therefore the impact is proportionally much larger on 4k blocks than on 1M blocks. A link that barely affects sequential throughput can cut random IOPS severely.
- **MTU and packet drops** show up in the 99th percentile before they show up in the average. A spiking p99 with a normal p50 is, very often, a network problem and not a disk one.

Context on protocols and metrics in [Storage protocols and metrics](../protocols.md); if you are measuring on Kubernetes volumes, keep in mind the CSI layer described in [Kubernetes CSI](../../kubernetes_csi.md).

!!! warning "Measure the protocol, not the client"
    Before blaming NFS or iSCSI, check that the network delivers what you think it does (`iperf3`) and that the client is not CPU-saturated. A high `slat` in fio's output points at the host; a high `clat`, at the path to the storage.

## Saving results as JSON

Text output is good for looking at once. To compare across runs, save JSON from the start.

```bash
for s in seqread-1M seqwrite-1M randread-4k randwrite-4k; do
  fio --section="$s" profiles.fio \
    --output-format=json --output="results/$(date +%F)-$s.json"
done
```

Extracting the essentials with `jq`:

```bash
jq -r '.jobs[] | [.jobname,
                  .read.iops, .read.bw,
                  .write.iops, .write.bw,
                  .read.clat_ns.percentile."99.000000"] | @tsv' \
  results/*.json
```

Store the job file next to the JSON, along with the output of `fio --version`, `uname -r` and `lsblk`. A result without the context that produced it is not comparable with anything, not even with itself six months from now.

## Report template

```markdown
## Storage measurement — <system> — <date>

**Goal:** (sizing / validating a change / comparing A and B)

### Environment
- Hardware / array, filesystem, mount options
- Kernel, fio version, and the iperf3 result if there is a network involved

### Method
- Job file (attached), size, runtime, ramp_time, numjobs × iodepth
- Preconditioning: yes / no, how. Repetitions: N

### Results
| Profile | IOPS | BW | lat p50 | lat p95 | lat p99 |
|---|---|---|---|---|---|
| seqread 1M | | | | | |
| seqwrite 1M | | | | | |
| randread 4k | | | | | |
| randwrite 4k | | | | | |

### Observations
- Variation between repetitions, behaviour of p99
- Known limitations of this measurement

### Conclusion
```

The limitations section is not filler: it is what stops the number from being quoted a year from now in a context where it does not hold.

## Troubleshooting

| Symptom | Likely cause | Check |
|---|---|---|
| Absurdly high IOPS | `direct=1` missing, or the file fits in RAM | Review `direct` and raise `size` |
| `iodepth` changes nothing | Synchronous engine, or `direct=0` with `libaio` | `ioengine=libaio` **and** `direct=1` |
| `Operation not supported` with `libaio` | The filesystem does not support direct AIO | Try `ioengine=psync` and document it |
| Different results on every pass | Other load on the machine, or missing `ramp_time` | Measure at rest, repeat 3 times |
| Performance drops mid-test | SSD cache exhausted — normal behaviour | Lengthen `runtime`; that is the real figure |
| Instant reads | Blocks never written on a *thin* volume | Fill with a sequential write first |
| `Permission denied` on a device | Missing privilege or the device is in use | `lsblk`, `lsof`, run with permissions |

An `err=` other than 0 in the job header invalidates the whole result: fio keeps printing statistics even when there have been I/O errors. Always look at it before reading the figures.

## Best practices

- **Job files versioned in Git**, never one-liners rebuilt from memory: reproducibility is half the value of a measurement.
- **`direct=1` by default.** If you want to measure with cache, say so explicitly in the report.
- **`ramp_time` always**, and proportional to `runtime`. Without it, the average includes the warm-up.
- **Publish p50, p95 and p99**, not lone averages. An average without percentiles is a marketing figure.
- **Three repetitions minimum** and the spread written down. A single number cannot tell an improvement from a coincidence.
- **Precondition before measuring writes** on any flash medium, and say how you did it.
- **JSON from day one**, with the job file and the context stored alongside.
- **Do not compare vendor figures with yours**: they were measured with another job, another queue and another medium. Compare yourself with yourself, before and after a change.

## References

- [Official fio documentation](https://fio.readthedocs.io/en/latest/fio_doc.html)
- [fio repository](https://github.com/axboe/fio) · [Job file examples](https://github.com/axboe/fio/tree/master/examples)
- [Storage protocols and metrics](../protocols.md) · [Kubernetes CSI](../../kubernetes_csi.md)
