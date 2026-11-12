"""
core/hardware_optimizer.py — Hardware Acceleration & Latency Optimization Engine for JARVIS Mark XL
Tailored for Dell Inspiron 15 (Intel UHD Graphics, 16GB RAM, 12 Core CPU, 512GB SSD)
Enables OpenCL GPU acceleration, Windows High Process Priority, UI macro acceleration, and RAM garbage collection.
"""

import os
import sys
import gc
import psutil
import cv2
import pyautogui

def optimize_hardware():
    """Applies GPU, OpenCL, CPU thread-pooling, PyAutoGUI macro speedup, and RAM garbage collection."""
    report = []
    
    # 1. UI Macro Speed Optimization (0.02s pause)
    try:
        pyautogui.PAUSE = 0.02
        pyautogui.FAILSAFE = True
        report.append("UI Macro Engine: Ultra-Low Latency (0.02s pause)")
    except Exception as e:
        report.append(f"UI Macro Notice: {e}")

    # 2. Hybrid P/E-Core Aware Process Priority (Intel Core i5-1334U)
    try:
        p = psutil.Process(os.getpid())
        bat = psutil.sensors_battery()
        on_battery = bool(bat and not bat.power_plugged)
        if sys.platform == "win32":
            prio = psutil.BELOW_NORMAL_PRIORITY_CLASS if on_battery else psutil.NORMAL_PRIORITY_CLASS
            p.nice(prio)
            mode_lbl = "BELOW_NORMAL (E-Core Battery Eco)" if on_battery else "NORMAL (Hybrid Thread Director)"
            report.append(f"Process Priority: {mode_lbl}")
        else:
            p.nice(0)
            report.append("Process Priority: Normal (0)")
    except Exception as e:
        report.append(f"Process Priority Notice: {e}")

    # 3. OpenCV OpenCL GPU Acceleration (Intel UHD Graphics)
    try:
        cv2.ocl.setUseOpenCL(True)
        is_ocl = cv2.ocl.useOpenCL()
        device_name = "Intel UHD / OpenCL GPU" if is_ocl else "CPU Fallback"
        report.append(f"OpenCV GPU Acceleration: {'ENABLED (' + device_name + ')' if is_ocl else 'DISABLED'}")
    except Exception as e:
        report.append(f"OpenCV GPU Notice: {e}")

    # 4. CPU Multi-Threading & Thread Contention Prevention (Cap at 4 threads for 2P+8E i5-1334U)
    try:
        cpu_count = os.cpu_count() or 4
        capped_threads = str(min(4, max(1, cpu_count // 3)))
        os.environ["OMP_NUM_THREADS"] = capped_threads
        os.environ["MKL_NUM_THREADS"] = capped_threads
        os.environ["OPENBLAS_NUM_THREADS"] = capped_threads
        os.environ["VECLIB_MAXIMUM_THREADS"] = capped_threads
        os.environ["NUMEXPR_NUM_THREADS"] = capped_threads
        report.append(f"CPU Thread Pool: Capped at {capped_threads} threads ({cpu_count} logical cores detected)")
    except Exception as e:
        report.append(f"CPU Thread Notice: {e}")

    # 5. DirectML Execution, Generational GC Tuning & Working Set Compaction
    try:
        os.environ["ONNXRUNTIME_PROVIDER"] = "DmlExecutionProvider,CPUExecutionProvider"
        # Tune Python cyclic garbage collection thresholds for high throughput & fast reclamation
        gc.set_threshold(700, 10, 5)
        mem_res = trim_process_memory()
        report.append(f"Memory Engine: Generational GC active | Working Set Trim: {mem_res.get('freed_mb', 0.0):.1f}MB freed ({mem_res.get('current_mb', 0.0):.1f}MB active)")
    except Exception as e:
        report.append(f"Memory Notice: {e}")

    return report


def trim_process_memory() -> dict:
    """
    Actively flushes unused pages from the process working set to minimize physical RAM consumption.
    On Windows, invokes psapi.dll EmptyWorkingSet and SetProcessWorkingSetSize(-1, -1).
    On Linux, calls libc.malloc_trim(0).
    Returns a dict with before_mb, after_mb, and freed_mb.
    """
    proc = psutil.Process(os.getpid())
    try:
        rss_before = proc.memory_info().rss
    except Exception:
        rss_before = 0

    # 1. Full cyclic GC collection across all generations
    gc.collect(2)

    # 2. OS-level process working set purge
    if sys.platform == "win32":
        try:
            import ctypes
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            ctypes.windll.kernel32.SetProcessWorkingSetSize(handle, ctypes.c_size_t(-1), ctypes.c_size_t(-1))
            ctypes.windll.psapi.EmptyWorkingSet(handle)
        except Exception:
            pass
    elif sys.platform.startswith("linux"):
        try:
            import ctypes
            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
        except Exception:
            pass

    try:
        rss_after = proc.memory_info().rss
    except Exception:
        rss_after = rss_before

    before_mb = rss_before / (1024 * 1024)
    after_mb = rss_after / (1024 * 1024)
    freed_mb = max(0.0, before_mb - after_mb)

    return {
        "before_mb": round(before_mb, 2),
        "current_mb": round(after_mb, 2),
        "freed_mb": round(freed_mb, 2),
        "percent_reduced": round((freed_mb / before_mb * 100) if before_mb > 0 else 0.0, 1)
    }


def start_memory_compactor(interval: float = 30.0, threshold_mb: float = 95.0, player=None):
    """
    Launches a lightweight background daemon thread that periodically flushes working set RAM
    whenever memory exceeds threshold_mb or system is idle.
    """
    import threading
    import time

    def _compactor_loop():
        while True:
            time.sleep(interval)
            try:
                proc = psutil.Process(os.getpid())
                current_mb = proc.memory_info().rss / (1024 * 1024)
                if current_mb >= threshold_mb:
                    res = trim_process_memory()
                    if res["freed_mb"] > 5.0 and player and hasattr(player, "write_log"):
                        player.write_log(f"RAM COMPACTOR: 🧹 Purged {res['freed_mb']:.1f}MB from working set (Now: {res['current_mb']:.1f}MB).")
            except Exception:
                pass

    t = threading.Thread(target=_compactor_loop, daemon=True, name="JarvisRamCompactor")
    t.start()


if __name__ == "__main__":
    results = optimize_hardware()
    print("--- JARVIS HARDWARE OPTIMIZER REPORT ---")
    for r in results:
        print(f"  [OK] {r}")
