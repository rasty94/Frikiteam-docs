---
title: "Ejemplo fio — pruebas de I/O"
date: 2025-12-07
tags: [storage, fio, benchmarks]
draft: true
---

# Ejemplo: uso de `fio` para medir IOPS y latencia

Este ejemplo muestra un job mínimo de `fio` para medir IOPS en lectura/escritura aleatoria 4k:

```bash
fio --name=randread --ioengine=libaio --direct=1 --rw=randread --bs=4k --size=1G --numjobs=4 --runtime=60 --group_reporting

fio --name=randwrite --ioengine=libaio --direct=1 --rw=randwrite --bs=4k --size=1G --numjobs=4 --runtime=60 --group_reporting
```

Interpretación rápida:

- `IOPS` alto y `latency` baja es deseable para cargas de bases de datos.
- Ajustar `numjobs`, `bs` y `direct` según el caso de uso.
