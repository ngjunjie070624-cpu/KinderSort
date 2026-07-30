"""
perf_monitor.py — Low-Resource Optimization monitoring for KinderSort.

Wraps psutil to sample THIS process's own CPU% and RSS memory at a low,
fixed frequency. This module is monitoring-only: it does not import,
call, or alter anything in face_detector.py, face_recognizer.py, or
sorter.py. It observes the OS process from the outside — the same way
Task Manager / htop would — so wiring it into the GUI carries zero risk
of touching the detection/recognition pipeline.

WHY psutil fits "Low Resource Optimization" monitoring specifically:
- It reads counters the OS kernel already maintains (Windows Performance
  Counters via psutil's backend, /proc on Linux) rather than instrumenting
  the pipeline itself, so it adds negligible CPU/RAM cost of its own —
  appropriate for a project whose whole point is staying CPU-only and
  low-resource.
- Process.cpu_percent(interval=None) is *non-blocking*: unlike passing
  interval=1 (which sleeps the calling thread for a second per call), the
  no-interval form returns immediately using the delta since the previous
  call. That means periodic sampling from the GUI thread cannot stall the
  UI or slow down the sorting worker thread.
- Sampling the *process* (psutil.Process(pid)) rather than the whole
  system isolates KinderSort's own footprint from whatever else happens
  to be running on the teacher's machine, which is what "is this app
  staying inside a low-resource budget" actually needs to measure.

CPU NORMALIZATION (fixes 620% display on multi-core CPUs):
- psutil reports process CPU as the sum of utilization across all logical
  cores. On a 6-core / 12-thread CPU, a fully busy process can read up to
  ~1200%. Dividing by the logical core count converts this to overall
  system CPU share (0–100%), matching Task Manager's "overall CPU" view
  and making assignment statistics easier to interpret.
"""

import os
import time

import psutil


class PerformanceMonitor:
    """Tracks this process's CPU% and memory footprint over one sort run.

    Usage mirrors the existing elapsed-time ticker pattern already in
    main.py (start() / periodic sample() / a final summary()) so it slots
    into the same GUI lifecycle without new concepts.
    """

    def __init__(self) -> None:
        """Bind to the current OS process; no sampling happens until start()."""
        self._process = psutil.Process(os.getpid())
        # Cached once: used to convert psutil's per-core sum into 0–100%
        # overall CPU utilization for this process.
        self._logical_cpus: int = psutil.cpu_count(logical=True) or 1
        self._start_time: float | None = None
        self._cpu_samples: list[float] = []
        self._memory_samples: list[float] = []
        self._peak_memory_mb: float = 0.0

    @staticmethod
    def _normalize_cpu_percent(raw_cpu_percent: float, logical_cpus: int) -> float:
        """Convert psutil's multi-core sum into overall CPU usage (0–100%).

        Example: 620% on 12 threads → 51.7%, meaning the process is using
        roughly half of total available CPU capacity — not 620% of the machine.
        """
        return min(max(raw_cpu_percent / logical_cpus, 0.0), 100.0)

    def start(self) -> None:
        """Begin a monitoring run.

        Primes cpu_percent() so the first real sample reflects usage since
        start(), not since the whole process launched. cpu_percent() always
        returns a meaningless value (0.0, or a stale figure) on its very
        first call because it has no prior timestamp to measure a delta
        against — the CustomTkinter app may have been sitting open for
        minutes before "Start Sorting" is clicked, and without this priming
        call the first reading would (mis)report an average since app
        launch, understating load once the person actually starts sorting.
        """
        self._start_time = time.monotonic()
        self._cpu_samples = []
        self._memory_samples = []
        self._peak_memory_mb = 0.0
        self._process.cpu_percent(interval=None)  # prime; discard the 0.0

    def sample(self) -> dict:
        """Take one lightweight, non-blocking sample.

        Cheap enough to call every second from the GUI's own .after() timer
        (see main.py's _perf_tick) without adding a measurable CPU/RAM
        burden of its own — this is just two syscalls read from kernel
        counters, no image, model, or file I/O involved.
        """
        raw_cpu = self._process.cpu_percent(interval=None)
        cpu_percent = self._normalize_cpu_percent(raw_cpu, self._logical_cpus)
        memory_mb = self._process.memory_info().rss / (1024 * 1024)

        self._cpu_samples.append(cpu_percent)
        self._memory_samples.append(memory_mb)
        if memory_mb > self._peak_memory_mb:
            self._peak_memory_mb = memory_mb

        elapsed_sec = (time.monotonic() - self._start_time) if self._start_time else 0.0
        avg_cpu_percent = sum(self._cpu_samples) / len(self._cpu_samples)
        avg_memory_mb = sum(self._memory_samples) / len(self._memory_samples)

        return {
            "cpu_percent": cpu_percent,
            "avg_cpu_percent": avg_cpu_percent,
            "memory_mb": memory_mb,
            "peak_memory_mb": self._peak_memory_mb,
            "avg_memory_mb": avg_memory_mb,
            "elapsed_sec": elapsed_sec,
        }

    def summary(self, images_processed: int) -> dict:
        """Compute the end-of-run aggregate figures for the completion summary.

        Args:
            images_processed: Count of event images the sorter finished,
                supplied by the caller (main.py already tracks this from the
                existing sort_all progress callback — no sorter.py change
                needed to obtain it).
        """
        elapsed_sec = (time.monotonic() - self._start_time) if self._start_time else 0.0
        avg_cpu_percent = (
            sum(self._cpu_samples) / len(self._cpu_samples) if self._cpu_samples else 0.0
        )
        avg_memory_mb = (
            sum(self._memory_samples) / len(self._memory_samples)
            if self._memory_samples
            else 0.0
        )
        avg_time_per_image_sec = (elapsed_sec / images_processed) if images_processed else 0.0
        return {
            "cpu_percent": self._cpu_samples[-1] if self._cpu_samples else 0.0,
            "avg_cpu_percent": avg_cpu_percent,
            "memory_mb": self._memory_samples[-1] if self._memory_samples else 0.0,
            "peak_memory_mb": self._peak_memory_mb,
            "avg_memory_mb": avg_memory_mb,
            "images_processed": images_processed,
            "total_time_sec": elapsed_sec,
            "avg_time_per_image_sec": avg_time_per_image_sec,
        }
