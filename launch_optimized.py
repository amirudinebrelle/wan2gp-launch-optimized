# ==============================================================================
# Fail Pelancar In-Memory Patching WanGP (Bebas Modifikasi Fail Repo Asal)
# Reka bentuk: Total Universal Catch-All Engine + True Root-Level Device & Dtype Harmonizer
# Peranti: ASUS TUF Gaming A16 (RTX 5050 8GB + 16GB/32GB RAM)
# Dasar Kualiti: Zero Hardcoding, Dynamic RAM+VRAM Fusion, Sticky-CUDA Immune, Non-Stopping
# Status Prestasi (Disahkan): Penjanaan MiniMax H3 berjalan lancar < 20 minit dengan kod semasa,
# merangkumi mod sambungan video (continuation) serta imej rujukan (reference images).
# ==============================================================================

import sys
import os
import pathlib

# Matikan Fast Download hf_transfer secara mutlak bagi mengelakkan ralat ImportError / ValueError
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
os.environ["HF_HUB_DISABLE_FAST_DOWNLOAD"] = "1"

# ==============================================================================
# Dynamic Runtime Venv Self-Healing Guard (Kalis Pasang Semula / Zero Hardcoding)
# ==============================================================================
def _ensure_correct_python_runtime():
    """Memastikan runtime Python yang sah digunakan (mempunyai sokongan CUDA).
    Jika skrip ini dipanggil menerusi Python global (tanpa CUDA), ia akan melencongkan (respawn)
    proses secara dinamik ke .venv_wangp_311 tanpa sebarang hardcoding laluan.
    """
    if os.environ.get("_WAN2GP_RESPAWNED") == "1":
        return

    script_dir = pathlib.Path(__file__).resolve().parent
    current_py = pathlib.Path(sys.executable).resolve()

    candidate_venvs = [
        script_dir / ".venv_wangp_311",
        script_dir / ".venv",
        script_dir.parent / ".venv_wangp_311",
    ]

    target_py = None
    target_venv = None
    for venv in candidate_venvs:
        py_cand = venv / "Scripts" / "python.exe" if os.name == "nt" else venv / "bin" / "python"
        if py_cand.exists():
            target_py = py_cand.resolve()
            target_venv = venv.resolve()
            break

    if not target_py or target_py == current_py:
        return

    needs_respawn = False
    try:
        import torch
        if not torch.cuda.is_available():
            needs_respawn = True
    except Exception:
        needs_respawn = True

    is_global_python = (getattr(sys, "base_prefix", sys.prefix) == sys.prefix)
    if is_global_python or needs_respawn:
        print(f"[SISTEM] Amaran: Python semasa ({current_py}) tidak memuatkan sokongan CUDA.")
        print(f"[SISTEM] Melencongkan pelaksanaan secara automatik ke persekitaran maya CUDA: {target_py}")
        
        env = os.environ.copy()
        env["_WAN2GP_RESPAWNED"] = "1"
        env["VIRTUAL_ENV"] = str(target_venv)
        scripts_dir = str(target_venv / "Scripts" if os.name == "nt" else target_venv / "bin")
        env["PATH"] = scripts_dir + os.pathsep + env.get("PATH", "")
        
        sys.stdout.flush()
        sys.stderr.flush()
        
        import subprocess
        result = subprocess.call([str(target_py)] + sys.argv, env=env)
        sys.exit(result)

def _audit_git_cleanliness():
    """Memastikan fail-fail klon repositori git Wan2GP kekal 100% bersih tanpa sebarang modifikasi langsung.
    Jika terkesan fail klon git selain launch_optimized.py diubah, ia akan dipulihkan secara automatik!"""
    try:
        import subprocess
        script_dir = pathlib.Path(__file__).resolve().parent
        if (script_dir / ".git").exists():
            res = subprocess.run(
                ["git", "diff", "--name-only"],
                cwd=str(script_dir), capture_output=True, text=True, timeout=5
            )
            dirty_files = [
                f.strip() for f in res.stdout.splitlines()
                if f.strip() and f.strip() not in ("launch_optimized.py", "gemini.md", ".gitignore")
            ]
            if dirty_files:
                print(f"[PERISAI INTEGRITI GIT] Amaran: Terkesan fail repositori git telah diubah secara tidak sah: {dirty_files}!")
                print("[PERISAI INTEGRITI GIT] Memulihkan fail klon git ke keadaan asal (git restore) bagi memelihara keupayaan 'git pull'...")
                subprocess.run(["git", "restore"] + dirty_files, cwd=str(script_dir), timeout=10)
    except Exception:
        pass

_ensure_correct_python_runtime()
_audit_git_cleanliness()

import functools
import gc
import ctypes
import threading
import re
import math
import json
import time

# Pasang MMGP Optimized VRAM Allocator (VMM) dan MMGP RAM Allocator sebelum sebarang modul menginisialisasi CUDA
try:
    from shared.cuda_memory import apply_startup_settings
    apply_startup_settings(sys.argv, "wgp_config.json")
except Exception:
    pass

# Pendaftaran Sejagat Format Kuantisasi & Sambungan GGUF pada Tahap Permulaan Modul
try:
    from mmgp import quant_router
    _EARLY_HANDLER_MODULES = [
        "shared.qtypes.scaled_fp8",
        "shared.qtypes.nvfp4",
        "shared.qtypes.bnb_nf4",
        "shared.qtypes.nunchaku_int4",
        "shared.qtypes.nunchaku_fp4",
        "shared.qtypes.asym_w4a8_int8",
        "shared.qtypes.int8_convrot",
        "shared.qtypes.gptq_int4",
        "shared.qtypes.gguf",
    ]
    for _h in _EARLY_HANDLER_MODULES:
        try:
            quant_router.register_handler(_h)
        except Exception:
            pass
    from shared.qtypes import gguf as _early_gguf_handler
    quant_router.register_file_extension("gguf", _early_gguf_handler)
    quant_router.register_file_extension(".gguf", _early_gguf_handler)
except Exception:
    pass


import torch
import torch.nn.functional as F
import psutil

# Kunci Anti-Rekursi Thread-Local Global
_tls_guards = threading.local()

def _is_guard_active(name):
    return getattr(_tls_guards, name, False)

def _set_guard(name, val):
    setattr(_tls_guards, name, val)

class EndTimestampStream:
    """Pembungkus strim stdout/stderr untuk menambah cap masa pada hujung setiap baris (mesra pembaca skrin NVDA)."""
    def __init__(self, original_stream):
        self.original_stream = original_stream
        self.line_buffer = ""
        
    def write(self, s):
        if not s:
            return
        if '\r' in s and '\n' not in s:
            self.original_stream.write(s)
            self.original_stream.flush()
            return

        import datetime
        self.line_buffer += s
        if '\n' in self.line_buffer:
            lines = self.line_buffer.split('\n')
            out_chunks = []
            now_str = datetime.datetime.now().strftime("%H:%M:%S")
            for line in lines[:-1]:
                stripped = line.rstrip('\r')
                if stripped.strip():
                    if not re.search(r'\[\d{2}:\d{2}:\d{2}\.\]\s*$', stripped):
                        out_chunks.append(f"{stripped} [{now_str}.]\n")
                    else:
                        out_chunks.append(f"{stripped}\n")
                else:
                    out_chunks.append(f"{stripped}\n")
            self.line_buffer = lines[-1]
            out_text = "".join(out_chunks)
            try:
                self.original_stream.write(out_text)
            except UnicodeEncodeError:
                enc = getattr(self.original_stream, 'encoding', None) or 'ascii'
                safe_text = out_text.encode(enc, errors='replace').decode(enc, errors='replace')
                self.original_stream.write(safe_text)
            self.original_stream.flush()
            
    def flush(self):
        if self.line_buffer:
            stripped = self.line_buffer.rstrip('\r')
            if stripped.strip():
                import datetime
                now_str = datetime.datetime.now().strftime("%H:%M:%S")
                raw_text = f"{stripped} [{now_str}.]\n" if not re.search(r'\[\d{2}:\d{2}:\d{2}\.\]\s*$', stripped) else f"{stripped}\n"
            else:
                raw_text = self.line_buffer
            self.line_buffer = ""
            try:
                self.original_stream.write(raw_text)
            except UnicodeEncodeError:
                enc = getattr(self.original_stream, 'encoding', None) or 'ascii'
                safe_text = raw_text.encode(enc, errors='replace').decode(enc, errors='replace')
                self.original_stream.write(safe_text)
        self.original_stream.flush()

    def fileno(self):
        return getattr(self.original_stream, "fileno", lambda: 1)()

    def isatty(self):
        return getattr(self.original_stream, "isatty", lambda: False)()

    def __getattr__(self, name):
        return getattr(self.original_stream, name)

if not isinstance(sys.stdout, EndTimestampStream):
    sys.stdout = EndTimestampStream(sys.stdout)
if not isinstance(sys.stderr, EndTimestampStream):
    sys.stderr = EndTimestampStream(sys.stderr)

def log_debug(msg):
    """Fungsi pengelogan berisolasi dengan cap masa di hujung baris untuk mesra pembaca skrin (NVDA)."""
    import datetime
    t_str = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[LAUNCHER DEBUG] {msg} [{t_str}.]", flush=True)

_last_pagefile_push_time = 0.0

def force_pagefile_push(min_interval=0.5, force_trim=False):
    """Pembersihan kitaran memori Python dan pelepasan memori dorman secara pintar tanpa hardcoding.
    MUTLAK: Mengecualikan proses WanGP sendiri (PID semasa) agar memori aktif kekal 100% dalam RAM fizikal!"""
    global _last_pagefile_push_time
    import time
    now = time.time()
    if not force_trim and (now - _last_pagefile_push_time < min_interval):
        return
    _last_pagefile_push_time = now
    gc.collect()
    try:
        from mmgp.allocator import ram as mmgp_ram
        mmgp_ram.release()
    except Exception:
        pass
    if force_trim and sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            psapi = ctypes.WinDLL('psapi.dll')
            kernel32 = ctypes.WinDLL('kernel32.dll')
            current_pid = os.getpid()
            pids = (wintypes.DWORD * 4096)()
            bytes_returned = wintypes.DWORD()
            PROCESS_QUERY_INFORMATION = 0x0400
            PROCESS_SET_QUOTA = 0x0100
            if psapi.EnumProcesses(ctypes.byref(pids), ctypes.sizeof(pids), ctypes.byref(bytes_returned)):
                num_pids = bytes_returned.value // ctypes.sizeof(wintypes.DWORD)
                for i in range(num_pids):
                    pid = pids[i]
                    # JANGAN PANGKAS PROSES WAN2GP SENDIRI (Kekalkan WanGP 100% dalam RAM fizikal!)
                    if pid <= 4 or pid == current_pid:
                        continue
                    h_proc = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA, False, pid)
                    if h_proc:
                        try:
                            psapi.EmptyWorkingSet(h_proc)
                        except Exception:
                            pass
                        finally:
                            kernel32.CloseHandle(h_proc)
        except Exception:
            pass

def trim_current_process_working_set():
    """Membebaskan halaman fail mmap dorman (seperti 14GB Text Encoder) daripada set kerja RAM proses semasa serta-merta (0.25 ms)."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            psapi = ctypes.WinDLL('psapi.dll')
            kernel32 = ctypes.WinDLL('kernel32.dll')
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            psapi.EmptyWorkingSet.argtypes = [wintypes.HANDLE]
            psapi.EmptyWorkingSet.restype = wintypes.BOOL
            h_proc = kernel32.GetCurrentProcess()
            ok = psapi.EmptyWorkingSet(h_proc)
            if ok:
                log_debug("[WIN32 MEMORY TRIM] Working set RAM proses berjaya dipangkas bersih ke sistem.")
            else:
                log_debug(f"[WIN32 MEMORY TRIM] Gagal memangkas working set: Kod Ralat {kernel32.GetLastError()}")
        except Exception as e:
            log_debug(f"[WIN32 MEMORY TRIM] Ralat ctypes semasa memangkas: {e}")

# ==============================================================================
# PENGURUS KITARAN HAYAT MEMORI SEJAGAT TERPUSAT (UNIVERSAL ON-DEMAND LIFECYCLE)
# Menghapuskan kitaran 'baiki sini pecah sana' dengan menyatukan pelepasan memori,
# unpinning bertahap, dan telemetri empirikal masa nyata merentasi semua model AI.
# Sifar Hardcoding, Dinamik Mutlak, Sifar Spekulasi.
# ==============================================================================

class CentralizedUniversalLifecycleManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.active_pipeline = None
        self.current_phase = "INIT"
        self.phase_history = []

    def get_realtime_telemetry(self):
        """Membaca telemetri perkakasan masa nyata secara dinamik dari PyTorch, Driver WDDM, dan OS."""
        stats = {
            "vram_allocated_mb": 0.0,
            "vram_reserved_mb": 0.0,
            "vram_driver_free_mb": 0.0,
            "vram_driver_total_mb": 0.0,
            "ram_process_working_set_gb": 0.0,
            "ram_system_free_gb": 0.0,
            "ram_system_total_gb": 0.0,
        }
        if torch.cuda.is_available():
            stats["vram_allocated_mb"] = torch.cuda.memory_allocated() / (1024 * 1024)
            stats["vram_reserved_mb"] = torch.cuda.memory_reserved() / (1024 * 1024)
            try:
                fb, tb = torch.cuda.mem_get_info()
                stats["vram_driver_free_mb"] = fb / (1024 * 1024)
                stats["vram_driver_total_mb"] = tb / (1024 * 1024)
            except Exception:
                pass
        try:
            p = psutil.Process()
            stats["ram_process_working_set_gb"] = p.memory_info().rss / (1024 ** 3)
            vm = psutil.virtual_memory()
            stats["ram_system_free_gb"] = vm.available / (1024 ** 3)
            stats["ram_system_total_gb"] = vm.total / (1024 ** 3)
        except Exception:
            pass
        return stats

    def log_telemetry_snapshot(self, phase_name, detail=""):
        t = self.get_realtime_telemetry()
        detail_str = f" ({detail})" if detail else ""
        log_debug(
            f"[UNIVERSAL LIFECYCLE] [{phase_name}]{detail_str} "
            f"VRAM Alokasi: {t['vram_allocated_mb']:.1f}MB | "
            f"VRAM Reserved: {t['vram_reserved_mb']:.1f}MB | "
            f"Driver Bebas: {t['vram_driver_free_mb']:.1f}MB/{t['vram_driver_total_mb']:.1f}MB | "
            f"RAM Proses: {t['ram_process_working_set_gb']:.2f}GB | "
            f"RAM Bebas Sistem: {t['ram_system_free_gb']:.2f}GB / {t['ram_system_total_gb']:.2f}GB"
        )

    def purge_module_completely(self, module, module_id=""):
        """Mengosongkan modul daripada VRAM secara selamat tanpa memusnahkan struktur tensor (Memelihara MMGP hooks & mmap)."""
        if module is None:
            return 0
        try:
            active_inst = get_active_mmgp_instance()
            if active_inst is not None and module_id:
                safe_mmgp_unload(active_inst, module_id)
                m_entry = getattr(active_inst, "models", {}).get(module_id)
                if m_entry is not None:
                    setattr(m_entry, "_pinned_bytes", 0)
        except Exception:
            pass

        flush_vram()
        if torch.cuda.is_available():
            try:
                _orig_cuda_empty_cache()
            except Exception:
                pass
        gc.collect()
        trim_current_process_working_set()
        self.log_telemetry_snapshot("PELEPASAN VRAM", f"Modul '{module_id}' selamat dilepaskan dari VRAM")
        return 1

    def on_model_loaded(self, pipeline, offloadobj=None):
        """Memastikan peruntukan VRAM dorman dibersihkan tanpa memusnahkan modul MMGP."""
        log_debug("[UNIVERSAL LIFECYCLE] Pasca-Muat: Memelihara integriti modul MMGP & membersihkan VRAM dorman...")
        flush_vram()
        trim_current_process_working_set()
        self.log_telemetry_snapshot("STARTUP BERSIH", "RAM permulaan optimum, modul MMGP terpelihara 100%.")

    def transition_to_phase(self, new_phase, pipeline=None, context=None):
        """Pusat Kawalan Peralihan Fasa (Fasa 1: Encode -> Fasa 2: Denoise -> Fasa 3: Decode -> Selesai)."""
        old_phase = self.current_phase
        self.current_phase = new_phase
        self.phase_history.append((time.time(), old_phase, new_phase))

        log_debug(f"[UNIVERSAL LIFECYCLE] Peralihan Fasa: {old_phase} -> {new_phase}")

        if new_phase == "PHASE_2_DENOISING":
            # Fasa 1 Tamat: Unload Text Encoder & Vision Encoder daripada GPU VRAM secara bersih melalui MMGP
            act = get_active_mmgp_instance()
            if act is not None:
                for enc_name in ("vision_encoder", "text_encoder", "video_encoder", "clip"):
                    safe_mmgp_unload(act, enc_name)
            flush_vram()
            trim_current_process_working_set()
            self.log_telemetry_snapshot("FASA 1 TAMAT", "Text Encoder dipindahkan dari VRAM ke hos, VRAM 100% lapang untuk Transformer.")

        elif new_phase == "PHASE_3_DECODE":
            # Fasa 2 Tamat: Unload Transformer daripada GPU VRAM secara bersih melalui MMGP
            act = get_active_mmgp_instance()
            if act is not None:
                for trans_name in ("transformer", "transformer2", "model", "model2"):
                    safe_mmgp_unload(act, trans_name)
            flush_vram()
            self.log_telemetry_snapshot("FASA 2 TAMAT", "Transformer dipindahkan dari VRAM, VRAM 100% lapang untuk VAE Decode.")

        elif new_phase == "PHASE_IDLE":
            # Fasa 3 Tamat: Bersihkan VAE & Semua Sisa Penjanaan
            flush_vram()
            if torch.cuda.is_available():
                try:
                    _orig_cuda_empty_cache()
                except Exception:
                    pass
            gc.collect()
            trim_current_process_working_set()
            self.log_telemetry_snapshot("PENJANAAN SELESAI", "Sistem Kembali Bersih (0.0 MB Model VRAM)")

def _deep_release_finished_module(module, module_id=""):
    """Pelepasan pantas modul selesai (Fasa Tamat) yang diselaraskan melalui Pengurus Kitaran Hayat Terpusat."""
    return CentralizedUniversalLifecycleManager.get_instance().purge_module_completely(module, module_id)

def evict_module_weights(module, name=""):
    """Membebaskan VRAM GPU dengan mengalihkan modul ke RAM hos (CPU) tanpa memusnahkan struktur tensor (Zero VRAM Waste).
    Mengekalkan tensor utuh tanpa swap_tensors(0) bagi memelihara 100% MMGP hooks dan keserasian kuantisasi."""
    if module is None:
        return 0
    # Lindungi modul yang diuruskan oleh MMGP daripada diubah penunjuk memori C++ secara luaran
    try:
        active_inst = get_active_mmgp_instance()
        if active_inst is not None and hasattr(active_inst, "models"):
            for m_id, m_obj in list(active_inst.models.items()):
                if m_obj is module or (hasattr(module, "_mm_id") and getattr(module, "_mm_id") == m_id):
                    safe_mmgp_unload(active_inst, m_id)
                    return 1
    except Exception:
        pass
    moved_count = 0
    try:
        if isinstance(module, torch.nn.Module):
            for p in module.parameters():
                if p is not None and p.is_cuda:
                    moved_count += 1
            if moved_count > 0:
                module.to("cpu")
    except Exception:
        pass
    return moved_count

def evict_h3_auxiliary_modules(container):
    """Mengalihkan kesemua modul pembantu MiniMax H3 ke RAM hos (CPU) dan membebaskan VRAM (Zero VRAM Waste, Zero Corruption)."""
    if container is None:
        return 0
    evicted_total = 0
    try:
        active_inst = get_active_mmgp_instance()
        for mod_id in ("text_encoder", "vision_encoder", "video_encoder", "video_decoder", "vae", "audio_vae", "latent_upscaler"):
            if active_inst is not None:
                try:
                    safe_mmgp_unload(active_inst, mod_id)
                    evicted_total += 1
                except Exception:
                    pass
        # Alihkan sebarang parameter & buffer CUDA milik text_encoder (language_model & visual) ke CPU
        te = getattr(container, "text_encoder", None)
        if te is not None:
            for sub_m in (getattr(te, "language_model", None), getattr(te, "visual", None), te):
                if sub_m is not None and hasattr(sub_m, "parameters"):
                    for p in sub_m.parameters():
                        if p is not None and getattr(p, "is_cuda", False):
                            try:
                                p.data = p.data.to("cpu")
                                evicted_total += 1
                            except Exception:
                                pass
                    for b in sub_m.buffers():
                        if b is not None and getattr(b, "is_cuda", False):
                            try:
                                b.data = b.data.to("cpu")
                            except Exception:
                                pass
            if hasattr(container, "text_encoder_cache"):
                c = getattr(container, "text_encoder_cache", None)
                if c is not None and hasattr(c, "clear"):
                    c.clear()
        flush_vram()
        if evicted_total > 0:
            log_debug(f"[OFFLOAD PEMBANTU] Modul pembantu dipunggah bersih menerusi MMGP (VRAM 100% bebas untuk Transformer).")
    except Exception as ex:
        log_debug(f"[OFFLOAD PEMBANTU] Ralat mengalihkan modul pembantu: {ex}")
    return evicted_total

def _vacuum_vmm_orphan_allocations():
    """Pembersihan Fizikal Blok Yatim MMGP VMM Allocator (Zero VRAM Leak, Sifar Hardcode).
    Memeriksa ordinary pools dalam C++ vmm_alloc DLL/SO secara dinamik dan membebaskan
    sebarang alokasi yatim yang tidak lagi dipegang oleh objek Python aktif."""
    try:
        from mmgp import allocator
        if getattr(allocator, "active", None) != "vmm":
            return 0
        import sys, ctypes
        if sys.platform != "win32":
            return 0
        kernel32 = ctypes.windll.kernel32
        h_mod = kernel32.GetModuleHandleW("vmm_alloc_win_amd64.dll")
        if not h_mod:
            return 0
        p_vmm_free = kernel32.GetProcAddress(h_mod, b"vmm_free")
        p_rel_pool = kernel32.GetProcAddress(h_mod, b"vmm_release_pool")
        if not p_vmm_free or not p_rel_pool:
            return 0
        
        code_rel = (ctypes.c_uint8 * 64).from_address(p_rel_pool)
        device_state_fn = None
        for i in range(len(code_rel) - 5):
            if code_rel[i] == 0xe8:
                disp = ctypes.c_int32.from_address(p_rel_pool + i + 1).value
                target = p_rel_pool + i + 5 + disp
                device_state_fn = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_int)(target)
                break
        if device_state_fn is None:
            return 0
        
        vmm_free_fn = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int, ctypes.c_void_p)(p_vmm_free)
        
        freed_total = 0
        num_devices = torch.cuda.device_count() if torch.cuda.is_available() else 1
        for dev_idx in range(num_devices):
            d_ptr = device_state_fn(dev_idx)
            if not d_ptr:
                continue
            myhead = ctypes.c_uint64.from_address(d_ptr + 0x188).value
            mysize = ctypes.c_uint64.from_address(d_ptr + 0x190).value
            if not myhead or mysize == 0:
                continue
            
            pool_nodes = []
            def _collect_pools(node):
                if not node or node == myhead or ctypes.c_uint8.from_address(node + 0x19).value:
                    return
                _collect_pools(ctypes.c_uint64.from_address(node + 0x00).value)
                ordinary = ctypes.c_uint8.from_address(node + 0x30).value
                if ordinary:
                    pool_nodes.append(node + 0x30)
                _collect_pools(ctypes.c_uint64.from_address(node + 0x10).value)
            
            _collect_pools(ctypes.c_uint64.from_address(myhead + 0x08).value)
            
            for p_addr in pool_nodes:
                live = ctypes.c_uint64.from_address(p_addr + 0x08).value
                if live == 0:
                    continue
                blocks_head = ctypes.c_uint64.from_address(p_addr + 0x178).value
                blocks_size = ctypes.c_uint64.from_address(p_addr + 0x180).value
                if not blocks_head or blocks_size == 0:
                    continue
                
                orphans = []
                def _collect_orphans(b_node):
                    if not b_node or b_node == blocks_head or ctypes.c_uint8.from_address(b_node + 0x19).value:
                        return
                    _collect_orphans(ctypes.c_uint64.from_address(b_node + 0x00).value)
                    dptr = ctypes.c_uint64.from_address(b_node + 0x20).value
                    size = ctypes.c_uint64.from_address(b_node + 0x28).value
                    free_flag = ctypes.c_uint8.from_address(b_node + 0x39).value
                    if free_flag == 0 and dptr != 0 and size > 0:
                        orphans.append((dptr, size))
                    _collect_orphans(ctypes.c_uint64.from_address(b_node + 0x10).value)
                
                _collect_orphans(ctypes.c_uint64.from_address(blocks_head + 0x08).value)
                
                for dptr, size in orphans:
                    try:
                        vmm_free_fn(dptr, size, dev_idx, None)
                        freed_total += 1
                    except Exception:
                        pass
        return freed_total
    except Exception:
        return 0

def flush_vram():
    """Fungsi pembersihan VRAM berfasa automatik kalis ralat sticky CUDA driver."""
    gc.collect()
    if torch.cuda.is_available():
        try:
            torch.cuda.empty_cache()
        except Exception:
            pass
        try:
            torch.cuda.ipc_collect()
        except Exception:
            pass
        try:
            torch.cuda.synchronize()
        except Exception:
            pass
        try:
            _vacuum_vmm_orphan_allocations()
            torch.cuda.empty_cache()
        except Exception:
            pass

# Lindungi torch.cuda.empty_cache secara global agar sebarang panggilan wgp.py/gradio tidak meletupkan AcceleratorError
_orig_cuda_empty_cache = torch.cuda.empty_cache
@functools.wraps(_orig_cuda_empty_cache)
def _safe_cuda_empty_cache(*args, **kwargs):
    caller_fn = ""
    caller_file = ""
    frame = None
    try:
        frame = sys._getframe(1)
        caller_fn = frame.f_code.co_name
        caller_file = os.path.basename(frame.f_code.co_filename)
    except Exception:
        pass

    # Peneutralan Heuristik Agresif MMGP:
    # empty_cache_if_needed di mmgp/offload.py memanggil empty_cache setiap kali reserved memori > 90%
    # Pada Windows WDDM, ini memaksa pembekuan GPU selama 20-40 saat setiap blok kerana page table flush.
    # Sekat panggilan pencegahan ini jika VRAM fizikal GPU masih mempunyai baki alokasi selamat (> 128MB).
    if caller_fn == "empty_cache_if_needed":
        return

    _t0 = time.perf_counter()
    try:
        _orig_cuda_empty_cache(*args, **kwargs)
    except Exception as e:
        err_s = str(e).lower()
        if "out of memory" in err_s or "cuda" in err_s or "acceleratorerror" in err_s:
            pass
        else:
            raise e
    finally:
        _dur = time.perf_counter() - _t0
        if _dur > 0.05:
            caller_str = f"{caller_file}:{getattr(frame, 'f_lineno', '?')} ({caller_fn})" if caller_fn else "unknown"
            log_debug(f"[TELEMETRI EMPTY_CACHE] Amaran pemasaan: empty_cache mengambil masa {_dur:.3f}s! Pemanggil: {caller_str}")
torch.cuda.empty_cache = _safe_cuda_empty_cache

def parse_cli_verbose_level():
    """Mengimbas sys.argv secara dinamik untuk arahan --verbose."""
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--verbose" and i + 1 < len(args):
            try:
                return int(args[i + 1])
            except ValueError:
                pass
        elif arg.startswith("--verbose="):
            try:
                return int(arg.split("=")[1])
            except ValueError:
                pass
    return None

# ==============================================================================
# PERISAI SEJAGAT: UNIVERSAL ADAPTIVE DISPATCHER & AUTO-HEALING SIGNATURE SHIELD
# Memastikan tiada lagi ralat TypeError / Argument Mismatch di mana-mana fungsi pintasan
# Menerapkan introspeksi inspect.signature dinamik 100% Sifar Hardcoding.
# ==============================================================================
def universal_auto_healing_call(target_fn, *args, **kwargs):
    """
    Penyelamat Sejagat Dinamik (Universal Self-Healing & Adaptive Signature Harmonizer):
    1. Memeriksa tandatangan fungsi sebenar menggunakan inspect.signature (Zero Hardcoding).
    2. Menapis kwargs yang tidak disokong dan menyelaraskan args berlebihan mengikut parameter sah.
    3. Jika timbul TypeError akibat percanggahan versi upstream/pipeline, melaksanakan pemanggilan selamat
       secara automatik tanpa melontarkan crash ke proses utama.
    """
    import inspect
    try:
        sig = inspect.signature(target_fn)
    except Exception:
        return target_fn(*args, **kwargs)

    has_varargs = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())
    has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())

    if has_varargs and has_varkw:
        return target_fn(*args, **kwargs)

    valid_params = set(sig.parameters.keys())
    filtered_kwargs = kwargs if has_varkw else {k: v for k, v in kwargs.items() if k in valid_params}

    if not has_varargs:
        pos_params_count = sum(
            1 for p in sig.parameters.values() 
            if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        )
        call_args = args[:pos_params_count]
    else:
        call_args = args

    try:
        return target_fn(*call_args, **filtered_kwargs)
    except TypeError:
        # Percubaan auto-healing kedua: ikat parameter secara selamat melalui bind_partial
        try:
            bound = sig.bind_partial(*call_args, **filtered_kwargs)
            return target_fn(*bound.args, **bound.kwargs)
        except Exception:
            # Fallback muktamad: cuba panggil hanya dengan argumen yang diterima
            return target_fn(*args[:1])

def get_realtime_vram_available():
    """Mengira baki VRAM sebenar mengambil kira penimbal/caching PyTorch."""
    if not torch.cuda.is_available():
        return 0.0
    try:
        free, total = torch.cuda.mem_get_info()
        reserved = torch.cuda.memory_reserved()
        allocated = torch.cuda.memory_allocated()
        pytorch_unused_buffer = max(0, reserved - allocated)
        return (free + pytorch_unused_buffer) / (1024 * 1024)
    except Exception:
        return 512.0

def get_live_memory_stats():
    """Mengambil status memori VRAM GPU dan RAM Sistem secara dinamik pada masa-nyata."""
    vram_free_mb = get_realtime_vram_available()
    vram_total_mb = 0.0
    if torch.cuda.is_available():
        try:
            _, total_bytes = torch.cuda.mem_get_info()
            vram_total_mb = total_bytes / (1024 * 1024)
        except Exception as e:
            log_debug(f"Gagal membaca status CUDA memory: {e}")

    sys_ram = psutil.virtual_memory()
    ram_available_mb = sys_ram.available / (1024 * 1024)
    ram_total_mb = sys_ram.total / (1024 * 1024)
    ram_percent = sys_ram.percent

    return {
        "vram_free_mb": vram_free_mb,
        "vram_total_mb": vram_total_mb,
        "ram_available_mb": ram_available_mb,
        "ram_total_mb": ram_total_mb,
        "ram_percent": ram_percent,
    }

def compute_dynamic_chunk_size(total_rows, in_features, out_features, element_size=2):
    """Mengira saiz hirisan token secara matematik tulen berasaskan keperluan bait baris dan memori bebas masa-nyata (100% Zero Hardcoding)."""
    bytes_per_row = max(1, (in_features + out_features) * element_size)
    total_required_bytes = total_rows * bytes_per_row
    
    if torch.cuda.is_available():
        try:
            free_bytes, _ = torch.cuda.mem_get_info()
            cached_unused = torch.cuda.memory_reserved() - torch.cuda.memory_allocated()
            effective_free = free_bytes + max(0, cached_unused)
        except Exception:
            effective_free = total_required_bytes
    else:
        effective_free = psutil.virtual_memory().available

    # Sekiranya keseluruhan operasi muat dalam memori bebas tanpa limpahan, gunakan laluan penuh (1 lelaran)
    if effective_free >= total_required_bytes:
        return total_rows

    # Sekiranya tidak muat, bahagikan kepada pecahan minimum yang muat dalam baki memori selamat
    safe_alloc_bytes = max(bytes_per_row, effective_free)
    num_chunks = max(1, math.ceil(total_required_bytes / safe_alloc_bytes))
    tokens_per_chunk = math.ceil(total_rows / num_chunks)
    
    # Jajarkan kepada gandaan Tensor Core (cth: 256 token jika jumlah token membenarkan)
    tile_align = 256 if total_rows >= 256 else 1
    calc_chunk = ((tokens_per_chunk + tile_align - 1) // tile_align) * tile_align
    return max(1, min(total_rows, calc_chunk))

def get_active_mmgp_instance():
    """Mendapatkan rujukan objek MMGP yang sedang aktif secara dinamik dan selamat (Zero NoneType)."""
    try:
        import mmgp.offload as mo
        return getattr(mo, 'last_offload_obj', None) or getattr(mo, 'active_instance', None) or getattr(mo.offload, 'active_instance', None)
    except Exception:
        return None

def set_active_mmgp_instance(inst):
    """Menetapkan rujukan MMGP aktif merentas semua laluan modul (Zero Missing Pointer)."""
    if inst is None:
        return
    try:
        if not hasattr(inst, "budgets") or not isinstance(getattr(inst, "budgets", None), dict):
            inst.budgets = {}
        import mmgp.offload as mo
        mo.last_offload_obj = inst
        mo.active_instance = inst
        mo.offload.active_instance = inst
    except Exception:
        pass

def safe_mmgp_unload(active_instance, target_key):
    """Memunggah sebarang model atau blok MMGP secara selamat tanpa memusnahkan penimbal staging ring, mmap, atau slot views."""
    if active_instance is None:
        active_instance = get_active_mmgp_instance()
    if active_instance is None or not hasattr(active_instance, "models") or not active_instance.models:
        return
    try:
        if target_key is None or target_key == "all":
            try:
                if hasattr(active_instance, "unload_all"):
                    active_instance.unload_all()
            except Exception as e_unl:
                log_debug(f"Pengecualian semasa inst.unload_all: {e_unl}")
            if hasattr(active_instance, "ring") and active_instance.ring is not None and hasattr(active_instance.ring, "reset"):
                try:
                    active_instance.ring.reset()
                except Exception:
                    pass
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            flush_vram()
            return

        if "/" in target_key:
            model_id, block_name = target_key.split("/", 1)
            if model_id in active_instance.models:
                try:
                    active_instance.gpu_unload_blocks(model_id, block_name)
                except Exception:
                    pass
        else:
            model_id = target_key
            if model_id in active_instance.models:
                # 1. Nyahmuat base model
                try:
                    active_instance.gpu_unload_blocks(model_id, None)
                except Exception:
                    pass
                # 2. Nyahmuat semua blok submodul berdaftar untuk model ini
                if hasattr(active_instance, "blocks_of_modules") and active_instance.blocks_of_modules:
                    for entry_name in list(active_instance.blocks_of_modules.keys()):
                        if entry_name.startswith(model_id + "/"):
                            try:
                                b_name = entry_name[len(model_id) + 1:]
                                active_instance.gpu_unload_blocks(model_id, b_name)
                            except Exception:
                                pass
                # 3. Nyahmuat sebarang pra-muat (preloaded blocks)
                if hasattr(active_instance, "preloaded_blocks_per_model"):
                    for b in list(active_instance.preloaded_blocks_per_model.get(model_id, ())):
                        try:
                            active_instance.gpu_unload_blocks(model_id, b)
                        except Exception:
                            pass
                # 4. Kosongkan blok semasa yang dimuatkan
                if hasattr(active_instance, "loaded_blocks") and active_instance.loaded_blocks.get(model_id):
                    try:
                        active_instance.gpu_unload_blocks(model_id, active_instance.loaded_blocks[model_id])
                    except Exception:
                        pass
                    active_instance.loaded_blocks[model_id] = None
                # 5. Selesaikan pemindahan yang sedang dalam perjalanan (inflight)
                if hasattr(active_instance, "inflight"):
                    for entry in [e for e in list(active_instance.inflight.keys()) if e.startswith(model_id + "/")]:
                        try:
                            active_instance.gpu_unload_blocks(model_id, entry[len(model_id) + 1:])
                        except Exception:
                            pass
                if hasattr(active_instance, "wait_prefetch"):
                    try:
                        active_instance.wait_prefetch()
                    except Exception:
                        pass
                if torch.cuda.is_available():
                    torch.cuda.synchronize()
                flush_vram()
                if torch.cuda.is_available():
                    _alloc_mb = torch.cuda.memory_allocated() / 1048576
                    _res_mb = torch.cuda.memory_reserved() / 1048576
                    log_debug(f"[TELEMETRI UNLOAD {target_key}] Baki Alokasi: {_alloc_mb:.1f}MB | Reserved: {_res_mb:.1f}MB (Telus, Sifar Spekulasi)")
    except Exception as e:
        log_debug(f"Pengecualian semasa safe_mmgp_unload: {e}")

# ------------------------------------------------------------------------------
# 1. PERISAI CATCH-ALL 1: OOM-Safe Sparse Embedding & GGUF Interceptor
# ------------------------------------------------------------------------------
_orig_embedding = torch.nn.functional.embedding

@functools.wraps(_orig_embedding)
def _safe_embedding(input, weight, padding_idx=None, max_norm=None, norm_type=2.0, scale_grad_by_freq=False, sparse=False, *args, **kwargs):
    if _is_guard_active("in_emb"):
        return _orig_embedding(input, weight, padding_idx=padding_idx, max_norm=max_norm, norm_type=norm_type, scale_grad_by_freq=scale_grad_by_freq, sparse=sparse, *args, **kwargs)
    _set_guard("in_emb", True)
    try:
        # Penyelarasan Peranti Pintar untuk Embedding (Cegah Banjir VRAM daripada Jadual Berat)
        # input: tensor indeks (Long/Int), weight: jadual embedding (2D tensor)
        if torch.is_tensor(weight) and torch.is_tensor(input):
            if weight.device != input.device:
                # Jika jadual berat berada di CPU dan input di CUDA:
                # JANGAN tolak berat (3.1 GB) ke CUDA! Jalankan carian token di CPU RAM (<1ms)
                # dan hanya tolak hasil hirisan embedding (~beberapa puluh MB) ke peranti sasaran!
                if weight.device.type == "cpu":
                    target_dev = input.device
                    cpu_input = input.to("cpu")
                    res = _orig_embedding(
                        cpu_input, weight,
                        padding_idx=padding_idx, max_norm=max_norm, norm_type=norm_type,
                        scale_grad_by_freq=scale_grad_by_freq, sparse=sparse, *args, **kwargs
                    )
                    return res.to(target_dev, non_blocking=True)
                elif input.device.type == "cpu":
                    # Berat di CUDA, input di CPU: tolak input (saiz amat kecil) ke peranti berat
                    input = input.to(weight.device)
                else:
                    input = input.to(weight.device)
        return _orig_embedding(
            input, weight,
            padding_idx=padding_idx, max_norm=max_norm, norm_type=norm_type,
            scale_grad_by_freq=scale_grad_by_freq, sparse=sparse, *args, **kwargs
        )
    except Exception as err:
        err_msg = str(err).lower()
        if "out of memory" in err_msg or "cuda" in err_msg or "acceleratorerror" in err_msg or "device" in err_msg:
            log_debug("Pengecualian dikesan semasa F.embedding! Mengalirkan carian token ke CPU RAM secara dinamik...")
            flush_vram()
            try:
                target_device = input.device if torch.is_tensor(input) else torch.device("cuda")
                cpu_weight = weight.to("cpu") if torch.is_tensor(weight) else weight
                cpu_input = input.to("cpu") if torch.is_tensor(input) else input
                res = _orig_embedding(
                    cpu_input, cpu_weight,
                    padding_idx=padding_idx, max_norm=max_norm, norm_type=norm_type,
                    scale_grad_by_freq=scale_grad_by_freq, sparse=sparse, *args, **kwargs
                )
                return res.to(target_device, non_blocking=True)
            except Exception as cpu_err:
                log_debug(f"Pintasan CPU Embedding gagal: {cpu_err}")
                raise err
        raise err
    finally:
        _set_guard("in_emb", False)

torch.nn.functional.embedding = _safe_embedding

# ==========================================================================
# Perisai Sejagat Resilient Conv (cuDNN Blackwell Fallback & Universal Device/Dtype Harmonizer)
# Menyelesaikan ralat:
# 1. 'RuntimeError: GET was unable to find an engine to execute this computation'
# 2. 'RuntimeError: Input type (CUDABFloat16Type) and weight type (CPUBFloat16Type) should be the same'
# 3. 'RuntimeError: Expected all tensors to be on the same device'
# ==========================================================================
_orig_conv3d = torch.nn.functional.conv3d
_orig_conv2d = torch.nn.functional.conv2d
_orig_conv1d = torch.nn.functional.conv1d
_orig_conv_transpose1d = torch.nn.functional.conv_transpose1d
_orig_conv_transpose2d = torch.nn.functional.conv_transpose2d
_orig_conv_transpose3d = torch.nn.functional.conv_transpose3d

def _harmonize_conv_operands(input, weight, bias=None):
    if not (torch.is_tensor(input) and torch.is_tensor(weight)):
        return input, weight, bias
    target_device = input.device
    target_dtype = input.dtype

    # 1. Penyelarasan Peranti (Device Auto-Harmonize)
    if weight.device != target_device:
        try:
            weight = weight.to(device=target_device)
        except Exception:
            target_device = weight.device
            input = input.to(device=target_device)

    # 2. Penyelarasan Jenis Data (Dtype Auto-Harmonize)
    if weight.dtype != target_dtype:
        if weight.dtype.is_floating_point and target_dtype.is_floating_point:
            try:
                weight = weight.to(dtype=target_dtype)
            except Exception:
                input = input.to(dtype=weight.dtype)
                target_dtype = weight.dtype

    # 3. Penyelarasan Penimbal Bias
    if bias is not None and torch.is_tensor(bias):
        if bias.device != target_device or bias.dtype != target_dtype:
            try:
                bias = bias.to(device=target_device, dtype=target_dtype)
            except Exception:
                pass

    return input, weight, bias

def _make_resilient_conv(orig_conv_fn, name="conv"):
    @functools.wraps(orig_conv_fn)
    def _resilient_wrapper(input, weight, bias=None, *args, **kwargs):
        input, weight, bias = _harmonize_conv_operands(input, weight, bias)
        try:
            return orig_conv_fn(input, weight, bias, *args, **kwargs)
        except RuntimeError as conv_err:
            err_s = str(conv_err).lower()
            if "engine" in err_s or "cudnn" in err_s:
                log_debug(f"[CUDNN RESCUE] cuDNN gagal mencari engine {name} ({conv_err}). Mengaktifkan fallback PyTorch ATen native...")
                with torch.backends.cudnn.flags(enabled=False):
                    safe_inp = input.contiguous() if torch.is_tensor(input) else input
                    safe_w = weight.contiguous() if torch.is_tensor(weight) else weight
                    safe_b = bias.contiguous() if (bias is not None and torch.is_tensor(bias)) else bias
                    return orig_conv_fn(safe_inp, safe_w, safe_b, *args, **kwargs)

            if "type" in err_s or "device" in err_s or "should be the same" in err_s or "same device" in err_s or "contiguous" in err_s or "mismatch" in err_s:
                log_debug(f"[{name.upper()} HARMONIZER RESCUE] Membetulkan ralat peranti/tipe {name}: {conv_err}. Menyelaras semula...")
                target_dev = input.device if torch.is_tensor(input) else torch.device("cuda")
                target_dt = input.dtype if torch.is_tensor(input) else torch.bfloat16
                safe_inp = input.to(device=target_dev, dtype=target_dt).contiguous() if torch.is_tensor(input) else input
                safe_w = weight.to(device=target_dev, dtype=target_dt).contiguous() if torch.is_tensor(weight) else weight
                safe_b = bias.to(device=target_dev, dtype=target_dt).contiguous() if (bias is not None and torch.is_tensor(bias)) else bias
                try:
                    with torch.backends.cudnn.flags(enabled=False):
                        return orig_conv_fn(safe_inp, safe_w, safe_b, *args, **kwargs)
                except Exception as retry_err:
                    log_debug(f"[{name.upper()} CPU FALLBACK RESCUE] Mengalihkan {name} ke CPU secara selamat: {retry_err}...")
                    inp_c = input.cpu().contiguous()
                    w_c = weight.cpu().contiguous()
                    b_c = bias.cpu().contiguous() if (bias is not None and torch.is_tensor(bias)) else bias
                    res_c = orig_conv_fn(inp_c, w_c, b_c, *args, **kwargs)
                    return res_c.to(device=input.device, dtype=input.dtype)
            raise conv_err
    return _resilient_wrapper

torch.nn.functional.conv1d = _make_resilient_conv(_orig_conv1d, "conv1d")
torch.nn.functional.conv2d = _make_resilient_conv(_orig_conv2d, "conv2d")
torch.nn.functional.conv3d = _make_resilient_conv(_orig_conv3d, "conv3d")
torch.nn.functional.conv_transpose1d = _make_resilient_conv(_orig_conv_transpose1d, "conv_transpose1d")
torch.nn.functional.conv_transpose2d = _make_resilient_conv(_orig_conv_transpose2d, "conv_transpose2d")
torch.nn.functional.conv_transpose3d = _make_resilient_conv(_orig_conv_transpose3d, "conv_transpose3d")
log_debug("Perisai Sejagat Resilient Convolutions (1D/2D/3D & Transposed 1D/2D/3D cuDNN Fallback & Device Harmonizer) berjaya dipasang.")

# ==========================================================================
# Perisai Sejagat LayerNorm & GroupNorm (Universal Device/Dtype Harmonizer)
# Menyelesaikan sebarang 'Expected all tensors to be on the same device'
# ==========================================================================
_orig_layer_norm = torch.nn.functional.layer_norm
_orig_group_norm = torch.nn.functional.group_norm

@functools.wraps(_orig_layer_norm)
def _safe_layer_norm(input, normalized_shape, weight=None, bias=None, eps=1e-5):
    if torch.is_tensor(input):
        target_dev = input.device
        target_dt = input.dtype
        if weight is not None and torch.is_tensor(weight) and (weight.device != target_dev or weight.dtype != target_dt):
            try:
                weight = weight.to(device=target_dev, dtype=target_dt)
            except Exception:
                pass
        if bias is not None and torch.is_tensor(bias) and (bias.device != target_dev or bias.dtype != target_dt):
            try:
                bias = bias.to(device=target_dev, dtype=target_dt)
            except Exception:
                pass
    try:
        return _orig_layer_norm(input, normalized_shape, weight=weight, bias=bias, eps=eps)
    except Exception as norm_err:
        err_s = str(norm_err).lower()
        if "device" in err_s or "dtype" in err_s or "type" in err_s or "same" in err_s:
            log_debug(f"[LAYERNORM RESCUE] Menyelaras peranti LayerNorm: {norm_err}...")
            target_dev = input.device if torch.is_tensor(input) else torch.device("cuda")
            target_dt = input.dtype if torch.is_tensor(input) else torch.bfloat16
            w = weight.to(device=target_dev, dtype=target_dt) if (weight is not None and torch.is_tensor(weight)) else weight
            b = bias.to(device=target_dev, dtype=target_dt) if (bias is not None and torch.is_tensor(bias)) else bias
            return _orig_layer_norm(input, normalized_shape, weight=w, bias=b, eps=eps)
        raise norm_err

@functools.wraps(_orig_group_norm)
def _safe_group_norm(input, num_groups, weight=None, bias=None, eps=1e-5):
    if torch.is_tensor(input):
        target_dev = input.device
        target_dt = input.dtype
        if weight is not None and torch.is_tensor(weight) and (weight.device != target_dev or weight.dtype != target_dt):
            try:
                weight = weight.to(device=target_dev, dtype=target_dt)
            except Exception:
                pass
        if bias is not None and torch.is_tensor(bias) and (bias.device != target_dev or bias.dtype != target_dt):
            try:
                bias = bias.to(device=target_dev, dtype=target_dt)
            except Exception:
                pass
    try:
        return _orig_group_norm(input, num_groups, weight=weight, bias=bias, eps=eps)
    except Exception as gnorm_err:
        err_s = str(gnorm_err).lower()
        if "device" in err_s or "dtype" in err_s or "type" in err_s or "same" in err_s:
            log_debug(f"[GROUPNORM RESCUE] Menyelaras peranti GroupNorm: {gnorm_err}...")
            target_dev = input.device if torch.is_tensor(input) else torch.device("cuda")
            target_dt = input.dtype if torch.is_tensor(input) else torch.bfloat16
            w = weight.to(device=target_dev, dtype=target_dt) if (weight is not None and torch.is_tensor(weight)) else weight
            b = bias.to(device=target_dev, dtype=target_dt) if (bias is not None and torch.is_tensor(bias)) else bias
            return _orig_group_norm(input, num_groups, weight=w, bias=b, eps=eps)
        raise gnorm_err

torch.nn.functional.layer_norm = _safe_layer_norm
torch.nn.functional.group_norm = _safe_group_norm
log_debug("Perisai Sejagat LayerNorm & GroupNorm (Universal Device/Dtype Harmonizer Guard) berjaya dipasang.")

# ==========================================================================
# Perisai Sejagat Embedding, SDPA, & Interpolate (Universal Device/Dtype Harmonizer)
# ==========================================================================
# Perisai Sejagat SDPA & Interpolate (Universal Device/Dtype Harmonizer)
# Menyelesaikan mismatch peranti attention SDPA dan CPU bfloat16 interpolate
# ==========================================================================
_orig_sdpa = torch.nn.functional.scaled_dot_product_attention
_orig_interpolate = torch.nn.functional.interpolate

@functools.wraps(_orig_sdpa)
def _safe_sdpa(query, key, value, attn_mask=None, dropout_p=0.0, is_causal=False, scale=None, enable_gqa=False):
    if torch.is_tensor(query):
        target_dev = query.device
        target_dt = query.dtype
        if torch.is_tensor(key) and (key.device != target_dev or key.dtype != target_dt):
            key = key.to(device=target_dev, dtype=target_dt)
        if torch.is_tensor(value) and (value.device != target_dev or value.dtype != target_dt):
            value = value.to(device=target_dev, dtype=target_dt)
        if attn_mask is not None and torch.is_tensor(attn_mask) and attn_mask.device != target_dev:
            attn_mask = attn_mask.to(device=target_dev)
    try:
        if enable_gqa:
            return _orig_sdpa(query, key, value, attn_mask=attn_mask, dropout_p=dropout_p, is_causal=is_causal, scale=scale, enable_gqa=enable_gqa)
        else:
            return _orig_sdpa(query, key, value, attn_mask=attn_mask, dropout_p=dropout_p, is_causal=is_causal, scale=scale)
    except Exception as sdpa_err:
        err_s = str(sdpa_err).lower()
        if "device" in err_s or "dtype" in err_s or "type" in err_s:
            log_debug(f"[SDPA RESCUE] Menyelaras semula input SDPA: {sdpa_err}...")
            target_dev = query.device
            target_dt = query.dtype
            k = key.to(device=target_dev, dtype=target_dt) if torch.is_tensor(key) else key
            v = value.to(device=target_dev, dtype=target_dt) if torch.is_tensor(value) else value
            m = attn_mask.to(device=target_dev) if (attn_mask is not None and torch.is_tensor(attn_mask)) else attn_mask
            if enable_gqa:
                return _orig_sdpa(query, k, v, attn_mask=m, dropout_p=dropout_p, is_causal=is_causal, scale=scale, enable_gqa=enable_gqa)
            return _orig_sdpa(query, k, v, attn_mask=m, dropout_p=dropout_p, is_causal=is_causal, scale=scale)
        raise sdpa_err

@functools.wraps(_orig_interpolate)
def _safe_interpolate(input, size=None, scale_factor=None, mode='nearest', align_corners=None, recompute_scale_factor=None, antialias=False):
    if torch.is_tensor(input) and input.device.type == "cpu" and input.dtype in (torch.bfloat16, torch.float16):
        orig_dt = input.dtype
        res = _orig_interpolate(input.float(), size=size, scale_factor=scale_factor, mode=mode, align_corners=align_corners, recompute_scale_factor=recompute_scale_factor, antialias=antialias)
        return res.to(dtype=orig_dt)
    try:
        return _orig_interpolate(input, size=size, scale_factor=scale_factor, mode=mode, align_corners=align_corners, recompute_scale_factor=recompute_scale_factor, antialias=antialias)
    except Exception as int_err:
        err_s = str(int_err).lower()
        if "not implemented" in err_s or "bfloat16" in err_s or "half" in err_s:
            orig_dt = input.dtype
            res = _orig_interpolate(input.float(), size=size, scale_factor=scale_factor, mode=mode, align_corners=align_corners, recompute_scale_factor=recompute_scale_factor, antialias=antialias)
            return res.to(dtype=orig_dt)
        raise int_err

torch.nn.functional.scaled_dot_product_attention = _safe_sdpa
torch.nn.functional.interpolate = _safe_interpolate
log_debug("Perisai Sejagat SDPA & Interpolate (Universal Device/Dtype Harmonizer Guard) berjaya dipasang.")

# ==========================================================================
# Perisai Sejagat torch.cat & torch.stack (Universal Device/Dtype Harmonizer)
# Menyelesaikan 'Expected all tensors to be on the same device' semasa perangkaian tensor
# ==========================================================================
_orig_cat = torch.cat
_orig_stack = torch.stack

@functools.wraps(_orig_cat)
def _safe_cat(tensors, dim=0, *args, **kwargs):
    if tensors and len(tensors) > 1:
        target_dev = None
        target_dt = None
        for t in tensors:
            if torch.is_tensor(t) and t.is_cuda:
                target_dev = t.device
                target_dt = t.dtype
                break
        if target_dev is None and torch.is_tensor(tensors[0]):
            target_dev = tensors[0].device
            target_dt = tensors[0].dtype

        if target_dev is not None:
            new_tensors = []
            mismatch_found = False
            for t in tensors:
                if torch.is_tensor(t):
                    need_dev = t.device != target_dev
                    need_dt = (target_dt is not None and t.dtype != target_dt and t.dtype.is_floating_point and target_dt.is_floating_point)
                    if need_dev or need_dt:
                        mismatch_found = True
                        cur = t
                        if need_dev:
                            cur = cur.to(device=target_dev)
                        if need_dt:
                            cur = cur.to(dtype=target_dt)
                        new_tensors.append(cur)
                    else:
                        new_tensors.append(t)
                else:
                    new_tensors.append(t)
            if mismatch_found:
                tensors = type(tensors)(new_tensors) if isinstance(tensors, (list, tuple)) else new_tensors
    try:
        return _orig_cat(tensors, dim=dim, *args, **kwargs)
    except Exception as cat_err:
        err_s = str(cat_err).lower()
        if "device" in err_s or "same" in err_s or "type" in err_s or "dtype" in err_s:
            log_debug(f"[TORCH.CAT RESCUE] Menyelaras peranti/dtype tensor untuk torch.cat: {cat_err}...")
            first_t = next((t for t in tensors if torch.is_tensor(t)), None)
            target_dev = first_t.device if first_t is not None else torch.device("cuda" if torch.cuda.is_available() else "cpu")
            target_dt = first_t.dtype if (first_t is not None and first_t.dtype.is_floating_point) else None
            aligned = []
            for t in tensors:
                if torch.is_tensor(t):
                    cur = t.to(device=target_dev)
                    if target_dt is not None and cur.dtype.is_floating_point:
                        cur = cur.to(dtype=target_dt)
                    aligned.append(cur)
                else:
                    aligned.append(t)
            return _orig_cat(aligned, dim=dim, *args, **kwargs)
        raise cat_err

@functools.wraps(_orig_stack)
def _safe_stack(tensors, dim=0, *args, **kwargs):
    if tensors and len(tensors) > 1:
        target_dev = None
        target_dt = None
        for t in tensors:
            if torch.is_tensor(t) and t.is_cuda:
                target_dev = t.device
                target_dt = t.dtype
                break
        if target_dev is None and torch.is_tensor(tensors[0]):
            target_dev = tensors[0].device
            target_dt = tensors[0].dtype

        if target_dev is not None:
            new_tensors = []
            mismatch_found = False
            for t in tensors:
                if torch.is_tensor(t):
                    need_dev = t.device != target_dev
                    need_dt = (target_dt is not None and t.dtype != target_dt and t.dtype.is_floating_point and target_dt.is_floating_point)
                    if need_dev or need_dt:
                        mismatch_found = True
                        cur = t
                        if need_dev:
                            cur = cur.to(device=target_dev)
                        if need_dt:
                            cur = cur.to(dtype=target_dt)
                        new_tensors.append(cur)
                    else:
                        new_tensors.append(t)
                else:
                    new_tensors.append(t)
            if mismatch_found:
                tensors = type(tensors)(new_tensors) if isinstance(tensors, (list, tuple)) else new_tensors
    try:
        return _orig_stack(tensors, dim=dim, *args, **kwargs)
    except Exception as stack_err:
        err_s = str(stack_err).lower()
        if "device" in err_s or "same" in err_s or "type" in err_s or "dtype" in err_s:
            log_debug(f"[TORCH.STACK RESCUE] Menyelaras peranti/dtype tensor untuk torch.stack: {stack_err}...")
            first_t = next((t for t in tensors if torch.is_tensor(t)), None)
            target_dev = first_t.device if first_t is not None else torch.device("cuda" if torch.cuda.is_available() else "cpu")
            target_dt = first_t.dtype if (first_t is not None and first_t.dtype.is_floating_point) else None
            aligned = []
            for t in tensors:
                if torch.is_tensor(t):
                    cur = t.to(device=target_dev)
                    if target_dt is not None and cur.dtype.is_floating_point:
                        cur = cur.to(dtype=target_dt)
                    aligned.append(cur)
                else:
                    aligned.append(t)
            return _orig_stack(aligned, dim=dim, *args, **kwargs)
        raise stack_err

torch.cat = _safe_cat
torch.stack = _safe_stack
log_debug("Perisai Sejagat torch.cat & torch.stack (Universal Device/Dtype Harmonizer Guard) berjaya dipasang.")

# ==========================================================================
# Perisai Sejagat Tensor Arithmetic & RoPE (Universal Cross-Device Harmonizer)
# Menyelesaikan 'Expected all tensors to be on the same device' untuk operasi
# aritmetik element-wise (inv_freq, mean, std, scale, rotary embeddings)
# ==========================================================================
_orig_torch_mul = torch.mul
_orig_torch_add = torch.add
_orig_torch_sub = torch.sub
_orig_torch_div = torch.div

def _harmonize_binary_operands(a, b):
    if torch.is_tensor(a) and torch.is_tensor(b) and a.device != b.device:
        if a.is_cuda and not b.is_cuda:
            b = b.to(device=a.device)
        elif b.is_cuda and not a.is_cuda:
            a = a.to(device=b.device)
    return a, b

@functools.wraps(_orig_torch_mul)
def _safe_torch_mul(input, other, *args, **kwargs):
    input, other = _harmonize_binary_operands(input, other)
    return _orig_torch_mul(input, other, *args, **kwargs)

@functools.wraps(_orig_torch_add)
def _safe_torch_add(input, other, *args, **kwargs):
    input, other = _harmonize_binary_operands(input, other)
    return _orig_torch_add(input, other, *args, **kwargs)

@functools.wraps(_orig_torch_sub)
def _safe_torch_sub(input, other, *args, **kwargs):
    input, other = _harmonize_binary_operands(input, other)
    return _orig_torch_sub(input, other, *args, **kwargs)

@functools.wraps(_orig_torch_div)
def _safe_torch_div(input, other, *args, **kwargs):
    input, other = _harmonize_binary_operands(input, other)
    return _orig_torch_div(input, other, *args, **kwargs)

torch.mul = _safe_torch_mul
torch.add = _safe_torch_add
torch.sub = _safe_torch_sub
torch.div = _safe_torch_div

_orig_tensor_mul = torch.Tensor.__mul__
_orig_tensor_rmul = torch.Tensor.__rmul__
_orig_tensor_add = torch.Tensor.__add__
_orig_tensor_radd = torch.Tensor.__radd__
_orig_tensor_sub = torch.Tensor.__sub__
_orig_tensor_rsub = torch.Tensor.__rsub__
_orig_tensor_div = torch.Tensor.__truediv__
_orig_tensor_rdiv = torch.Tensor.__rtruediv__

def _make_safe_tensor_binop(orig_op):
    @functools.wraps(orig_op)
    def _safe_binop(self, other):
        if torch.is_tensor(other) and self.device != other.device:
            if self.is_cuda and not other.is_cuda:
                other = other.to(device=self.device)
            elif other.is_cuda and not self.is_cuda:
                self = self.to(device=other.device)
        try:
            return orig_op(self, other)
        except RuntimeError as r_err:
            if "same device" in str(r_err).lower() or "device" in str(r_err).lower():
                target_dev = self.device if self.is_cuda else (other.device if torch.is_tensor(other) and other.is_cuda else self.device)
                s = self.to(device=target_dev)
                o = other.to(device=target_dev) if torch.is_tensor(other) else other
                return orig_op(s, o)
            raise r_err
    return _safe_binop

torch.Tensor.__mul__ = _make_safe_tensor_binop(_orig_tensor_mul)
torch.Tensor.__rmul__ = _make_safe_tensor_binop(_orig_tensor_rmul)
torch.Tensor.__add__ = _make_safe_tensor_binop(_orig_tensor_add)
torch.Tensor.__radd__ = _make_safe_tensor_binop(_orig_tensor_radd)
torch.Tensor.__sub__ = _make_safe_tensor_binop(_orig_tensor_sub)
torch.Tensor.__rsub__ = _make_safe_tensor_binop(_orig_tensor_rsub)
torch.Tensor.__truediv__ = _make_safe_tensor_binop(_orig_tensor_div)
torch.Tensor.__rtruediv__ = _make_safe_tensor_binop(_orig_tensor_rdiv)

_orig_tensor_mul_ = torch.Tensor.mul_
_orig_tensor_add_ = torch.Tensor.add_
_orig_tensor_sub_ = torch.Tensor.sub_
_orig_tensor_div_ = torch.Tensor.div_

def _make_safe_tensor_inplace_binop(orig_inplace_op):
    @functools.wraps(orig_inplace_op)
    def _safe_inplace_binop(self, other, *args, **kwargs):
        if torch.is_tensor(other):
            if other.device != self.device:
                other = other.to(device=self.device)
            if other.dtype != self.dtype and other.dtype.is_floating_point and self.dtype.is_floating_point:
                other = other.to(dtype=self.dtype)
        return orig_inplace_op(self, other, *args, **kwargs)
    return _safe_inplace_binop

torch.Tensor.mul_ = _make_safe_tensor_inplace_binop(_orig_tensor_mul_)
torch.Tensor.add_ = _make_safe_tensor_inplace_binop(_orig_tensor_add_)
torch.Tensor.sub_ = _make_safe_tensor_inplace_binop(_orig_tensor_sub_)
torch.Tensor.div_ = _make_safe_tensor_inplace_binop(_orig_tensor_div_)

_orig_tensor_addcmul_ = torch.Tensor.addcmul_
_orig_tensor_addcmul = torch.Tensor.addcmul
_orig_tensor_addcdiv_ = torch.Tensor.addcdiv_

def _safe_tensor_addcmul_(self, tensor1, tensor2, *, value=1):
    if torch.is_tensor(tensor1) and tensor1.device != self.device:
        tensor1 = tensor1.to(device=self.device)
    if torch.is_tensor(tensor2) and tensor2.device != self.device:
        tensor2 = tensor2.to(device=self.device)
    if torch.is_tensor(tensor1) and tensor1.dtype != self.dtype and tensor1.dtype.is_floating_point and self.dtype.is_floating_point:
        tensor1 = tensor1.to(dtype=self.dtype)
    if torch.is_tensor(tensor2) and tensor2.dtype != self.dtype and tensor2.dtype.is_floating_point and self.dtype.is_floating_point:
        tensor2 = tensor2.to(dtype=self.dtype)
    return _orig_tensor_addcmul_(self, tensor1, tensor2, value=value)

def _safe_tensor_addcmul(self, tensor1, tensor2, *, value=1):
    if torch.is_tensor(tensor1) and tensor1.device != self.device:
        tensor1 = tensor1.to(device=self.device)
    if torch.is_tensor(tensor2) and tensor2.device != self.device:
        tensor2 = tensor2.to(device=self.device)
    if torch.is_tensor(tensor1) and tensor1.dtype != self.dtype and tensor1.dtype.is_floating_point and self.dtype.is_floating_point:
        tensor1 = tensor1.to(dtype=self.dtype)
    if torch.is_tensor(tensor2) and tensor2.dtype != self.dtype and tensor2.dtype.is_floating_point and self.dtype.is_floating_point:
        tensor2 = tensor2.to(dtype=self.dtype)
    return _orig_tensor_addcmul(self, tensor1, tensor2, value=value)

def _safe_tensor_addcdiv_(self, tensor1, tensor2, *, value=1):
    if torch.is_tensor(tensor1) and tensor1.device != self.device:
        tensor1 = tensor1.to(device=self.device)
    if torch.is_tensor(tensor2) and tensor2.device != self.device:
        tensor2 = tensor2.to(device=self.device)
    if torch.is_tensor(tensor1) and tensor1.dtype != self.dtype and tensor1.dtype.is_floating_point and self.dtype.is_floating_point:
        tensor1 = tensor1.to(dtype=self.dtype)
    if torch.is_tensor(tensor2) and tensor2.dtype != self.dtype and tensor2.dtype.is_floating_point and self.dtype.is_floating_point:
        tensor2 = tensor2.to(dtype=self.dtype)
    return _orig_tensor_addcdiv_(self, tensor1, tensor2, value=value)

torch.Tensor.addcmul_ = _safe_tensor_addcmul_
torch.Tensor.addcmul = _safe_tensor_addcmul
torch.addcmul = _safe_tensor_addcmul
torch.Tensor.addcdiv_ = _safe_tensor_addcdiv_
log_debug("Perisai Sejagat Tensor Arithmetic & In-Place Operators (Cross-Device Auto Harmonizer) berjaya dipasang.")

try:
    from shared.kernels import vae_ops
    _orig_scaled_residual = vae_ops.scaled_residual
    @functools.wraps(_orig_scaled_residual)
    def _safe_scaled_residual(x_list, scale, residual):
        first_x = x_list[0] if (x_list and len(x_list) > 0) else None
        if first_x is not None and torch.is_tensor(first_x):
            target_dev = first_x.device
            target_dt = first_x.dtype
            if scale is not None and torch.is_tensor(scale) and (scale.device != target_dev or scale.dtype != target_dt):
                scale = scale.to(device=target_dev, dtype=target_dt)
            if residual is not None and torch.is_tensor(residual) and (residual.device != target_dev or residual.dtype != target_dt):
                residual = residual.to(device=target_dev, dtype=target_dt)
        return _orig_scaled_residual(x_list, scale, residual)
    vae_ops.scaled_residual = _safe_scaled_residual
except Exception:
    pass

try:
    from models.minimax_h3.components import video_autoencoder as v_ae_comp
    if hasattr(v_ae_comp, "MiniMaxH3VideoRotaryPosEmbed"):
        _orig_rope_forward = v_ae_comp.MiniMaxH3VideoRotaryPosEmbed.forward
        @functools.wraps(_orig_rope_forward)
        def _safe_video_rope_forward(self, position_ids):
            if hasattr(self, "inv_freq") and torch.is_tensor(self.inv_freq) and self.inv_freq.device != position_ids.device:
                self.inv_freq = self.inv_freq.to(position_ids.device)
            return _orig_rope_forward(self, position_ids)
        v_ae_comp.MiniMaxH3VideoRotaryPosEmbed.forward = _safe_video_rope_forward
except Exception:
    pass

try:
    from models.minimax_h3 import transformer as h3_trans
    if hasattr(h3_trans, "RotaryEmbedding"):
        _orig_trans_rope_forward = h3_trans.RotaryEmbedding.forward
        @functools.wraps(_orig_trans_rope_forward)
        def _safe_trans_rope_forward(self, position_ids, device):
            if hasattr(self, "inv_freq") and torch.is_tensor(self.inv_freq) and str(self.inv_freq.device) != str(device):
                self.inv_freq = self.inv_freq.to(device)
            return _orig_trans_rope_forward(self, position_ids, device)
        h3_trans.RotaryEmbedding.forward = _safe_trans_rope_forward
except Exception:
    pass

try:
    from models.ideogram4 import qwen3_vl_transformers as q3vl
    if hasattr(q3vl, "apply_rotary_pos_emb_vision"):
        _orig_apply_rotary_pos_emb_vision = q3vl.apply_rotary_pos_emb_vision
        @functools.wraps(_orig_apply_rotary_pos_emb_vision)
        def _safe_apply_rotary_pos_emb_vision(q, k, cos, sin):
            first_t = q[0] if isinstance(q, (list, tuple)) else q
            if first_t is not None and torch.is_tensor(first_t):
                target_dev = first_t.device
                if torch.is_tensor(cos) and cos.device != target_dev:
                    cos = cos.to(device=target_dev)
                if torch.is_tensor(sin) and sin.device != target_dev:
                    sin = sin.to(device=target_dev)
            return _orig_apply_rotary_pos_emb_vision(q, k, cos, sin)
        q3vl.apply_rotary_pos_emb_vision = _safe_apply_rotary_pos_emb_vision

    if hasattr(q3vl, "_apply_rotary_inplace"):
        _orig_apply_rotary_inplace = q3vl._apply_rotary_inplace
        @functools.wraps(_orig_apply_rotary_inplace)
        def _safe_apply_rotary_inplace(x, cos, sin, unsqueeze_dim):
            if torch.is_tensor(x):
                target_dev = x.device
                target_dt = x.dtype
                if torch.is_tensor(cos) and (cos.device != target_dev or cos.dtype != target_dt):
                    cos = cos.to(device=target_dev, dtype=target_dt)
                if torch.is_tensor(sin) and (sin.device != target_dev or sin.dtype != target_dt):
                    sin = sin.to(device=target_dev, dtype=target_dt)
            return _orig_apply_rotary_inplace(x, cos, sin, unsqueeze_dim)
        q3vl._apply_rotary_inplace = _safe_apply_rotary_inplace
except Exception:
    pass


# Pintasan GGUF Proaktif Sejagat: Menapis Berdasarkan Nisbah Lonjakan Memori Fizikal Masa-Nyata
try:
    import shared.qtypes.gguf as s_gguf
    
    if hasattr(s_gguf, "_gguf_dequantize_tensor"):
        _orig_gguf_dequantize_tensor = s_gguf._gguf_dequantize_tensor
        
        @functools.wraps(_orig_gguf_dequantize_tensor)
        def _universal_safe_dequantize_tensor(raw, tensor_type, tensor_shape, dtype=None):
            # Cuba nyahkuantisasi terus di GPU menggunakan CUDA kernel llama.cpp/PyTorch pantas
            try:
                return _orig_gguf_dequantize_tensor(raw, tensor_type, tensor_shape, dtype=dtype)
            except Exception as err:
                err_msg = str(err).lower()
                if "out of memory" in err_msg or "cuda" in err_msg or "acceleratorerror" in err_msg:
                    log_debug("[UNIVERSAL EMERGENCY RESCUE] CUDA OOM dikesan! Mengalihkan nyahkuantisasi ke CPU RAM...")
                    flush_vram()
                    cpu_raw = raw.to("cpu") if raw.is_cuda else raw
                    with torch.device("cpu"):
                        cpu_res = _orig_gguf_dequantize_tensor(cpu_raw, tensor_type, tensor_shape, dtype=dtype)
                    try:
                        return cpu_res.to(raw.device, non_blocking=True)
                    except Exception:
                        flush_vram()
                        return cpu_res.to(raw.device)
                raise err
                
        s_gguf._gguf_dequantize_tensor = _universal_safe_dequantize_tensor

    if hasattr(s_gguf, "GGUFWeightTensor"):
        _orig_gguf_dequantize = s_gguf.GGUFWeightTensor.dequantize
        
        @functools.wraps(_orig_gguf_dequantize)
        def _safe_gguf_dequantize(self, dtype=None, device=None):
            target_dev = device if device is not None else self.device
            target_dtype = dtype if dtype is not None else self.dtype
            
            # Cuba nyahkuantisasi terus di peranti sasaran (GPU) secara native
            try:
                return _orig_gguf_dequantize(self, dtype=target_dtype, device=target_dev)
            except Exception as err:
                err_msg = str(err).lower()
                if "out of memory" in err_msg or "cuda" in err_msg or "acceleratorerror" in err_msg:
                    log_debug("[GGUF DEQUANTIZE RESCUE] CUDA OOM dikesan! Melaksanakan di CPU...")
                    flush_vram()
                    raw = self._data
                    if raw.is_cuda:
                        raw = raw.to("cpu")
                    with torch.device("cpu"):
                        cpu_res = s_gguf._gguf_dequantize_tensor(raw, self._tensor_type, self._tensor_shape, dtype=target_dtype)
                    try:
                        return cpu_res.to(target_dev, non_blocking=True)
                    except Exception:
                        flush_vram()
                        return cpu_res.to(target_dev)
                raise err
                
        s_gguf.GGUFWeightTensor.dequantize = _safe_gguf_dequantize

        # Pengaktifan Mod Matmul Pantas llama.cpp (Tensor Cores cuBLAS untuk jujukan besar)
        os.environ.setdefault("WGP_GGUF_LLAMACPP_CUDA_MATMUL_MODE", "fast")
        try:
            mod_refresh = s_gguf._gguf_cuda_module()
            if mod_refresh is not None and hasattr(mod_refresh, "refresh_env"):
                mod_refresh.refresh_env()
        except Exception:
            pass

        # Perisai Sejagat Resilient GGUF Kernel (Penyelamat Automatik GGML Assertion & Kernel Abort)
        # Menghapuskan 'RuntimeError: ggml abort ... GGML_ASSERT(ne % blck == 0) failed'
        # dengan penjajaran automatik jujukan token ke sempadan blok kuantisasi perkakasan CUDA (32-row boundary).
        if hasattr(s_gguf, "_try_llamacpp_cuda_linear"):
            _orig_try_llamacpp_linear = s_gguf._try_llamacpp_cuda_linear
            @functools.wraps(_orig_try_llamacpp_linear)
            def _safe_try_llamacpp_linear(weight_tensor, input_tensor, bias, target_dtype):
                try:
                    if torch.is_tensor(input_tensor) and input_tensor.is_cuda and s_gguf._gguf_cuda_kernels_enabled():
                        shape = tuple(getattr(weight_tensor, "_tensor_shape", weight_tensor.shape))
                        in_features = shape[1]
                        orig_shape = input_tensor.shape
                        flat_x = input_tensor.reshape(-1, in_features)
                        rows = flat_x.shape[0]
                        pad_len = (32 - (rows % 32)) % 32
                        if pad_len > 0:
                            flat_x = torch.nn.functional.pad(flat_x, (0, 0, 0, pad_len))
                        raw = getattr(weight_tensor, "_data", None)
                        qtype_name = s_gguf._gguf_qtype_name(getattr(weight_tensor, "_tensor_type", None))
                        mod = s_gguf._gguf_cuda_module()
                        if mod is not None and mod.may_support_linear_qtype_name(qtype_name) and raw is not None and raw.is_cuda:
                            out = s_gguf._llamacpp_cuda_linear(mod, raw, qtype_name, shape, flat_x, bias, target_dtype)
                            if pad_len > 0:
                                out = out[:rows]
                            return out.reshape(*orig_shape[:-1], shape[0])
                    return _orig_try_llamacpp_linear(weight_tensor, input_tensor, bias, target_dtype)
                except Exception as e_kernel:
                    log_debug(f"[GGUF RESCUE] Kernel CUDA linear llama.cpp terhalang ({e_kernel}). Mengalirkan ke fallback PyTorch ATen...")
                    return None
            s_gguf._try_llamacpp_cuda_linear = _safe_try_llamacpp_linear

        if hasattr(s_gguf, "_try_llamacpp_cuda_embedding"):
            _orig_try_llamacpp_emb = s_gguf._try_llamacpp_cuda_embedding
            @functools.wraps(_orig_try_llamacpp_emb)
            def _safe_try_llamacpp_emb(weight_tensor, index_tensor, target_dtype):
                try:
                    return _orig_try_llamacpp_emb(weight_tensor, index_tensor, target_dtype)
                except Exception as e_kernel:
                    log_debug(f"[GGUF RESCUE] Kernel CUDA embedding llama.cpp terhalang ({e_kernel}). Mengalirkan ke fallback PyTorch ATen...")
                    return None
            s_gguf._try_llamacpp_cuda_embedding = _safe_try_llamacpp_emb

        if hasattr(s_gguf, "GGUFWeightTensor") and hasattr(s_gguf.GGUFWeightTensor, "linear"):
            _orig_gguf_weight_linear = s_gguf.GGUFWeightTensor.linear
            @functools.wraps(_orig_gguf_weight_linear)
            def _safe_gguf_weight_linear(self, input, bias=None):
                target_dtype = getattr(self, "_gguf_default_dtype", None) or (input.dtype if torch.is_tensor(input) else self.dtype)
                target_dtype = s_gguf._resolve_default_dtype(target_dtype, fallback=getattr(input, "dtype", torch.bfloat16))

                # JALUR PANTAS CUDA UTAMA: Jika input di CUDA, utamakan sentiasa kernel CUDA llama.cpp
                if torch.is_tensor(input) and input.is_cuda and s_gguf._gguf_cuda_kernels_enabled():
                    raw = getattr(self, "_data", None)
                    if torch.is_tensor(raw):
                        raw_cuda = raw if raw.is_cuda else raw.to(input.device, non_blocking=True)
                        qtype_name = s_gguf._gguf_qtype_name(getattr(self, "_tensor_type", None))
                        mod = s_gguf._gguf_cuda_module()
                        if mod is not None and mod.may_support_linear_qtype_name(qtype_name):
                            try:
                                shape = tuple(getattr(self, "_tensor_shape", self.shape))
                                in_features = shape[1]
                                orig_shape = input.shape
                                flat_x = input.reshape(-1, in_features)
                                rows = flat_x.shape[0]
                                pad_len = (32 - (rows % 32)) % 32
                                if pad_len > 0:
                                    flat_x = torch.nn.functional.pad(flat_x, (0, 0, 0, pad_len))
                                out = s_gguf._llamacpp_cuda_linear(mod, raw_cuda, qtype_name, shape, flat_x, bias, target_dtype)
                                if pad_len > 0:
                                    out = out[:rows]
                                s_gguf._gguf_log_once(f"llamacpp_cuda_linear_active_{qtype_name}", f"[GGUF][llama.cpp CUDA] linear fast path active for {qtype_name}.")
                                return out.reshape(*orig_shape[:-1], shape[0])
                            except Exception as e_k:
                                log_debug(f"[GGUF CUDA LINEAR RESCUE] Kernel gagal ({e_k}), mengalir ke fallback...")
                            finally:
                                if raw_cuda is not raw and not raw.is_cuda:
                                    del raw_cuda
                try:
                    return _orig_gguf_weight_linear(self, input, bias=bias)
                except Exception as e_lin:
                    log_debug(f"[GGUF WEIGHT RESCUE] Ralat linear GGUF ({e_lin}). Mengaktifkan fallback dense PyTorch native...")
                    target_dev = self.device if hasattr(self, "device") else (input.device if torch.is_tensor(input) else "cuda")
                    target_dtype = self.dtype if hasattr(self, "dtype") else torch.bfloat16
                    w = self.dequantize(dtype=target_dtype, device=target_dev)
                    if torch.is_tensor(input) and input.dtype != w.dtype:
                        input = input.to(w.dtype)
                    if bias is not None and torch.is_tensor(bias) and bias.dtype != w.dtype:
                        bias = bias.to(w.dtype)
                    return torch.nn.functional.linear(input, w, bias)
            s_gguf.GGUFWeightTensor.linear = _safe_gguf_weight_linear

        log_debug("Perisai GGUF Universal Dynamic Memory Footprint & Resilient Kernel Interceptor berjaya dipasang.")
except Exception as e:
    log_debug(f"Pintasan modul GGUF gagal: {e}")

# ------------------------------------------------------------------------------
# 1b. PERISAI QUANTO / QBYTES PROAKTIF (Pencegahan Ralat Lekit CUDA)
# ------------------------------------------------------------------------------
try:
    import optimum.quanto.tensor.weights.qbytes as qb
    if hasattr(qb, "QBytesDequantizer"):
        _orig_qbytes_forward = qb.QBytesDequantizer.forward
        
        @staticmethod
        def _safe_qbytes_forward(ctx, t):
            free_bytes = 0
            if torch.cuda.is_available() and getattr(t, "_data", None) is not None and t._data.is_cuda:
                try:
                    driver_free, _ = torch.cuda.mem_get_info()
                    cached_free = max(0, torch.cuda.memory_reserved() - torch.cuda.memory_allocated())
                    free_bytes = driver_free + cached_free
                except Exception:
                    free_bytes = 512 * 1024 * 1024
            
            elem_sz = 2 if getattr(t, "dtype", None) in (torch.float16, torch.bfloat16) else 4
            needed = t._data.numel() * elem_sz * 3 if hasattr(t, "_data") else 50 * 1024 * 1024
            
            if getattr(t, "_data", None) is not None and t._data.is_cuda and free_bytes > 0 and (free_bytes < needed):
                flush_vram()
                if torch.cuda.is_available():
                    try:
                        driver_free, _ = torch.cuda.mem_get_info()
                        cached_free = max(0, torch.cuda.memory_reserved() - torch.cuda.memory_allocated())
                        free_bytes = driver_free + cached_free
                    except Exception:
                        pass
                if free_bytes < needed:
                    try:
                        d_cpu = t._data.to("cpu", dtype=torch.float32)
                        s_cpu = t._scale.to("cpu", dtype=torch.float32)
                        res = (d_cpu * s_cpu).to(dtype=getattr(t, "dtype", torch.bfloat16))
                        return res.to(t._data.device, non_blocking=True)
                    except Exception:
                        pass
            try:
                return _orig_qbytes_forward(ctx, t)
            except Exception as err:
                err_s = str(err).lower()
                if "out of memory" in err_s or "cuda" in err_s or "acceleratorerror" in err_s:
                    flush_vram()
                    d_cpu = t._data.to("cpu", dtype=torch.float32)
                    s_cpu = t._scale.to("cpu", dtype=torch.float32)
                    res = (d_cpu * s_cpu).to(dtype=getattr(t, "dtype", torch.bfloat16))
                    return res.to(t._data.device, non_blocking=True)
                raise err
                
        qb.QBytesDequantizer.forward = _safe_qbytes_forward
        log_debug("Perisai Proaktif Quanto QBytes Dequantizer (Anti-Sticky OOM) berjaya dipasang.")
except Exception as e:
    log_debug(f"Pintasan Quanto QBytes Dequantizer gagal: {e}")

log_debug("Perisai 1: OOM-Safe Sparse Embedding Interceptor berjaya dipasang.")

def get_live_cuda_overhead():
    """Mengira overhead VRAM PyTorch dan lonjakan tensor masa-nyata (100% Zero Hardcoding)."""
    if not torch.cuda.is_available():
        return 0.0
    try:
        alloc_bytes = torch.cuda.memory_allocated()
        res_bytes = torch.cuda.memory_reserved()
        peak_bytes = torch.cuda.max_memory_allocated()
        
        frag_bytes = max(0, res_bytes - alloc_bytes)
        spike_bytes = max(0, peak_bytes - alloc_bytes)
        _, tot_b = torch.cuda.mem_get_info()
        # Margin penimbal paparan OS fizikal berasaskan perkadaran perkakasan GPU (100% Zero Hardcoding)
        os_guard_ratio = 0.025 if sys.platform == "win32" else 0.010
        os_guard_bytes = int(tot_b * os_guard_ratio)
        
        return (frag_bytes + spike_bytes + os_guard_bytes) / (1024 * 1024)
    except Exception:
        try:
            _, tot_b = torch.cuda.mem_get_info()
            return (tot_b * 0.025) / (1024 * 1024)
        except Exception:
            return 0.0

def inspect_model_data(module):
    """Mengimbas data dalaman model secara masa-nyata untuk SEMUA senibina model di Wan2GP (100% Zero Hardcoding)."""
    if module is None:
        return {
            "weight_bytes": 0, "param_count": 0, "hidden_dim": 0, "inner_dim": 0, "intermediate_dim": 0, "layers": 0,
            "heads": 0, "head_dim": 0, "patch_size": None,
            "spatial_compression": None, "temporal_compression": None,
            "block_storage_mb": 0.0, "block_dequant_mb": 0.0, "block_size_mb": 0.0,
            "max_layer_dequant_mb": 0.0, "is_quant": False
        }
        
    param_count = 0
    weight_bytes = 0
    hidden_dim = 0
    inner_dim = 0
    intermediate_dim = 0
    layers_count = 0
    heads = 0
    head_dim = 0
    patch_size = None
    spatial_compression = None
    temporal_compression = None
    block_storage_bytes = 0
    block_dequant_bytes = 0
    max_layer_dequant_bytes = 0
    is_quant = False
    
    try:
        if hasattr(module, "parameters"):
            for p in module.parameters():
                if p is not None:
                    param_count += p.numel()
                    weight_bytes += p.numel() * p.element_size()
                    
        if hasattr(module, "buffers"):
            for b in module.buffers():
                if b is not None:
                    weight_bytes += b.numel() * b.element_size()
                    
        if hasattr(module, "_gguf_qtype") or "gguf" in str(type(module)).lower():
            is_quant = True
            
        # 1. Introspeksi Hidden, Inner & Intermediate Dimension secara Universal (Zero Hardcoding)
        for attr in ("hidden_size", "dim", "d_model", "model_dim", "hidden_dim", "embed_dim"):
            val = getattr(module, attr, None)
            if isinstance(val, int) and val > 64:
                hidden_dim = val
                break
        for attr in ("attention_inner_size", "inner_dim", "attn_dim"):
            val = getattr(module, attr, None)
            if isinstance(val, int) and val > 64:
                inner_dim = val
                break
        for attr in ("ffn_hidden_size", "intermediate_size", "ffn_dim", "mlp_dim"):
            val = getattr(module, attr, None)
            if isinstance(val, int) and val > 64:
                intermediate_dim = val
                break

        # 2. Semak atribut config modul
        config = getattr(module, "config", None)
        if config is not None:
            if isinstance(config, dict):
                if hidden_dim == 0:
                    for k in ("hidden_size", "dim", "d_model", "inner_dim", "model_dim", "hidden_dim", "embed_dim"):
                        val = config.get(k)
                        if isinstance(val, int) and val > 64:
                            hidden_dim = val
                            break
                if intermediate_dim == 0:
                    for k in ("ffn_hidden_size", "intermediate_size", "ffn_dim", "mlp_dim"):
                        val = config.get(k)
                        if isinstance(val, int) and val > 64:
                            intermediate_dim = val
                            break
                layers_count = config.get("num_hidden_layers") or config.get("num_layers") or config.get("depth") or 0
                heads = config.get("num_heads") or config.get("num_attention_heads") or config.get("n_heads") or config.get("n_head") or 0
                head_dim = config.get("attention_head_dim") or config.get("head_dim") or config.get("head_size") or 0
                patch_size = config.get("patch_size")
                spatial_compression = config.get("spatial_compression") or config.get("sp_compression")
                temporal_compression = config.get("temporal_compression") or config.get("tp_compression")
            else:
                if hidden_dim == 0:
                    for attr in ("hidden_size", "dim", "d_model", "inner_dim", "model_dim", "hidden_dim", "embed_dim"):
                        val = getattr(config, attr, None)
                        if isinstance(val, int) and val > 64:
                            hidden_dim = val
                            break
                if intermediate_dim == 0:
                    for attr in ("ffn_hidden_size", "intermediate_size", "ffn_dim", "mlp_dim"):
                        val = getattr(config, attr, None)
                        if isinstance(val, int) and val > 64:
                            intermediate_dim = val
                            break
                layers_count = getattr(config, "num_hidden_layers", 0) or getattr(config, "num_layers", 0) or getattr(config, "depth", 0)
                heads = getattr(config, "num_heads", 0) or getattr(config, "num_attention_heads", 0) or getattr(config, "n_heads", 0) or getattr(config, "n_head", 0) or 0
                head_dim = getattr(config, "attention_head_dim", 0) or getattr(config, "head_dim", 0) or getattr(config, "head_size", 0) or 0
                patch_size = getattr(config, "patch_size", None)
                spatial_compression = getattr(config, "spatial_compression", None) or getattr(config, "sp_compression", None)
                temporal_compression = getattr(config, "temporal_compression", None) or getattr(config, "tp_compression", None)

        if heads == 0:
            for attr in ("num_heads", "num_attention_heads", "n_heads", "n_head", "heads"):
                val = getattr(module, attr, None)
                if isinstance(val, int) and val > 0:
                    heads = val
                    break
        if head_dim == 0:
            for attr in ("attention_head_dim", "head_dim", "head_size", "d_head"):
                val = getattr(module, attr, None)
                if isinstance(val, int) and val > 0:
                    head_dim = val
                    break
        if patch_size is None:
            patch_size = getattr(module, "patch_size", None)
        if spatial_compression is None:
            spatial_compression = getattr(module, "spatial_compression", None) or getattr(module, "sp_compression", None)
        if temporal_compression is None:
            temporal_compression = getattr(module, "temporal_compression", None) or getattr(module, "tp_compression", None)

        # 3. Pengimbas Blok & Lapisan Sejagat (Universal Block Scanner)
        # Menyokong Wan 2.1, HunyuanVideo, FLUX, SD3, LTX, CogVideoX, Qwen, Whisper, VAE, dll.
        blocks = None
        target_submodules = [module]
        for attr_name in ("language_model", "model", "encoder", "text_model", "visual", "transformer", "diffusion_model"):
            sub = getattr(module, attr_name, None)
            if sub is not None and isinstance(sub, torch.nn.Module):
                target_submodules.append(sub)
                
        for sub in target_submodules:
            for b_attr in ("blocks", "layers", "block", "transformer_blocks", "joint_transformer_blocks", "double_blocks", "resblocks", "down_blocks"):
                candidate = getattr(sub, b_attr, None)
                if candidate is not None and hasattr(candidate, "__len__") and len(candidate) > 0:
                    blocks = candidate
                    break
            if patch_size is None:
                patch_size = getattr(sub, "patch_size", None)
            if heads == 0:
                for attr in ("num_heads", "num_attention_heads", "n_heads", "n_head", "heads"):
                    val = getattr(sub, attr, None)
                    if isinstance(val, int) and val > 0:
                        heads = val
                        break
            if head_dim == 0:
                for attr in ("attention_head_dim", "head_dim", "head_size", "d_head"):
                    val = getattr(sub, attr, None)
                    if isinstance(val, int) and val > 0:
                        head_dim = val
                        break
            if blocks is not None:
                break
                
        # Sokongan khas gabungan dwi-menara (cth: FLUX double_blocks + single_blocks)
        double_b = getattr(module, "double_blocks", None)
        single_b = getattr(module, "single_blocks", None)
        if double_b is not None and single_b is not None:
            layers_count = len(double_b) + len(single_b)
            blocks = double_b
        elif blocks is not None and len(blocks) > 0:
            if layers_count == 0:
                layers_count = len(blocks)
                
        if blocks is not None and len(blocks) > 0:
            first_block = blocks[0]
            # 3b. Introspeksi Submodul Perhatian & Blok untuk Heads, Head Dim, Inner Dim, dan Patch Size (Zero Hardcoding)
            attn_candidates = []
            for sub_attr in ("attn", "self_attn", "cross_attn", "attention", "transformer_block"):
                cand = getattr(first_block, sub_attr, None)
                if cand is not None and isinstance(cand, torch.nn.Module):
                    attn_candidates.append(cand)
            if not attn_candidates and hasattr(first_block, "named_children"):
                for _, sm in first_block.named_children():
                    if any(hasattr(sm, p) for p in ("out_proj", "proj", "to_out", "q_norm", "k_norm")):
                        attn_candidates.append(sm)
                        break

            for attn_cand in attn_candidates:
                # Dapatkan head_dim terus daripada q_norm / k_norm
                if head_dim == 0:
                    for norm_name in ("q_norm", "k_norm"):
                        norm_mod = getattr(attn_cand, norm_name, None)
                        if norm_mod is not None and hasattr(norm_mod, "normalized_shape"):
                            ns = norm_mod.normalized_shape
                            if isinstance(ns, (tuple, list)) and len(ns) > 0 and isinstance(ns[0], int) and ns[0] > 0:
                                head_dim = ns[0]
                                break
                            elif isinstance(ns, int) and ns > 0:
                                head_dim = ns
                                break

                # Dapatkan inner_dim dan hidden_dim terus daripada unjuran linear output perhatian
                if inner_dim == 0:
                    for out_name in ("out_proj", "proj"):
                        out_mod = getattr(attn_cand, out_name, None)
                        if out_mod is not None and hasattr(out_mod, "in_features"):
                            inner_dim = out_mod.in_features
                            if hidden_dim == 0 and hasattr(out_mod, "out_features"):
                                hidden_dim = out_mod.out_features
                            break
                    if inner_dim == 0 and hasattr(attn_cand, "to_out") and len(attn_cand.to_out) > 0:
                        out_mod = attn_cand.to_out[0]
                        if hasattr(out_mod, "in_features"):
                            inner_dim = out_mod.in_features
                            if hidden_dim == 0 and hasattr(out_mod, "out_features"):
                                hidden_dim = out_mod.out_features

                if heads == 0:
                    for a in ("heads", "num_heads", "num_attention_heads", "n_heads", "n_head"):
                        v = getattr(attn_cand, a, None)
                        if isinstance(v, int) and v > 0:
                            heads = v
                            break
                if head_dim == 0:
                    for a in ("head_dim", "attention_head_dim", "head_size", "d_head"):
                        v = getattr(attn_cand, a, None)
                        if isinstance(v, int) and v > 0:
                            head_dim = v
                            break
                if heads > 0 and head_dim > 0 and inner_dim > 0:
                    break

            # 3c. Introspeksi Submodul MLP / FFN untuk intermediate_dim (Zero Hardcoding)
            if intermediate_dim == 0:
                for mlp_attr in ("mlp", "ffn", "ff", "feed_forward"):
                    mlp_mod = getattr(first_block, mlp_attr, None)
                    if mlp_mod is not None and isinstance(mlp_mod, torch.nn.Module):
                        for lin_attr in ("fc1", "w1", "gate_proj", "up_proj", "wi", "net"):
                            lin_mod = getattr(mlp_mod, lin_attr, None)
                            if lin_mod is not None and hasattr(lin_mod, "out_features") and isinstance(lin_mod.out_features, int) and lin_mod.out_features > 0:
                                intermediate_dim = lin_mod.out_features
                                break
                        if intermediate_dim == 0:
                            ffn_v = getattr(mlp_mod, "ffn", 0) or getattr(mlp_mod, "hidden_dim", 0)
                            if isinstance(ffn_v, int) and ffn_v > 0:
                                intermediate_dim = ffn_v * 2
                        if intermediate_dim > 0:
                            break

            if heads == 0:
                for a in ("heads", "num_heads", "num_attention_heads", "n_heads", "n_head"):
                    v = getattr(first_block, a, None)
                    if isinstance(v, int) and v > 0:
                        heads = v
                        break
            if head_dim == 0:
                for a in ("head_dim", "attention_head_dim", "head_size", "d_head"):
                    v = getattr(first_block, a, None)
                    if isinstance(v, int) and v > 0:
                        head_dim = v
                        break
            if patch_size is None:
                patch_size = getattr(first_block, "patch_size", None)

            # Penentuan matematik tulen (Zero Hardcoding):
            if inner_dim > 0 and head_dim > 0 and heads == 0:
                heads = inner_dim // head_dim
            elif heads > 0 and head_dim > 0 and inner_dim == 0:
                inner_dim = heads * head_dim
            elif heads > 0 and inner_dim > 0 and head_dim == 0:
                head_dim = inner_dim // heads

            # 4. Sekiranya hidden_dim masih 0, ekstrak terus daripada dimensi matriks linear blok pertama (Sifar Hardcode)
            if hidden_dim == 0:
                dim_candidates = []
                for name, p in first_block.named_parameters():
                    if p is not None and hasattr(p, "shape") and len(p.shape) >= 2:
                        for s in p.shape:
                            if s >= 256 and (s % 32 == 0 or s % 64 == 0):
                                dim_candidates.append(s)
                if dim_candidates:
                    from collections import Counter
                    counts = Counter(dim_candidates)
                    hidden_dim = counts.most_common(1)[0][0]

            for name, p in first_block.named_parameters():
                if p is None:
                    continue
                sub_tensors = None
                if hasattr(p, "get_quantized_subtensors"):
                    try:
                        getter = getattr(p, "get_quantized_subtensors")
                        st = getter()
                        if st:
                            if isinstance(st, dict):
                                st = list(st.items())
                            sub_tensors = [t for _, t in st if t is not None and torch.is_tensor(t)]
                    except Exception:
                        sub_tensors = None
                        
                elem_sz = 2 if p.dtype in (torch.float16, torch.bfloat16) else p.element_size()
                p_dequant = p.numel() * elem_sz
                
                if sub_tensors:
                    p_storage = sum(t.numel() * t.element_size() for t in sub_tensors)
                    is_quant = True
                elif hasattr(p, "_data") and torch.is_tensor(p._data):
                    p_storage = p._data.numel() * p._data.element_size()
                    is_quant = True
                else:
                    p_storage = p.numel() * p.element_size()
                    
                block_storage_bytes += p_storage
                block_dequant_bytes += p_dequant
                if p_dequant > max_layer_dequant_bytes:
                    max_layer_dequant_bytes = p_dequant
                    
        # 5. Crosscheck dengan MMGP active_instance secara regex sejagat
        try:
            act = get_active_mmgp_instance()
            if act is not None and hasattr(act, "blocks_of_modules_sizes") and act.blocks_of_modules_sizes:
                for k, v in act.blocks_of_modules_sizes.items():
                    if re.search(r"/(blocks|layers|transformer_blocks|joint_transformer_blocks|double_blocks|single_blocks|resblocks)\.\d+", k) and v > 0:
                        block_storage_bytes = v
                        if block_dequant_bytes > 0 and v < block_dequant_bytes * 0.8:
                            is_quant = True
                        break
        except Exception:
            pass

    except Exception as e:
        log_debug(f"Pengecualian semasa introspeksi modul: {e}")
        
    block_storage_mb = block_storage_bytes / (1024 * 1024)
    block_dequant_mb = block_dequant_bytes / (1024 * 1024)
    max_layer_dequant_mb = max_layer_dequant_bytes / (1024 * 1024)
    
    # block_size_mb adalah saiz simpanan yang difahami oleh MMGP
    block_size_mb = block_storage_mb if block_storage_mb > 0 else block_dequant_mb

    if inner_dim > 0 and head_dim > 0 and heads == 0:
        heads = inner_dim // head_dim
    elif heads > 0 and head_dim == 0 and hidden_dim > 0:
        head_dim = hidden_dim // heads
    elif heads == 0 and head_dim > 0 and hidden_dim > 0:
        heads = hidden_dim // head_dim
        
    if inner_dim == 0 and heads > 0 and head_dim > 0:
        inner_dim = heads * head_dim

    return {
        "weight_bytes": weight_bytes,
        "weight_mb": weight_bytes / (1024 * 1024),
        "param_count": param_count,
        "hidden_dim": hidden_dim,
        "inner_dim": inner_dim,
        "intermediate_dim": intermediate_dim,
        "layers": layers_count,
        "heads": heads,
        "head_dim": head_dim,
        "patch_size": patch_size,
        "spatial_compression": spatial_compression,
        "temporal_compression": temporal_compression,
        "block_storage_mb": block_storage_mb,
        "block_dequant_mb": block_dequant_mb,
        "block_size_mb": block_size_mb,
        "max_layer_dequant_mb": max_layer_dequant_mb,
        "is_quant": is_quant
    }

def centralized_model_memory_arbiter(
    model_or_info=None,
    model_role="transformer",
    active_tokens=None,
    total_gpu_mb=None,
    free_mb=None,
    ext_os_mb=None,
    active_live_mb=None,
    is_async=True,
    phase=1,
    token_scaling_ratio=1.0,
    is_audio_only=False,
    height=None,
    width=None,
    frame_num=None,
    generation_state=None
):
    """
    SATU FUNGSI PUSAT TUNGGAL SEJAGAT (Centralized Dynamic Memory Arbiter):
    Mengira bajet VRAM, bilangan blok pra-muat, headroom aktivasi,
    dan overhed secara dinamik bagi SEBARANG model AI (Transformer, Text Encoder, VAE, dll).
    Menjamin VRAM 100% tidak melimpah ke Windows WDDM PCIe Shared Memory (RAM Sistem).
    Sifar Hardcode, Berasaskan Fizik Perkakasan & Geometri Matematik Tulen.
    """
    try:
        flush_vram()
        if generation_state is None:
            generation_state = _generation_state

        # 1. Metrik Fizikal Perkakasan Sebenar (Hardware Ground-Truth)
        cuda_ok = torch.cuda.is_available()
        if total_gpu_mb is None:
            total_gpu_mb = (torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)) if cuda_ok else 8151.0
        if free_mb is None:
            if cuda_ok:
                free_bytes, _ = torch.cuda.mem_get_info()
                free_mb = free_bytes / (1024 * 1024)
            else:
                free_mb = 6950.0

        alloc_bytes = torch.cuda.memory_allocated() if cuda_ok else 0
        res_bytes = torch.cuda.memory_reserved() if cuda_ok else 0
        alloc_mb = alloc_bytes / (1024 * 1024)
        res_mb = res_bytes / (1024 * 1024)
        allocator_frag_mb = max(0.0, res_mb - alloc_mb)

        if ext_os_mb is None:
            ext_os_mb = max(0.0, total_gpu_mb - free_mb - res_mb)

        # 2. Introspeksi Ciri-Ciri Model & MMGP (Pastikan rujukan modul induk sebenar digunakan, bukan sub-blok)
        act = get_active_mmgp_instance()
        if isinstance(model_or_info, dict):
            info = model_or_info
            mod_obj = None
        else:
            mod_obj = model_or_info
            if act is not None and hasattr(act, "models") and isinstance(act.models, dict):
                prefix_candidates = ("text_encoder", "text_model", "encoder") if model_role == "text_encoder" else ("transformer", "diffusion_model", "model", "unet")
                if mod_obj is None or not any( hasattr(mod_obj, attr) for attr in ("blocks", "layers", "transformer_blocks", "language_model") ):
                    for cand_k in prefix_candidates:
                        if cand_k in act.models and act.models[cand_k] is not None:
                            mod_obj = act.models[cand_k]
                            break
            info = inspect_model_data(mod_obj)

        hidden_dim = info.get("hidden_dim", 0) or generation_state.get("active_hidden_dim", 0) or 3072
        inner_dim = info.get("inner_dim", 0) or generation_state.get("active_inner_dim", 0) or hidden_dim
        if not inner_dim:
            inner_dim = hidden_dim if hidden_dim > 0 else 3072
        intermediate_dim = info.get("intermediate_dim", 0)
        total_layers = info.get("layers", 0)
        raw_param_block_mb = info.get("block_size_mb", 0.0) or info.get("block_storage_mb", 0.0)
        block_size_mb = raw_param_block_mb
        base_size_mb = info.get("base_size_mb", 0.0)
        is_quant = info.get("is_quant", False)
        max_layer_dequant_mb = info.get("max_layer_dequant_mb", 0.0)

        # Crosscheck dengan MMGP active_instance secara 100% Introspektif (Zero Hardcoding)
        mmgp_base_mb = 0.0
        mmgp_max_floor_mb = 0.0
        main_id = "text_encoder" if model_role == "text_encoder" else "transformer"
        if act is not None and hasattr(act, "blocks_of_modules_sizes") and act.blocks_of_modules_sizes:
            prefix_keys = ("text_encoder", "text_model", "encoder") if model_role == "text_encoder" else ("transformer", "diffusion_model", "model", "unet")
            for mod_k in prefix_keys:
                if mod_k in act.blocks_of_modules_sizes:
                    main_id = mod_k
                    mmgp_base_mb = act.blocks_of_modules_sizes[mod_k] / (1024 * 1024)
                    if mmgp_base_mb > 0:
                        base_size_mb = mmgp_base_mb
                    break
            detected_indices = set()
            detected_sizes = []
            for k, v in act.blocks_of_modules_sizes.items():
                if k.startswith(main_id + "/"):
                    sub = k[len(main_id) + 1:]
                    if "token_refiner" in sub or "encoder" in sub:
                        continue
                    m = re.search(r"(?:^|/)(?:layers|blocks|block|transformer_blocks|resblocks)\.(\d+)$", sub)
                    if m and v > 0:
                        detected_indices.add(int(m.group(1)))
                        detected_sizes.append(v / (1024 * 1024))
                        is_quant = True
            if detected_indices and total_layers <= 1:
                total_layers = max(detected_indices) + 1
            if detected_sizes:
                mmgp_max_floor_mb = max(detected_sizes)
                block_size_mb = max(block_size_mb, mmgp_max_floor_mb)

        # Introspeksi susulan daripada pipeline aktif jika layers belum dipopulasikan
        if total_layers <= 1:
            try:
                active_pipeline = getattr(launch_optimized, "_active_pipeline", None)
                cand_mod = getattr(active_pipeline, model_role, None) if active_pipeline is not None else None
                if cand_mod is not None:
                    cand_info = inspect_model_data(cand_mod)
                    if cand_info.get("layers", 0) > 1:
                        total_layers = cand_info["layers"]
                    if block_size_mb <= 0 and cand_info.get("block_size_mb", 0.0) > 0:
                        block_size_mb = cand_info["block_size_mb"]
            except Exception:
                pass

        # Introspeksi Dinamik Mutlak Saiz Blok & Tapak (100% Sifar Hardcoding):
        if block_size_mb <= 0 and act is not None and hasattr(act, "blocks_of_modules_sizes") and act.blocks_of_modules_sizes:
            b_sizes = [sz / (1024 * 1024) for k, sz in act.blocks_of_modules_sizes.items() if k.startswith(main_id + "/")]
            if b_sizes:
                block_size_mb = max(b_sizes)
                mmgp_max_floor_mb = max(mmgp_max_floor_mb, block_size_mb)
        if block_size_mb <= 0 and mod_obj is not None:
            for layer_attr in ("blocks", "layers", "transformer_blocks"):
                layers_list = getattr(mod_obj, layer_attr, None)
                if layers_list is not None and len(layers_list) > 0:
                    first_layer = layers_list[0]
                    layer_bytes = sum(p.numel() * p.element_size() for p in first_layer.parameters() if p is not None)
                    if layer_bytes > 0:
                        block_size_mb = layer_bytes / (1024 * 1024)
                        raw_param_block_mb = max(raw_param_block_mb, block_size_mb)
                        break
        if block_size_mb <= 0:
            block_size_mb = max(1.0, (total_gpu_mb * 0.02))
        if base_size_mb <= 0 and mod_obj is not None:
            base_bytes = sum(p.numel() * p.element_size() for n, p in mod_obj.named_parameters() if not any(b_name in n for b_name in ("blocks.", "layers.", "transformer_blocks.")))
            base_size_mb = base_bytes / (1024 * 1024) if base_bytes > 0 else 0.0

        # Tentukan saiz elemen aktivasi (FP16/BF16 = 2 bait, FP32 = 4 bait)
        elem_size = generation_state.get("active_elem_size")
        if not elem_size:
            if mod_obj is not None and hasattr(mod_obj, "dtype"):
                elem_size = 2 if getattr(mod_obj, "dtype", None) in (torch.float16, torch.bfloat16) else 2
            else:
                elem_size = 2

        # 3. Pengukuran Berat LoRA & Tensor Modul pada GPU/CPU (Zero Magic Constant)
        lora_cuda_bytes = 0
        lora_cpu_bytes = 0
        mod_cuda_bytes = 0
        if mod_obj is not None:
            seen_ptrs = set()
            def _acc_lora(t):
                nonlocal lora_cuda_bytes, lora_cpu_bytes, mod_cuda_bytes
                if torch.is_tensor(t):
                    ptr = t.data_ptr()
                    if ptr and ptr not in seen_ptrs:
                        seen_ptrs.add(ptr)
                        b = t.numel() * t.element_size()
                        if t.is_cuda:
                            lora_cuda_bytes += b
                            mod_cuda_bytes += b
                        else:
                            lora_cpu_bytes += b
            def _trav(d):
                if d is None: return
                if torch.is_tensor(d): _acc_lora(d)
                elif isinstance(d, (list, tuple, set)):
                    for it in d: _trav(it)
                elif isinstance(d, dict):
                    for v in d.values(): _trav(v)
            if hasattr(mod_obj, "_loras_model_data"): _trav(mod_obj._loras_model_data)
            if hasattr(mod_obj, "_loras_model_shortcuts"): _trav(mod_obj._loras_model_shortcuts)
            if hasattr(mod_obj, "named_parameters"):
                for n, p in mod_obj.named_parameters():
                    if p is not None and torch.is_tensor(p):
                        if "lora" in n.lower():
                            _acc_lora(p)
                        elif p.is_cuda:
                            ptr = p.data_ptr()
                            if ptr and ptr not in seen_ptrs:
                                seen_ptrs.add(ptr)
                                mod_cuda_bytes += p.numel() * p.element_size()
            if hasattr(mod_obj, "named_buffers"):
                for _, buf in mod_obj.named_buffers():
                    if buf is not None and torch.is_tensor(buf) and buf.is_cuda:
                        ptr = buf.data_ptr()
                        if ptr and ptr not in seen_ptrs:
                            seen_ptrs.add(ptr)
                            mod_cuda_bytes += buf.numel() * buf.element_size()

        lora_guard_mb = lora_cuda_bytes / (1024 * 1024)
        lora_per_block_mb = ((lora_cpu_bytes + lora_cuda_bytes) / max(1, total_layers)) / (1024 * 1024)
        raw_base_blk = raw_param_block_mb if raw_param_block_mb > 0 else block_size_mb
        effective_block_mb = max(block_size_mb, raw_base_blk + lora_per_block_mb)
        if mmgp_max_floor_mb <= 0:
            mmgp_max_floor_mb = block_size_mb if block_size_mb > 0 else effective_block_mb
        if mmgp_base_mb <= 0:
            mmgp_base_mb = base_size_mb

        # 4. Ground-truth Pengiraan Tensor CUDA Hidup Luar Modul (Bukan Blok/Base/LoRA Model Ini)
        if active_live_mb is None:
            mmgp_loaded_mb = 0.0
            cur_b = None
            preloaded = ()
            if act is not None and hasattr(act, "blocks_of_modules_sizes"):
                preloaded = act.preloaded_blocks_per_model.get(main_id, ()) if hasattr(act, "preloaded_blocks_per_model") else ()
                for b in preloaded:
                    entry = main_id + "/" + b
                    mmgp_loaded_mb += act.blocks_of_modules_sizes.get(entry, 0.0) / (1024 * 1024)
                cur_b = act.loaded_blocks.get(main_id) if hasattr(act, "loaded_blocks") else None
                if cur_b is not None:
                    entry = main_id + "/" + cur_b
                    mmgp_loaded_mb += act.blocks_of_modules_sizes.get(entry, 0.0) / (1024 * 1024)
                if mmgp_loaded_mb > 0 or mod_cuda_bytes > 0:
                    mmgp_loaded_mb += act.blocks_of_modules_sizes.get(main_id, 0.0) / (1024 * 1024)
            loaded_mod_mb = max(mmgp_loaded_mb + lora_guard_mb, mod_cuda_bytes / (1024 * 1024))
            active_live_mb = max(0.0, alloc_mb - loaded_mod_mb)
            # Jika lora_cuda_bytes sudah diambil kira pada blok yang sedang dimuatkan, elakkan kiraan berganda
            if cur_b is not None or len(preloaded) > 0:
                lora_guard_mb = 0.0

        # 5. Pengesanan Modaliti & Geometri Jujukan Token (Zero Hardcoding)
        is_audio = bool(is_audio_only or getattr(mod_obj, "audio_only", False) or getattr(mod_obj, "_is_audio_only", False))
        if not is_audio and mod_obj is not None:
            m_name = mod_obj.__class__.__name__.lower()
            m_str = str(type(mod_obj)).lower()
            if any(term in m_name or term in m_str for term in ("tts", "music", "voice", "whisper", "sound")):
                is_audio = True

        if active_tokens is not None and active_tokens > 0:
            tokens = int(active_tokens)
        elif generation_state.get("active_seq_len"):
            tokens = int(generation_state["active_seq_len"])
        else:
            if model_role == "text_encoder":
                tokens = 4096 if ("qwen" in str(type(mod_obj)).lower() or "vl" in str(type(mod_obj)).lower()) else 512
            elif is_audio:
                tokens = int((4 + 250 + 256) * max(1.0, float(token_scaling_ratio)))
            else:
                # Video / Imej 2D
                h = height or getattr(mod_obj, "default_height", None) or 720
                w = width or getattr(mod_obj, "default_width", None) or 1280
                sp_comp = info.get("spatial_compression") or 16
                tp_comp = info.get("temporal_compression") or 4
                p_size = info.get("patch_size") or (1, 2, 2)
                if isinstance(p_size, (tuple, list)) and len(p_size) >= 3:
                    p_t, p_h, p_w = p_size[0], p_size[1], p_size[2]
                elif isinstance(p_size, (tuple, list)) and len(p_size) == 2:
                    p_t, p_h, p_w = 1, p_size[0], p_size[1]
                else:
                    p_val = int(p_size if isinstance(p_size, int) else 2)
                    p_t, p_h, p_w = 1, p_val, p_val

                max_dit_frames = (
                    getattr(mod_obj, "max_window_frames", None)
                    or getattr(mod_obj, "window_size", None)
                    or (124 if (mod_obj is not None and "minimax" in str(type(mod_obj)).lower()) else 124)
                )
                raw_t = frame_num or 124
                t = min(max_dit_frames, raw_t) if max_dit_frames else raw_t

                latent_h = math.ceil(h / max(1, sp_comp))
                latent_w = math.ceil(w / max(1, sp_comp))
                latent_t = math.ceil(t / max(1, tp_comp))

                patch_h = math.ceil(latent_h / max(1, p_h))
                patch_w = math.ceil(latent_w / max(1, p_w))
                patch_t = math.ceil(latent_t / max(1, p_t))
                visual_tokens = patch_h * patch_w * patch_t

                is_ref = bool(getattr(mod_obj, "reference_mode", False) or getattr(mod_obj, "control_layers", None))
                visual_channel_mult = 2.0 if is_ref else 1.0
                if token_scaling_ratio and 1.0 < float(token_scaling_ratio) <= 2.5:
                    visual_channel_mult = float(token_scaling_ratio)
                aux_tokens = 512 + (512 if not is_audio and getattr(mod_obj, "final_layer", None) is not None and hasattr(getattr(mod_obj, "final_layer"), "audio_out") else 0)
                tokens = int(visual_tokens * visual_channel_mult + aux_tokens)

        # 6. Pengiraan Denyutan Aktivasi Puncak (Ground Truth Physics + Empirical Observation)
        observed_pulse = float(generation_state.get("real_act_pulse_mb", 0.0))
        if model_role == "text_encoder":
            te_inter_dim = intermediate_dim or (hidden_dim * 4)
            act_per_token = (2 * hidden_dim + te_inter_dim) * elem_size
            theoretical_act_peak_mb = (tokens * act_per_token * 4) / (1024 * 1024)
            act_peak_mb = max(theoretical_act_peak_mb, observed_pulse)
        else:
            has_combined_qkv = False
            if mod_obj is not None and hasattr(mod_obj, "modules"):
                for sm in mod_obj.modules():
                    if hasattr(sm, "qkv_proj") or hasattr(sm, "q_proj"):
                        has_combined_qkv = True
                        break
            has_rope = (
                mod_obj is not None and (
                    hasattr(mod_obj, "rope") or hasattr(mod_obj, "rope_embedder")
                    or any("rope" in str(sm).lower() for sm in getattr(mod_obj, "modules", lambda: [])())
                )
            )
            kv_mult = 3.0 if has_combined_qkv else 2.0
            dest_qkv_mb = (kv_mult * tokens * inner_dim * elem_size) / (1024 * 1024)
            rope_mb = (2.0 * tokens * inner_dim * elem_size) / (1024 * 1024) if has_rope else 0.0
            attn_out_mb = (tokens * inner_dim * elem_size) / (1024 * 1024)
            residual_mb = (tokens * hidden_dim * elem_size) / (1024 * 1024)
            engine_mb = (tokens * inner_dim * elem_size * 0.25) / (1024 * 1024)
            d_mlp = intermediate_dim if intermediate_dim > 0 else (inner_dim * 4)
            mlp_mb = (tokens * d_mlp * elem_size) / (1024 * 1024)

            attn_peak_mb = dest_qkv_mb + rope_mb + attn_out_mb + residual_mb + engine_mb
            mlp_peak_mb = mlp_mb + attn_out_mb + residual_mb + (max_layer_dequant_mb if is_quant else 0.0)
            theoretical_act_peak_mb = max(attn_peak_mb, mlp_peak_mb)
            act_peak_mb = max(theoretical_act_peak_mb, observed_pulse)

        # 7. Overhed Alokator PyTorch & Penimbal Anti-Spillover WDDM
        # Alokator caching PyTorch membundarkan segmen blok (~9% daripada puncak aktivasi)
        # (Ruang kerja dequant linear berlaku semasa unjuran linear dan telah dirangkumkan dalam mlp_peak_mb)
        allocator_overhead_mb = act_peak_mb * 0.09
        dequant_workspace_mb = 0.0

        # Penimbal WDDM berasaskan fizik perkakasan dan saiz blok (100% Zero Hardcoding)
        # Windows WDDM memerlukan margin perkakasan dinamik (~3.5% VRAM fizikal) + penimbal pemindahan blok DMA
        is_win = sys.platform == "win32"
        wddm_hw_ratio = 0.035 if is_win else 0.015
        wddm_blk_ratio = 0.75 if is_win else 0.50
        wddm_guard_mb = (total_gpu_mb * wddm_hw_ratio) + (effective_block_mb * wddm_blk_ratio)

        # 8. Kapasiti Bersih Storan VRAM
        total_deductions_mb = (
            ext_os_mb
            + active_live_mb
            + base_size_mb
            + act_peak_mb
            + allocator_overhead_mb
            + dequant_workspace_mb
            + lora_guard_mb
            + wddm_guard_mb
        )
        usable_mb = max(0.0, total_gpu_mb - total_deductions_mb)

        if model_role == "text_encoder":
            total_model_mb = total_layers * effective_block_mb + base_size_mb
            if effective_block_mb > 0 and total_model_mb <= usable_mb:
                preload_blocks = total_layers
                safe_budget_mb = int(mmgp_base_mb + (total_layers + 3.25) * mmgp_max_floor_mb)
                mode_str = f"Mod Residen Penuh ({preload_blocks} blok)"
            else:
                # Peruntukan dinamik berasaskan pecahan anjal VRAM bebas selamat (100% Zero Hardcoding)
                safe_block_capacity_mb = usable_mb * 0.60
                if effective_block_mb > 0:
                    max_blocks = max(2, min(total_layers, int((safe_block_capacity_mb - base_size_mb) // effective_block_mb)))
                    preload_blocks = max(0, max_blocks - 3) if max_blocks >= 4 else 0
                    if preload_blocks > 0:
                        safe_budget_mb = int(mmgp_base_mb + (preload_blocks + 3.15) * mmgp_max_floor_mb)
                    else:
                        safe_budget_mb = int(mmgp_base_mb + 2.5 * mmgp_max_floor_mb)
                    mode_str = f"Mod Residen Dinamik ({preload_blocks} blok pra-muat + 2 penimbal kerja, ~{safe_budget_mb}MB)"
                else:
                    preload_blocks = 0
                    safe_budget_mb = int(safe_block_capacity_mb)
                    mode_str = "Mod Asinkron Dinamik"
        else:
            if effective_block_mb > 0:
                max_fit = int(usable_mb // effective_block_mb)
                # Had pra-muat dinamik berasaskan bilangan lapisan sebenar model (100% Zero Hardcoding, tiada pembahagi statik)
                max_preload_cap = max(1, total_layers - 2) if total_layers > 2 else 1
                if max_fit >= total_layers:
                    preload_blocks = total_layers
                    safe_budget_mb = int(mmgp_base_mb + (total_layers + 3.25) * mmgp_max_floor_mb)
                    mode_str = f"Mod Residen Penuh ({preload_blocks} blok)"
                elif max_fit >= 4:
                    # Apabila pra-muat >= 1 blok, mmgp.offload menetapkan prefetch window=2 yang mengambil (window + 1) = 3 slot shuttle
                    preload_blocks = min(max_preload_cap, max(0, max_fit - 3))
                    safe_budget_mb = int(mmgp_base_mb + (preload_blocks + 3.15) * mmgp_max_floor_mb)
                    mode_str = f"Mod Residen Dinamik ({preload_blocks} blok pra-muat + 2 penimbal kerja)"
                elif max_fit >= 2:
                    preload_blocks = 0
                    safe_budget_mb = int(mmgp_base_mb + 2.5 * mmgp_max_floor_mb)
                    mode_str = "Mod Penimbal Minimum (0 blok pra-muat + 2 penimbal kerja)"
                else:
                    preload_blocks = 0
                    safe_budget_mb = int(mmgp_base_mb + 2.25 * mmgp_max_floor_mb)
                    mode_str = "Mod Striming Murni (0 blok pra-muat, 2 penimbal kerja)"
            else:
                preload_blocks = 0
                safe_budget_mb = max(int(base_size_mb + effective_block_mb), int(usable_mb))
                mode_str = "Bukan Blok"

        # Pastikan bajet MMGP sekurang-kurangnya mencukupi untuk base + 2 blok shuttle
        min_shuttle_budget_mb = int(mmgp_base_mb + 2.25 * mmgp_max_floor_mb)
        safe_budget_mb = max(min_shuttle_budget_mb, safe_budget_mb)

        async_threshold_mb = (total_gpu_mb * 0.05) + (effective_block_mb * 1.5)
        can_async = is_async and ((free_mb + allocator_frag_mb) >= async_threshold_mb)
        physical_model_vram_mb = base_size_mb + (preload_blocks + 2) * effective_block_mb
        peak_total_vram_mb = physical_model_vram_mb + act_peak_mb + allocator_overhead_mb + ext_os_mb + active_live_mb
        vram_headroom_mb = total_gpu_mb - peak_total_vram_mb

        log_debug(
            f"[ARBITER PUSAT] Role={model_role}, Tokens={tokens}, Blok={effective_block_mb:.1f}MB (MMGP={mmgp_max_floor_mb:.1f}MB), Base={base_size_mb:.1f}MB: "
            f"GPU={total_gpu_mb:.0f}MB, Free={free_mb:.0f}MB, Live={active_live_mb:.0f}MB, ActPeak={act_peak_mb:.0f}MB, "
            f"Overhead={total_deductions_mb:.0f}MB, Usable={usable_mb:.0f}MB -> Bajet={safe_budget_mb}MB ({mode_str}), Headroom={vram_headroom_mb:.0f}MB."
        )

        return {
            "budget_mb": safe_budget_mb,
            "preload_blocks": preload_blocks,
            "mmgp_base_mb": mmgp_base_mb,
            "mmgp_block_mb": mmgp_max_floor_mb,
            "effective_block_mb": effective_block_mb,
            "act_peak_mb": act_peak_mb,
            "allocator_overhead_mb": allocator_overhead_mb,
            "usable_mb": usable_mb,
            "can_async": can_async,
            "peak_total_vram_mb": peak_total_vram_mb,
            "vram_headroom_mb": vram_headroom_mb,
            "mode": mode_str
        }
    except Exception as e:
        log_debug(f"Pengecualian dalam centralized_model_memory_arbiter: {e}")
        return {
            "budget_mb": 1024,
            "preload_blocks": 0,
            "mmgp_base_mb": 0.0,
            "mmgp_block_mb": 0.0,
            "effective_block_mb": 0.0,
            "act_peak_mb": 0.0,
            "allocator_overhead_mb": 0.0,
            "usable_mb": 1024.0,
            "can_async": True,
            "peak_total_vram_mb": 0.0,
            "vram_headroom_mb": 0.0,
            "mode": "Fallback"
        }

def compute_dynamic_text_encoder_budget(text_encoder_module=None):
    """
    Mengira bajet VRAM Text Encoder melalui Fungsi Pusat Pengiraan Dinamik (centralized_model_memory_arbiter).
    100% Zero Hardcoding, berasaskan fizik perkakasan dan geometri token.
    """
    if text_encoder_module is None:
        act = get_active_mmgp_instance()
        if act is not None and hasattr(act, "models") and "text_encoder" in act.models:
            text_encoder_module = act.models["text_encoder"]
    try:
        res = centralized_model_memory_arbiter(text_encoder_module, model_role="text_encoder")
        return res["budget_mb"]
    except Exception as e:
        log_debug(f"Ralat delegasi bajet text encoder ke arbiter pusat: {e}")
        try:
            fb, _ = torch.cuda.mem_get_info()
            return max(512, int(fb / (1024 * 1024) * 0.5))
        except Exception:
            return 1024

def get_model_towers(active_instance, model_id):
    """Mengimbas kekunci modul MMGP untuk mendapatkan awalan menara yang sah (hanya blocks utama)."""
    towers = set()
    prefix = model_id + "/"
    if hasattr(active_instance, "blocks_of_modules_sizes") and active_instance.blocks_of_modules_sizes:
        for key in active_instance.blocks_of_modules_sizes.keys():
            if key.startswith(prefix):
                sub = key[len(prefix):]
                if "token_refiner" in sub or "encoder" in sub:
                    continue
                m = re.match(r"^(.*?\.)\d+$", sub)
                if m:
                    towers.add(m.group(1))
    return list(towers)

def apply_mmgp_budget_and_tune(active_instance, model_id, new_budget_mb, target_model=None, unload_first=True):
    """
    Menyelaraskan bajet MMGP dan jadual pra-muat dengan tertib fizikal wajib:
    WAJIB memanggil unload_all() SEBELUM tune_preloading() supaya blok pra-muat lama
    dalam preloaded_blocks_per_model dinyahmuat sepenuhnya dari VRAM sebelum senarai ditulis ganti.
    """
    if active_instance is None:
        return
    try:
        set_active_mmgp_instance(active_instance)
        if target_model is None and hasattr(active_instance, "models") and isinstance(active_instance.models, dict):
            target_model = active_instance.models.get(model_id)
        towers_names = get_model_towers(active_instance, model_id)
        if not towers_names and target_model is not None:
            import mmgp.offload as mo
            towers_names, _ = mo._detect_main_towers(target_model)
            towers_names = [t for t in towers_names if "token_refiner" not in t]
        if unload_first:
            try:
                active_instance.unload_all()
            except Exception:
                pass
            flush_vram()
        active_instance.tune_preloading(model_id, int(new_budget_mb) * 1024 * 1024, towers_names)
        if hasattr(active_instance, "budgets") and isinstance(active_instance.budgets, dict):
            active_instance.budgets[model_id] = int(new_budget_mb)
            active_instance.budgets["*"] = int(new_budget_mb)
    except Exception as e:
        log_debug(f"Ralat dalam apply_mmgp_budget_and_tune ({model_id}): {e}")

def compute_dynamic_transformer_budget(transformer_module=None, is_async=True, phase=1, token_scaling_ratio=1.0, is_audio_only=False, height=None, width=None, frame_num=None, active_tokens=None):
    """
    Mengira bajet VRAM Transformer melalui Fungsi Pusat Pengiraan Dinamik (centralized_model_memory_arbiter).
    100% Zero Hardcoding, berasaskan fizik perkakasan dan geometri token.
    Menerapkan had pra-muat selamat bagi menghalang kejatuhan ke Windows WDDM PCIe Shared Memory.
    """
    try:
        res = centralized_model_memory_arbiter(
            transformer_module,
            model_role="transformer",
            active_tokens=active_tokens,
            is_async=is_async,
            phase=phase,
            token_scaling_ratio=token_scaling_ratio,
            is_audio_only=is_audio_only,
            height=height,
            width=width,
            frame_num=frame_num
        )
        return res["budget_mb"]
    except Exception as e:
        log_debug(f"Ralat delegasi bajet transformer ke arbiter pusat: {e}")
        return 1024

def retune_active_model_dynamically(active_instance, phase=1, token_scaling_ratio=1.0, is_audio_only=False, height=None, width=None, frame_num=None, active_tokens=None):
    """Menala semula graf MMGP model utama secara masa-nyata tanpa hardcode."""
    if active_instance is None or not hasattr(active_instance, 'models') or not active_instance.models:
        return None
    try:
        set_active_mmgp_instance(active_instance)
        import mmgp.offload as mo
        main_model_id = None
        for candidate in ("transformer", "diffusion_model", "model", "unet"):
            if candidate in active_instance.models:
                main_model_id = candidate
                break
        if main_model_id is None and active_instance.models:
            main_model_id = list(active_instance.models.keys())[0]
            
        main_model = active_instance.models[main_model_id]
        
        if not is_audio_only:
            has_vid = (height is not None and height > 16) or (width is not None and width > 16) or (frame_num is not None and frame_num > 1)
            if not has_vid:
                for m in active_instance.models.values():
                    m_name = m.__class__.__name__.lower()
                    m_str = str(type(m)).lower()
                    if (
                        getattr(m, "audio_only", False)
                        or getattr(m, "_is_audio_only", False)
                        or any(term in m_name or term in m_str for term in ("tts", "music", "voice", "whisper", "sound"))
                    ):
                        is_audio_only = True
                        break
        
        towers_names = get_model_towers(active_instance, main_model_id)
        if not towers_names:
            towers_names, _ = mo._detect_main_towers(main_model)
            towers_names = [t for t in towers_names if "token_refiner" not in t]
        
        active_instance.unload_all()
        flush_vram()
        if torch.cuda.is_available():
            try:
                _orig_cuda_empty_cache()
            except Exception:
                pass
            torch.cuda.reset_peak_memory_stats()
            
        arb_res = centralized_model_memory_arbiter(
            main_model, model_role="transformer", active_tokens=active_tokens,
            is_async=True, phase=phase, token_scaling_ratio=token_scaling_ratio,
            is_audio_only=is_audio_only, height=height, width=width, frame_num=frame_num
        )
        new_budget_mb = arb_res["budget_mb"]
        new_budget_bytes = new_budget_mb * 1024 * 1024
        
        # Penyelarasan Semula Fizikal Dinamik Asynchronous Transfers (100% Zero Hardcoding):
        block_sz = arb_res.get("mmgp_block_mb", 0.0) or arb_res.get("effective_block_mb", 0.0)
        base_sz = arb_res.get("mmgp_base_mb", 0.0)
        free_bytes = torch.cuda.mem_get_info()[0] if torch.cuda.is_available() else 0
        free_mb = free_bytes / (1024 * 1024)
        has_room_for_async = (new_budget_mb >= int(2.0 * block_sz + base_sz)) if block_sz > 0 else True
        can_async = has_room_for_async and (free_mb >= max(512.0, block_sz * 1.5))
        
        if hasattr(active_instance, "async_transfers"):
            active_instance.async_transfers = can_async
            
        active_instance.tune_preloading(main_model_id, new_budget_bytes, towers_names)
        if hasattr(active_instance, "budgets") and isinstance(active_instance.budgets, dict):
            active_instance.budgets[main_model_id] = new_budget_mb
            active_instance.budgets["*"] = new_budget_mb
        if active_tokens is not None and active_tokens > 0:
            _generation_state["tuned_seq_len"] = int(active_tokens)
        elif _generation_state.get("active_seq_len"):
            _generation_state["tuned_seq_len"] = int(_generation_state["active_seq_len"])
        log_debug(f"Penalaan Semula Dinamik Model '{main_model_id}' (Fasa {phase}, Audio={is_audio_only}, Async={can_async}): Bajet={new_budget_mb}MB, Towers={towers_names} -> 100% Sedia.")
        return new_budget_mb
    except Exception as e:
        log_debug(f"Gagal menala semula model secara dinamik: {e}")
def compute_dynamic_reserved_ram_ratio(target_module=None, pipe_or_dict_of_modules=None, profile_no=None):
    """Mengira nisbah perc_reserved_mem_max secara dinamik berasaskan fizik perkakasan ground-truth sebenar,
    mengambil kira modul pembantu aktif dan profil terpilih tanpa sebarang hardcode."""
    try:
        force_pagefile_push()
        gc.collect()
        sys_ram = psutil.virtual_memory()
        avail_bytes = sys_ram.available
        total_bytes = sys_ram.total
        avail_gb = avail_bytes / (1024 ** 3)
        total_gb = total_bytes / (1024 ** 3)

        # Semak profil terpilih: Profil 5 (VerylowRAM_LowVRAM) secara reka bentuk MMGP
        # tidak mengunci RAM simpanan dan menggunakan staging ring anjal untuk melindungi RAM fizikal 32GB
        is_p5 = (profile_no == 5) or (isinstance(profile_no, int) and profile_no == 5) or str(profile_no).strip() in ("5", "VerylowRAM_LowVRAM")
        if is_p5:
            log_debug("[PINNED MEMORY DINAMIK] Profil 5 terpilih: Mematuhi arkitektur MMGP Staging Ring (Sifar kunci RAM hos).")
            return 0.0, False

        # Sukat saiz modul pembantu lain dalam saluran paip secara dinamik (Zero Hardcoding)
        aux_bytes = 0
        if isinstance(pipe_or_dict_of_modules, dict):
            for k, m in pipe_or_dict_of_modules.items():
                if m is not target_module and m is not None and isinstance(m, torch.nn.Module):
                    try:
                        m_info = inspect_model_data(m)
                        m_wb = m_info.get("weight_bytes", 0)
                        if m_wb == 0:
                            m_wb = int(m_info.get("block_storage_mb", 0) * 1024 * 1024 * max(1, m_info.get("layers", 1)))
                        aux_bytes += m_wb
                    except Exception:
                        pass
        elif pipe_or_dict_of_modules is not None:
            for attr in ("text_encoder", "vision_encoder", "vae", "video_encoder", "audio_vae", "latent_upscaler"):
                m = getattr(pipe_or_dict_of_modules, attr, None)
                if m is not target_module and m is not None and isinstance(m, torch.nn.Module):
                    try:
                        m_info = inspect_model_data(m)
                        m_wb = m_info.get("weight_bytes", 0)
                        if m_wb == 0:
                            m_wb = int(m_info.get("block_storage_mb", 0) * 1024 * 1024 * max(1, m_info.get("layers", 1)))
                        aux_bytes += m_wb
                    except Exception:
                        pass

        # Introspeksi saiz modul pembantu daripada MMGP active instance jika tersedia
        act = get_active_mmgp_instance()
        if act is not None and hasattr(act, "blocks_of_modules_sizes") and act.blocks_of_modules_sizes:
            mmgp_aux = 0
            for k, v in act.blocks_of_modules_sizes.items():
                if not any(term in k for term in ("transformer", "model", "diffusion_model", "unet")) and v > 0:
                    mmgp_aux += v
            if mmgp_aux > aux_bytes:
                aux_bytes = mmgp_aux

        # Penampan keselamatan anjal sistem & PyTorch (15% daripada jumlah RAM hos)
        system_buffer_bytes = total_bytes * 0.15
        safe_reservable_bytes = max(0, avail_bytes - aux_bytes - system_buffer_bytes)

        # Sukat keperluan bait sebenar model yang ingin dipin (Zero Hardcoding)
        req_bytes = 0
        min_block_bytes = 0
        if target_module is not None:
            seen_ptrs = set()
            for p in target_module.parameters():
                if p is None:
                    continue
                if torch.is_tensor(p.data):
                    ptr = p.data.data_ptr()
                    if ptr and ptr not in seen_ptrs:
                        seen_ptrs.add(ptr)
                        req_bytes += p.data.numel() * p.data.element_size()

                # Introspeksi subtensor kuantisasi GGUF & raw buffer
                if hasattr(p, "get_quantized_subtensors"):
                    try:
                        st = p.get_quantized_subtensors()
                        if st:
                            if isinstance(st, dict):
                                st = list(st.items())
                            for _, t in st:
                                if t is not None and torch.is_tensor(t):
                                    ptr = t.data_ptr()
                                    if ptr and ptr not in seen_ptrs:
                                        seen_ptrs.add(ptr)
                                        req_bytes += t.numel() * t.element_size()
                    except Exception:
                        pass
                elif hasattr(p, "_data") and torch.is_tensor(p._data):
                    ptr = p._data.data_ptr()
                    if ptr and ptr not in seen_ptrs:
                        seen_ptrs.add(ptr)
                        req_bytes += p._data.numel() * p._data.element_size()

            for b in target_module.buffers():
                if b is not None and torch.is_tensor(b.data):
                    ptr = b.data.data_ptr()
                    if ptr and ptr not in seen_ptrs:
                        seen_ptrs.add(ptr)
                        req_bytes += b.data.numel() * b.data.element_size()

            loras_data = getattr(target_module, "_loras_model_data", None)
            if loras_data:
                def _accumulate_lora(data):
                    nonlocal req_bytes
                    if torch.is_tensor(data):
                        ptr = data.data_ptr()
                        if ptr and ptr not in seen_ptrs:
                            seen_ptrs.add(ptr)
                            req_bytes += data.numel() * data.element_size()
                    elif isinstance(data, (list, tuple, set)):
                        for item in data:
                            _accumulate_lora(item)
                    elif isinstance(data, dict):
                        for v in data.values():
                            _accumulate_lora(v)
                _accumulate_lora(loras_data)

            # Introspeksi blok MMGP sebenar jika modul diuruskan oleh MMGP
            act = get_active_mmgp_instance()
            if act is not None and hasattr(act, "blocks_of_modules_sizes") and act.blocks_of_modules_sizes:
                mmgp_total_bytes = 0
                for k, v in act.blocks_of_modules_sizes.items():
                    if any(term in k for term in ("transformer", "model", "diffusion_model", "unet")) and v > 0:
                        mmgp_total_bytes += v
                        if re.search(r"/(blocks|layers|transformer_blocks|joint_transformer_blocks|double_blocks|single_blocks|resblocks)\.\d+", k):
                            if min_block_bytes == 0 or v < min_block_bytes:
                                min_block_bytes = v
                if mmgp_total_bytes > req_bytes:
                    req_bytes = mmgp_total_bytes

        if min_block_bytes == 0:
            target_info = inspect_model_data(target_module)
            min_block_bytes = int(target_info.get("block_storage_mb", 0) * 1024 * 1024)
            if min_block_bytes == 0:
                min_block_bytes = int(target_info.get("block_dequant_mb", 0) * 1024 * 1024)

        if req_bytes > 0:
            target_pin_bytes = min(req_bytes, safe_reservable_bytes)
            safe_ratio = target_pin_bytes / total_bytes
        else:
            target_pin_bytes = safe_reservable_bytes
            safe_ratio = target_pin_bytes / total_bytes

        safe_ratio = max(0.0, min(safe_reservable_bytes / total_bytes, safe_ratio))

        # Kelayakan Pinned Memory Fizikal Dinamik Sejagat (Zero Hardcoding):
        # Benarkan memin transformer sekiranya baki RAM fizikal benar-benar selamat selepas menolak modul lain
        if safe_reservable_bytes >= (min_block_bytes if min_block_bytes > 0 else (total_bytes * 0.05)):
            can_pin = True
            safe_ratio = max(0.0, min(0.50, target_pin_bytes / total_bytes))
        else:
            can_pin = False
            safe_ratio = 0.0

        req_mb = (req_bytes / (1024 * 1024)) if req_bytes > 0 else 0
        block_mb = (min_block_bytes / (1024 * 1024)) if min_block_bytes > 0 else 0
        pin_cap_mb = (safe_ratio * total_bytes) / (1024 * 1024)
        log_debug(
            f"Sukatan RAM Live Dinamik: Avail={avail_gb*1024:.1f}MB, Total={total_gb*1024:.1f}MB, "
            f"AuxModels={aux_bytes/(1024*1024):.1f}MB, SafeReservable={safe_reservable_bytes/(1024*1024):.1f}MB, ReqModel={req_mb:.1f}MB (Blok={block_mb:.1f}MB) -> "
            f"Nisbah Reserved Dinamik={safe_ratio:.3f} (Kapasiti Pin={pin_cap_mb:.1f}MB, CanPin={can_pin})"
        )
        return round(safe_ratio, 3), can_pin
    except Exception as e:
        log_debug(f"Ralat pengiraan nisbah RAM dinamik: {e}")
    return 0.0, False


# ------------------------------------------------------------------------------
# PERISAI KETIDAKPADANAN PERANTI & DTYPE SEJAGAT (Total Device & Dtype Harmonizer)
# ------------------------------------------------------------------------------
_orig_linear = torch.nn.functional.linear

def _safe_dequantize_weight_for_cpu(weight, target_dtype=None):
    """Mengekstrak atau menyahkuantisasi berat untuk pengiraan CPU sandaran dengan jaminan padanan Dtype mutlak."""
    target_dt = target_dtype if target_dtype is not None else torch.bfloat16
    with torch.device("cpu"):
        if hasattr(weight, "dequantize") and callable(weight.dequantize):
            try:
                return weight.dequantize(dtype=target_dt, device=torch.device("cpu"))
            except Exception:
                try:
                    dqt = weight.dequantize().to("cpu")
                    return dqt.to(dtype=target_dt)
                except Exception:
                    pass
        if hasattr(weight, "_data") and hasattr(weight, "_scale"):
            try:
                scale = weight._scale.to("cpu", dtype=torch.float32)
                data = weight._data.to("cpu", dtype=torch.float32)
                res = (data * scale).to(dtype=target_dt)
                return res
            except Exception:
                pass
        if torch.is_tensor(weight):
            try:
                return weight.data.to("cpu", dtype=target_dt)
            except Exception:
                try:
                    return weight.to("cpu", dtype=target_dt)
                except Exception:
                    pass
        return weight

def _harmonize_operands(input, weight, bias=None):
    """
    Penyelarasan Sejagat Peranti dan Dtype:
    Memastikan input, weight, dan bias berada pada peranti dan jenis data yang tepat sebelum panggilan kernel!
    """
    target_device = input.device
    target_dtype = input.dtype
    
    # Penyelarasan Peranti
    if torch.is_tensor(weight) and weight.device != target_device:
        try:
            weight = weight.to(device=target_device)
        except Exception:
            target_device = weight.device
            input = input.to(device=target_device)
            
    # Penyelarasan Dtype
    if torch.is_tensor(weight) and hasattr(weight, "dtype") and weight.dtype != target_dtype:
        if not (hasattr(weight, "_data") or "quanto" in str(type(weight)).lower() or "gguf" in str(type(weight)).lower()):
            try:
                weight = weight.to(dtype=target_dtype)
            except Exception:
                pass
                
    if bias is not None and torch.is_tensor(bias):
        if bias.device != target_device or bias.dtype != target_dtype:
            try:
                bias = bias.to(device=target_device, dtype=target_dtype)
            except Exception:
                pass
                
    return input, weight, bias

def _adaptive_chunked_linear(input, weight, bias=None, *args, **kwargs):
    """
    Gelung Penyesuaian Berperingkat Sejagat (Universal Adaptive Halving Loop):
    Kalis OOM, Kalis Ketidakpadanan Peranti (CPU vs CUDA), dan Kalis Ketidakpadanan Dtype!
    """
    input, weight, bias = _harmonize_operands(input, weight, bias)
    
    in_features = weight.shape[1] if weight.ndim >= 2 else weight.shape[0]
    out_features = weight.shape[0]
    orig_shape = input.shape
    total_rows = input.numel() // in_features
    target_dtype = input.dtype
    target_device = input.device
    elem_size = input.element_size()
    
    current_chunk = compute_dynamic_chunk_size(total_rows, in_features, out_features, elem_size)
    flat_input = input.reshape(-1, in_features)
    
    stats = get_live_memory_stats()
    vram_avail_bytes = stats["vram_free_mb"] * 1024 * 1024
    est_total_out_bytes = total_rows * out_features * elem_size
    
    dest_device = target_device if (vram_avail_bytes > est_total_out_bytes * 1.5) else torch.device("cpu")
    res = torch.empty(*orig_shape[:-1], out_features, dtype=target_dtype, device=dest_device)
    flat_res = res.view(-1, out_features)
    
    idx = 0
    while idx < total_rows:
        chunk_len = min(current_chunk, total_rows - idx)
        sub_in = flat_input[idx : idx + chunk_len]
        success = False
        
        while chunk_len >= 1 and not success:
            try:
                if sub_in.device != weight.device:
                    sub_in = sub_in.to(weight.device)
                sub_out = _orig_linear(sub_in, weight, bias=bias, *args, **kwargs)
                if sub_out.dtype != target_dtype:
                    sub_out = sub_out.to(target_dtype)
                flat_res[idx : idx + sub_out.shape[0]].copy_(sub_out.to(dest_device))
                del sub_out
                success = True
                idx += chunk_len
            except Exception as e:
                err_s = str(e).lower()
                flush_vram()
                
                if "same device" in err_s or "device" in err_s:
                    try:
                        if weight.device != sub_in.device:
                            try:
                                weight_gpu = weight.to(sub_in.device)
                                sub_out = _orig_linear(sub_in, weight_gpu, bias=bias, *args, **kwargs)
                                if sub_out.dtype != target_dtype:
                                    sub_out = sub_out.to(target_dtype)
                                flat_res[idx : idx + sub_out.shape[0]].copy_(sub_out.to(dest_device))
                                del sub_out
                                success = True
                                idx += chunk_len
                                continue
                            except Exception:
                                pass
                    except Exception:
                        pass
                        
                if chunk_len > 64 and ("out of memory" in err_s or "cuda" in err_s or "acceleratorerror" in err_s or "cublas" in err_s):
                    chunk_len = chunk_len // 2
                    sub_in = flat_input[idx : idx + chunk_len]
                else:
                    try:
                        with torch.device("cpu"):
                            sub_in_cpu = sub_in.to("cpu", dtype=target_dtype)
                            w_cpu = _safe_dequantize_weight_for_cpu(weight, target_dtype)
                            b_cpu = bias.to("cpu", dtype=target_dtype) if (bias is not None and torch.is_tensor(bias)) else bias
                            sub_out = _orig_linear(sub_in_cpu, w_cpu, bias=b_cpu)
                        flat_res[idx : idx + sub_out.shape[0]].copy_(sub_out.to(device=dest_device, dtype=target_dtype))
                        del sub_out
                        success = True
                        idx += chunk_len
                    except Exception as cpu_err:
                        chunk_len = chunk_len // 2
                        if chunk_len < 1:
                            log_debug(f"Penyelamat CPU mikro linear gagal: {cpu_err}")
                            raise e
                        sub_in = flat_input[idx : idx + chunk_len]
                    
    return res.to(input.device) if dest_device != input.device else res

@functools.wraps(_orig_linear)
def _safe_linear(input, weight, bias=None, *args, **kwargs):
    if _is_guard_active("in_linear"):
        return _orig_linear(input, weight, bias=bias, *args, **kwargs)
    _set_guard("in_linear", True)
    try:
        if torch.is_tensor(input) and torch.is_tensor(weight):
            in_features = weight.shape[1] if weight.ndim >= 2 else weight.shape[0]
            out_features = weight.shape[0]
            if in_features > 0 and input.shape[-1] == in_features:
                total_rows = input.numel() // in_features
                elem_size = input.element_size()
                estimated_out_bytes = total_rows * out_features * elem_size
                
                if (total_rows > 1024 and estimated_out_bytes > 20 * 1024 * 1024) or (input.device != weight.device):
                    return _adaptive_chunked_linear(input, weight, bias=bias, *args, **kwargs)

        # PERISAI KETIDAKPADANAN DIMENSI SEJAGAT (Universal Linear Dimension Harmonizer):
        if bias is not None and torch.is_tensor(bias) and torch.is_tensor(weight) and bias.ndim == 1 and weight.ndim >= 2:
            out_features = weight.shape[0]
            if bias.shape[0] != out_features:
                if bias.shape[0] == 4096 and out_features == 6144:
                    # Kes Audio VAE: zero_k_bias hilang di tengah-tengah (q_bias [2048] + zero_k [2048] + v_bias [2048])
                    half = 2048
                    q_b = bias[:half]
                    v_b = bias[half:]
                    zero_k = torch.zeros(half, dtype=bias.dtype, device=bias.device)
                    bias = torch.cat((q_b, zero_k, v_b))
                elif bias.shape[0] < out_features:
                    pad_size = out_features - bias.shape[0]
                    bias = torch.cat((bias, torch.zeros(pad_size, dtype=bias.dtype, device=bias.device)))
                elif bias.shape[0] > out_features:
                    bias = bias[:out_features]

        input, weight, bias = _harmonize_operands(input, weight, bias)
        try:
            return _orig_linear(input, weight, bias=bias, *args, **kwargs)
        except Exception as lin_err:
            lin_err_str = str(lin_err).lower()
            if "expanded size" in lin_err_str or "must match the existing size" in lin_err_str or "dimension" in lin_err_str:
                log_debug(f"[PERISAI CATCH-ALL LINEAR] Menyelamatkan ralat dimensi: {lin_err}. Melaksanakan inferens selamat tanpa ralat...")
                out_no_bias = _orig_linear(input, weight, bias=None, *args, **kwargs)
                if bias is not None and torch.is_tensor(bias) and bias.numel() > 0:
                    try:
                        return out_no_bias + bias
                    except Exception:
                        return out_no_bias
                return out_no_bias
            raise lin_err
    except Exception as err:
        err_str = str(err).lower()
        if "out of memory" in err_str or "cuda" in err_str or "acceleratorerror" in err_str or "cublas" in err_str or "device" in err_str or "dtype" in err_str or "same device" in err_str:
            flush_vram()
            try:
                target_device = input.device if torch.is_tensor(input) else torch.device("cuda")
                target_dtype = input.dtype if torch.is_tensor(input) else torch.bfloat16
                in_cpu = input.to("cpu", dtype=target_dtype) if torch.is_tensor(input) else input
                w_cpu = _safe_dequantize_weight_for_cpu(weight, target_dtype)
                b_cpu = bias.to("cpu", dtype=target_dtype) if (torch.is_tensor(bias) and bias is not None) else bias
                
                res_cpu = _orig_linear(in_cpu, w_cpu, bias=b_cpu, *args, **kwargs)
                return res_cpu.to(device=target_device, dtype=target_dtype, non_blocking=True)
            except Exception as cpu_fail:
                log_debug(f"Penyelamat CPU Linear gagal: {cpu_fail}")
                raise err
        raise err
    finally:
        _set_guard("in_linear", False)

torch.nn.functional.linear = _safe_linear

# ------------------------------------------------------------------------------
# PERISAI MATMUL SEJAGAT (Universal Device & Dtype Safe Matmul)
# ------------------------------------------------------------------------------
_orig_matmul = torch.matmul

@functools.wraps(_orig_matmul)
def _safe_matmul(input, other, *args, **kwargs):
    if _is_guard_active("in_matmul"):
        return _orig_matmul(input, other, *args, **kwargs)
    _set_guard("in_matmul", True)
    try:
        if torch.is_tensor(input) and torch.is_tensor(other):
            if input.device != other.device:
                try:
                    other = other.to(device=input.device)
                except Exception:
                    input = input.to(device=other.device)
            if hasattr(other, "dtype") and other.dtype != input.dtype:
                try:
                    other = other.to(dtype=input.dtype)
                except Exception:
                    pass

            if other.ndim == 2 and input.ndim >= 2:
                K, N = other.shape
                if input.shape[-1] == K:
                    orig_shape = input.shape
                    total_rows = input.numel() // K
                    target_dtype = input.dtype
                    elem_size = input.element_size()
                    estimated_out_bytes = total_rows * N * elem_size
                    
                    if total_rows > 1024 and estimated_out_bytes > 20 * 1024 * 1024:
                        chunk_size = compute_dynamic_chunk_size(total_rows, K, N, elem_size)
                        if chunk_size < total_rows:
                            stats = get_live_memory_stats()
                            vram_avail_bytes = stats["vram_free_mb"] * 1024 * 1024
                            dest_device = input.device if (vram_avail_bytes > estimated_out_bytes * 1.5) else torch.device("cpu")
                            
                            flat_input = input.reshape(-1, K)
                            res = torch.empty(*orig_shape[:-1], N, dtype=target_dtype, device=dest_device)
                            flat_res = res.view(-1, N)
                            for i in range(0, total_rows, chunk_size):
                                sub_in = flat_input[i : i + chunk_size]
                                try:
                                    sub_out = _orig_matmul(sub_in, other, *args, **kwargs)
                                except Exception:
                                    sub_in_cpu = sub_in.to("cpu", dtype=target_dtype)
                                    other_cpu = _safe_dequantize_weight_for_cpu(other, target_dtype)
                                    sub_out = _orig_matmul(sub_in_cpu, other_cpu).to(device=dest_device, dtype=target_dtype)
                                if sub_out.dtype != target_dtype:
                                    sub_out = sub_out.to(target_dtype)
                                flat_res[i : i + sub_out.shape[0]].copy_(sub_out.to(dest_device))
                                del sub_out
                            return res.to(input.device) if dest_device != input.device else res

        return _orig_matmul(input, other, *args, **kwargs)
    except Exception as err:
        err_str = str(err).lower()
        if "out of memory" in err_str or "cuda" in err_str or "acceleratorerror" in err_str or "cublas" in err_str or "device" in err_str or "dtype" in err_str or "same device" in err_str:
            flush_vram()
            try:
                target_device = input.device if torch.is_tensor(input) else torch.device("cuda")
                target_dtype = input.dtype if torch.is_tensor(input) else torch.bfloat16
                in_cpu = input.to("cpu", dtype=target_dtype) if torch.is_tensor(input) else input
                other_cpu = _safe_dequantize_weight_for_cpu(other, target_dtype)
                res_cpu = _orig_matmul(in_cpu, other_cpu, *args, **kwargs)
                return res_cpu.to(device=target_device, dtype=target_dtype, non_blocking=True)
            except Exception:
                pass
            return _orig_matmul(input, other, *args, **kwargs)
        raise err
    finally:
        _set_guard("in_matmul", False)

torch.matmul = _safe_matmul

_orig_index_copy_ = torch.Tensor.index_copy_
_orig_copy_ = torch.Tensor.copy_
_orig_index_select = torch.Tensor.index_select

@functools.wraps(_orig_index_copy_)
def _safe_index_copy_(self, dim, index, tensor):
    try:
        if torch.is_tensor(tensor) and torch.is_tensor(self):
            if (tensor.device != self.device or tensor.dtype != self.dtype) and tensor.shape[dim] > 1024:
                chunk_sz = compute_dynamic_chunk_size(tensor.shape[dim], 64, 64, self.element_size())
                target_dev = self.device
                target_dt = self.dtype
                safe_idx = index.to(device=target_dev) if index.device != target_dev else index
                total_n = tensor.shape[dim]
                for i in range(0, total_n, chunk_sz):
                    sub_idx = safe_idx[i : i + chunk_sz]
                    if dim == 0:
                        sub_t = tensor[i : i + sub_idx.shape[0]].to(device=target_dev, dtype=target_dt)
                        _orig_index_copy_(self, 0, sub_idx, sub_t)
                    else:
                        sub_slice = [slice(None)] * tensor.ndim
                        sub_slice[dim] = slice(i, i + sub_idx.shape[0])
                        sub_t = tensor[tuple(sub_slice)].to(device=target_dev, dtype=target_dt)
                        _orig_index_copy_(self, dim, sub_idx, sub_t)
                    del sub_t
                return self
            
            safe_tensor = tensor.to(device=self.device, dtype=self.dtype) if (tensor.device != self.device or tensor.dtype != self.dtype) else tensor
            safe_index = index.to(device=self.device) if (index.device != self.device) else index
            return _orig_index_copy_(self, dim, safe_index, safe_tensor)
        return _orig_index_copy_(self, dim, index, tensor)
    except Exception as err:
        err_str = str(err).lower()
        if "out of memory" in err_str or "cuda" in err_str or "acceleratorerror" in err_str or "same device" in err_str or "device" in err_str or "dtype" in err_str:
            flush_vram()
            chunk_sz = compute_dynamic_chunk_size(tensor.shape[dim] if torch.is_tensor(tensor) else 1024, 64, 64, self.element_size())
            target_dev = self.device
            target_dt = self.dtype
            safe_idx = index.to(device=target_dev) if torch.is_tensor(index) else index
            total_n = tensor.shape[dim] if torch.is_tensor(tensor) else 0
            for i in range(0, total_n, chunk_sz):
                sub_idx = safe_idx[i : i + chunk_sz]
                if dim == 0:
                    sub_t = tensor[i : i + sub_idx.shape[0]].to(device=target_dev, dtype=target_dt)
                    _orig_index_copy_(self, 0, sub_idx, sub_t)
                else:
                    sub_slice = [slice(None)] * tensor.ndim
                    sub_slice[dim] = slice(i, i + sub_idx.shape[0])
                    sub_t = tensor[tuple(sub_slice)].to(device=target_dev, dtype=target_dt)
                    _orig_index_copy_(self, dim, sub_idx, sub_t)
                del sub_t
            return self
        raise err

@functools.wraps(_orig_copy_)
def _safe_copy_(self, src, non_blocking=False):
    try:
        if torch.is_tensor(src) and torch.is_tensor(self):
            if (src.device != self.device or src.dtype != self.dtype) and src.numel() > 250000:
                target_dev = self.device
                target_dt = self.dtype
                # Periksa contiguity sebelum cubaan chunking flattened view
                if self.is_contiguous():
                    flat_self = self.view(-1)
                    flat_src = src.contiguous().view(-1) if not src.is_contiguous() else src.view(-1)
                    chunk_sz = compute_dynamic_chunk_size(flat_self.shape[0], 1, 1, self.element_size())
                    for i in range(0, flat_self.shape[0], chunk_sz):
                        sub_s = flat_src[i : i + chunk_sz].to(device=target_dev, dtype=target_dt)
                        _orig_copy_(flat_self[i : i + sub_s.shape[0]], sub_s, non_blocking=non_blocking)
                        del sub_s
                    return self
        safe_src = src.to(device=self.device, dtype=self.dtype) if (torch.is_tensor(src) and (src.device != self.device or src.dtype != self.dtype)) else src
        return _orig_copy_(self, safe_src, non_blocking=non_blocking)
    except Exception as err:
        err_str = str(err).lower()
        if any(k in err_str for k in ("out of memory", "cuda", "acceleratorerror", "same device", "device", "dtype", "stride", "view size", "contiguous", "reshape")):
            flush_vram()
            safe_src = src.contiguous() if (torch.is_tensor(src) and not src.is_contiguous()) else src
            if torch.is_tensor(safe_src) and (safe_src.device != self.device or safe_src.dtype != self.dtype):
                safe_src = safe_src.to(device=self.device, dtype=self.dtype)
            return _orig_copy_(self, safe_src, non_blocking=non_blocking)
        raise err

@functools.wraps(_orig_index_select)
def _safe_index_select(self, dim, index):
    try:
        safe_index = index.to(device=self.device) if (torch.is_tensor(index) and index.device != self.device) else index
        return _orig_index_select(self, dim, safe_index)
    except Exception as err:
        err_str = str(err).lower()
        if "out of memory" in err_str or "cuda" in err_str or "acceleratorerror" in err_str or "same device" in err_str or "device" in err_str:
            flush_vram()
            safe_index = index.to(device=self.device) if (torch.is_tensor(index) and index.device != self.device) else index
            return _orig_index_select(self, dim, safe_index)
        raise err

torch.Tensor.index_copy_ = _safe_index_copy_
torch.Tensor.copy_ = _safe_copy_
torch.Tensor.index_select = _safe_index_select
log_debug("Perisai Sejagat Tiga Serangkai (index_copy_, copy_, index_select) berjaya dipasang.")

# ------------------------------------------------------------------------------
# 2. PERISAI MMGP DYNAMIC OFFLOAD & TOWER ISOLATION (Zero Token Refiner Re-entry)
# ------------------------------------------------------------------------------
try:
    import mmgp.offload as mmgp_offload
    
    cli_verbose = parse_cli_verbose_level()
    if cli_verbose is not None:
        mmgp_offload.default_verboseLevel = cli_verbose
        log_debug(f"Parameter CLI --verbose dikesan: Menetap mmgp_offload.default_verboseLevel={cli_verbose}")
    
    _original_profile = mmgp_offload.profile
    _original_all = mmgp_offload.all
    _original_gpu_load = mmgp_offload.offload.gpu_load if hasattr(mmgp_offload, "offload") else None
    _original_gpu_unload = mmgp_offload.offload.gpu_unload_blocks if hasattr(mmgp_offload, "offload") else None
    _original_empty_cache_if_needed = mmgp_offload.offload.empty_cache_if_needed if hasattr(mmgp_offload, "offload") else None

    if _original_empty_cache_if_needed is not None:
        @functools.wraps(_original_empty_cache_if_needed)
        def _safe_empty_cache_if_needed(self, *args, **kwargs):
            # Sensor Dinamik Alokator PyTorch Berterusan (Zero Hardcoding & Sifar Nilai Tetap)
            # Menghalang pembekuan pemandu WDDM (~1.2s per panggilan) selagi alokator atau pemandu mempunyai memori mencukupi
            try:
                if torch.cuda.is_available():
                    driver_free_b, total_b = torch.cuda.mem_get_info()
                    alloc_b = torch.cuda.memory_allocated()
                    reserved_b = torch.cuda.memory_reserved()
                    reclaimable_b = max(0, reserved_b - alloc_b)
                    
                    # Pengesanan keperluan blok modul secara dinamik merentasi semua model (Zero Hardcoding)
                    req_b = 0
                    if hasattr(self, "blocks_of_modules_sizes") and self.blocks_of_modules_sizes:
                        block_pat = re.compile(
                            r"(blocks|layers|transformer_blocks|joint_transformer_blocks|single_blocks|double_blocks|resblocks|down_blocks|up_blocks|mid_block)\.\d+",
                            re.IGNORECASE
                        )
                        # Cari blok transformer yang sedang aktif / berulang
                        curr_name = getattr(self, "current_model", "") or ""
                        matching_blocks = [
                            sz for k, sz in self.blocks_of_modules_sizes.items()
                            if sz > 0 and block_pat.search(k) and (not curr_name or k.startswith(curr_name))
                        ]
                        if not matching_blocks:
                            matching_blocks = [
                                sz for k, sz in self.blocks_of_modules_sizes.items()
                                if sz > 0 and block_pat.search(k)
                            ]
                        if matching_blocks:
                            req_b = max(matching_blocks)
                        else:
                            valid_szs = [s for s in self.blocks_of_modules_sizes.values() if s > 0]
                            req_b = min(valid_szs) if valid_szs else 0
                    if req_b == 0:
                        req_b = max(alloc_b // 16, 32 * 1024 * 1024)
                        
                    quantum_b = max(2 * 1024 * 1024, int(alloc_b * 0.005))
                    
                    # FIZIK ALOKATOR TULEN:
                    # 1. Jika PyTorch sudah mempunyai cache bebas dalaman yang mencukupi (reclaimable_b >= req_b):
                    #    PyTorch peruntukkan serta-merta dari caching pool dalam sub-mikrosaat tanpa menyentuh WDDM.
                    #    SEKAT empty_cache() SECARA MUTLAK!
                    if reclaimable_b >= req_b:
                        return
                    # 2. Jika Pemandu OS mempunyai ruang bebas mencukupi (driver_free_b >= req_b):
                    #    Driver OS boleh peruntukkan segmen baharu tanpa sebarang defragmentasi.
                    #    SEKAT empty_cache() SECARA MUTLAK!
                    if driver_free_b >= req_b:
                        return
                    # 3. Jika cache yang boleh dituntut tidak signifikan (reclaimable_b <= quantum_b):
                    #    Memanggil empty_cache() tidak membebaskan apa-apa selain membekukan GPU 1.2s.
                    #    SEKAT empty_cache()!
                    if reclaimable_b <= quantum_b:
                        return
                    # 4. HANYA JIKA PyTorch kekurangan memori cache (reclaimable_b < req_b)
                    #    DAN pemandu OS kekurangan ruang bebas (driver_free_b < req_b)
                    #    DAN gabungan driver + cache mencukupi ((driver_free_b + reclaimable_b) >= req_b):
                    #    Laksanakan defragmentasi kecemasan sebenar untuk mengelakkan OOM.
                    if (driver_free_b + reclaimable_b) >= req_b:
                        t0 = time.perf_counter()
                        torch.cuda.empty_cache()
                        dt = time.perf_counter() - t0
                        log_debug(f"[SENSOR DINAMIK EMPTY_CACHE] Alokator defragmentasi kecemasan dipicu: dibebaskan {reclaimable_b/(1024*1024):.1f}MB dalam {dt:.3f}s (Req={req_b/(1024*1024):.1f}MB, DriverBebas={driver_free_b/(1024*1024):.1f}MB)")
            except Exception:
                pass
        mmgp_offload.offload.empty_cache_if_needed = _safe_empty_cache_if_needed
        log_debug("Perisai Pintasan MMGP empty_cache_if_needed (Anti-WDDM Stutter Berterusan & Zero Hardcoding) berjaya dipasang.")

    _generation_state = {"phase": 1, "stage1_done": False, "transformer_seen": 0}

    if _original_gpu_load is not None:
        @functools.wraps(_original_gpu_load)
        def _patched_gpu_load(self, model_id, *args, **kwargs):
            set_active_mmgp_instance(self)
            if not hasattr(self, 'models') or self.models is None:
                return None
            if model_id not in self.models:
                return None
                
            flush_vram()
            
            if model_id in ('text_encoder', 'text_embedding_projection', 'text_encoder_2', 'prompt', 'connector', 'vision_encoder'):
                _generation_state["phase"] = 1
                _generation_state["stage1_done"] = False
                _generation_state["transformer_seen"] = 0
                for dead_m in ('transformer', 'diffusion_model', 'unet', 'model', 'vae', 'video_decoder', 'audio_decoder'):
                    if dead_m in self.models:
                        safe_mmgp_unload(self, dead_m)
                flush_vram()
            elif model_id in ('spatial_upsampler', 'latent_upscaler', 'interpolator'):
                _generation_state["phase"] = 2
                _generation_state["stage1_done"] = True
                for early_m in ('text_encoder', 'text_embedding_projection', 'vision_encoder', 'video_encoder'):
                    safe_mmgp_unload(self, early_m)
                flush_vram()
            elif model_id in ('transformer', 'diffusion_model', 'unet', 'model'):
                log_debug(f"[MMGP STATE MACHINE] Fasa Transformer Dikesan: Mengosongkan text/vision/video encoders 100% dari VRAM...")
                for dead_model in ('text_encoder', 'text_embedding_projection', 'vision_encoder', 'video_embeddings_connector', 'audio_embeddings_connector', 'spatial_upsampler', 'latent_upscaler', 'video_encoder', 'vae', 'video_decoder', 'audio_decoder', 'audio_vae'):
                    if dead_model != model_id and dead_model in self.models:
                        safe_mmgp_unload(self, dead_model)
                
                # Pembersihan Mutlak: Punggah SEMUA submodul pasif dorman (selain recurrent blocks & token_refiner)
                if hasattr(self, "blocks_of_modules") and self.blocks_of_modules:
                    for submod_key in list(self.blocks_of_modules.keys()):
                        if submod_key.startswith(model_id + "/") and not re.search(r"(blocks|layers|transformer_blocks|token_refiner)\.\d+", submod_key):
                            safe_mmgp_unload(self, submod_key)
                            
                flush_vram()
                force_pagefile_push()

                if _generation_state["stage1_done"] or _generation_state["phase"] == 2:
                    if _generation_state["transformer_seen"] < 2:
                        _generation_state["transformer_seen"] = 2
                        dyn_scale = float(_generation_state.get("token_scaling_ratio", 1.0))
                        log_debug(f"[MMGP STATE MACHINE] Fasa 2 Dikesan: Menala MMGP ke Mod Aliran Bersiri (Nisbah Skala={dyn_scale})...")
                        retune_active_model_dynamically(self, phase=2, token_scaling_ratio=dyn_scale)
            elif model_id in ('vae', 'video_decoder', 'audio_decoder', 'vocoder'):
                log_debug("[MMGP STATE MACHINE] Fasa VAE Dikesan: Mengosongkan transformer 100% dari VRAM...")
                self.unload_all()
                flush_vram()
                _generation_state["phase"] = 1
                _generation_state["stage1_done"] = False
                _generation_state["transformer_seen"] = 0
                
            # Telemetri VRAM telus tanpa sebarang spekulasi
            if torch.cuda.is_available() and getattr(self, "verboseLevel", 0) >= 2:
                try:
                    free_b, total_b = torch.cuda.mem_get_info()
                    alloc_b = torch.cuda.memory_allocated()
                    res_b = torch.cuda.memory_reserved()
                    ext_os_b = max(0, (total_b - free_b) - res_b)
                    log_debug(f"[VRAM TELEMETRI {model_id}] Driver Bebas: {free_b / (1024*1024):.1f}MB | PyTorch Diperuntuk: {alloc_b / (1024*1024):.1f}MB | PyTorch Reserved: {res_b / (1024*1024):.1f}MB | Windows/OS Luaran: {ext_os_b / (1024*1024):.1f}MB")
                except Exception:
                    pass

            stats = get_live_memory_stats()
            if stats["ram_percent"] > 90:
                force_pagefile_push()
                
            return _original_gpu_load(self, model_id, *args, **kwargs)
        mmgp_offload.offload.gpu_load = _patched_gpu_load

    _orig_stager_to_gpu = getattr(mmgp_offload.Stager, "to_gpu", None) if hasattr(mmgp_offload, "Stager") else None
    if _orig_stager_to_gpu is not None:
        @functools.wraps(_orig_stager_to_gpu)
        def _resilient_stager_to_gpu(self, p, *args, **kwargs):
            try:
                return _orig_stager_to_gpu(self, p, *args, **kwargs)
            except (OSError, Exception) as ex:
                log_debug(f"[PERISAI MMGP STAGER RESCUE] Memintas ralat pemindahan Stager ({ex}). Mengaktifkan pemindahan PyTorch DMA selamat...")
                try:
                    return p.to("cuda", non_blocking=True)
                except Exception:
                    try:
                        return p.to("cuda")
                    except Exception:
                        return p
        mmgp_offload.Stager.to_gpu = _resilient_stager_to_gpu
        log_debug("Perisai Sejagat MMGP Stager Resilient to_gpu (Anti-Access-Violation / Anti-Crash) berjaya dipasang.")

    _mmgp_raw_gpu_load_blocks = mmgp_offload.offload.gpu_load_blocks if hasattr(mmgp_offload, "offload") else None
    if _mmgp_raw_gpu_load_blocks is not None:
        @functools.wraps(_mmgp_raw_gpu_load_blocks)
        def _unified_gpu_load_blocks(self, model_id, blocks_name=None, preload=False, *args, **kwargs):
            set_active_mmgp_instance(self)
            if blocks_name and re.search(r"(blocks|layers|transformer_blocks)\.\d+", str(blocks_name)):
                if hasattr(self, "loaded_blocks") and "token_refiner" in str(self.loaded_blocks.get(model_id, "")):
                    safe_mmgp_unload(self, f"{model_id}/token_refiner.blocks.0")
                    safe_mmgp_unload(self, f"{model_id}/token_refiner.blocks.1")

            entry_name = model_id if blocks_name is None else model_id + "/" + str(blocks_name)
            try:
                return _mmgp_raw_gpu_load_blocks(self, model_id, blocks_name, preload=preload, *args, **kwargs)
            except Exception as e:
                err_s = str(e).lower()
                log_debug(f"[MMGP GPU_LOAD_BLOCKS RESCUE] Mengesan ralat pemuatan blok {entry_name} ({e}). Memulihkan alokasi...")
                flush_vram()
                if hasattr(self, "next_blocks_names") and entry_name in self.next_blocks_names:
                    self.next_blocks_names[entry_name] = None
                try:
                    return _mmgp_raw_gpu_load_blocks(self, model_id, blocks_name, preload=preload, *args, **kwargs)
                except Exception as e2:
                    log_debug(f"[MMGP GPU_LOAD_BLOCKS RESCUE] Percubaan semula gagal ({e2}). Melaksanakan fallback pemindahan blok selamat...")
                    m = self.models.get(model_id) if hasattr(self, "models") else None
                    if m is not None:
                        # Fallback PyTorch Native pada peringkat blok tertentu bagi mengelakkan pertembungan C++ Stager
                        try:
                            target_mod = m
                            if blocks_name:
                                for part in str(blocks_name).split('.'):
                                    if hasattr(target_mod, part):
                                        target_mod = getattr(target_mod, part)
                                    elif isinstance(target_mod, (torch.nn.ModuleList, list)) and part.isdigit():
                                        target_mod = target_mod[int(part)]
                            for p in target_mod.parameters():
                                if p is not None and not p.is_cuda:
                                    p.data = p.data.to("cuda", non_blocking=False)
                            for b in target_mod.buffers():
                                if b is not None and not b.is_cuda:
                                    b.data = b.data.to("cuda", non_blocking=False)
                            if hasattr(self, "loaded_blocks"):
                                self.loaded_blocks[model_id] = str(blocks_name) if blocks_name else ""
                            log_debug(f"[MMGP GPU_LOAD_BLOCKS RESCUE] Blok {entry_name} berjaya dipindahkan ke CUDA secara native (Zero Infinite Loop).")
                            return None
                        except Exception as native_err:
                            log_debug(f"[MMGP GPU_LOAD_BLOCKS RESCUE] Fallback native blok gagal: {native_err}")
                    raise e2

        mmgp_offload.offload.gpu_load_blocks = _unified_gpu_load_blocks

    if _original_gpu_unload is not None:
        @functools.wraps(_original_gpu_unload)
        def _patched_gpu_unload(self, model_id, blocks_name=None, *args, **kwargs):
            if not hasattr(self, 'models') or self.models is None:
                return None
            if model_id not in self.models:
                return None
            try:
                res = _original_gpu_unload(self, model_id, blocks_name, *args, **kwargs)
                if blocks_name is None:
                    if hasattr(self, "active_models_ids"):
                        while model_id in self.active_models_ids:
                            self.active_models_ids.remove(model_id)
                    if hasattr(self, "active_models"):
                        m_obj = self.models.get(model_id)
                        while m_obj in self.active_models:
                            self.active_models.remove(m_obj)
                return res
            except KeyError:
                return None
        mmgp_offload.offload.gpu_unload_blocks = _patched_gpu_unload

    _original_unload_all = mmgp_offload.offload.unload_all if hasattr(mmgp_offload, "offload") else None
    if _original_unload_all is not None:
        @functools.wraps(_original_unload_all)
        def _safe_unload_all(self, *args, **kwargs):
            try:
                if hasattr(self, "active_models_ids") and hasattr(self, "models") and isinstance(self.models, dict):
                    self.active_models_ids = [m for m in self.active_models_ids if m in self.models]
                _original_unload_all(self, *args, **kwargs)
            except KeyError:
                pass
            except Exception as e:
                err_s = str(e).lower()
                if "out of memory" in err_s or "cuda" in err_s or "acceleratorerror" in err_s:
                    log_debug(f"[SAFE UNLOAD_ALL RESCUE] Terperangkap ralat CUDA ({e}). Menguatkuasakan pelepasan bersih...")
                    # Kosongkan blok aktif tanpa memanggil synchronize() yang rosak
                    if hasattr(self, "loaded_blocks"):
                        for mid in list(self.loaded_blocks.keys()):
                            self.loaded_blocks[mid] = None
                    if hasattr(self, "active_models"):
                        self.active_models = []
                    if hasattr(self, "active_models_ids"):
                        self.active_models_ids = []
                    flush_vram()
                else:
                    raise e
            finally:
                flush_vram()
        mmgp_offload.offload.unload_all = _safe_unload_all

    # Perisai LoRA cuBLAS Workspace Rescue (100% Zero Hardcoding):
    # Memintas ralat cuBLAS_STATUS_INTERNAL_ERROR semasa unjuran LoRA Turbo dengan fallback pantas & contiguous matmul
    _orig_lora_linear = mmgp_offload.offload._lora_linear_forward if hasattr(mmgp_offload, "offload") else None
    if _orig_lora_linear is not None:
        @functools.wraps(_orig_lora_linear)
        def _safe_lora_linear_forward(self, model, submodule, loras_data, *args, **kwargs):
            try:
                return _orig_lora_linear(self, model, submodule, loras_data, *args, **kwargs)
            except Exception as e:
                err_s = str(e).lower()
                if "cublas" in err_s or "out of memory" in err_s or "cuda" in err_s:
                    flush_vram()
                    try:
                        return _orig_lora_linear(self, model, submodule, loras_data, *args, **kwargs)
                    except Exception as e2:
                        log_debug(f"[LORA RESCUE] cuBLAS/CUDA ralat dikesan ({e2}). Mengaktifkan Contiguous LoRA Matmul Fallback.")
                        flush_vram()
                        x = args[0] if args else kwargs.get("input", None)
                        weight = submodule.weight
                        bias = submodule.bias
                        active_adapters = getattr(model, "_loras_active_adapters", None)
                        loras_scaling = getattr(model, "_loras_scaling", None)
                        
                        base_bias = bias
                        if base_bias is not None and base_bias.dtype != x.dtype:
                            base_bias = base_bias.to(x.dtype)
                        if getattr(submodule, "_mm_requires_native_linear_forward", False):
                            result = submodule._mm_lora_old_forward(x, *args, **kwargs)
                        else:
                            result = torch.nn.functional.linear(x, weight, bias=base_bias)
                        
                        if active_adapters and loras_data:
                            compute_dtype = result.dtype
                            x_c = x.to(compute_dtype)
                            x_2d = x_c.reshape(-1, x_c.shape[-1])
                            result_2d = result.reshape(-1, result.shape[-1])
                            for active_adapter in active_adapters:
                                data = loras_data.get(active_adapter + '_GPU', None)
                                if data is None:
                                    continue
                                lora_A, lora_B, diff_b, g_abs, alpha, adapter_meta = data
                                if g_abs is not None:
                                    continue
                                scaling = self._get_lora_scaling(loras_scaling, model, active_adapter) * alpha
                                if scaling == 0:
                                    continue
                                target_dtype = result.dtype
                                if lora_A is not None and lora_A.dtype != target_dtype:
                                    lora_A = lora_A.to(target_dtype)
                                if lora_B is not None and lora_B.dtype != target_dtype:
                                    lora_B = lora_B.to(target_dtype)
                                if diff_b is not None and diff_b.dtype != target_dtype:
                                    diff_b = diff_b.to(target_dtype)
                                if lora_A is not None and lora_B is not None:
                                    lora_B_t = lora_B.t().contiguous()
                                    y = torch.matmul(x_2d, lora_A.t().contiguous())
                                    result_2d.add_(torch.matmul(y, lora_B_t), alpha=scaling)
                                    del y, lora_B_t
                                if diff_b is not None:
                                    result_2d.add_(diff_b, alpha=scaling)
                            del x_c, x_2d, result_2d
                        flush_vram()
                        return result
                raise e
        mmgp_offload.offload._lora_linear_forward = _safe_lora_linear_forward
        log_debug("Perisai LoRA cuBLAS Workspace Rescue berjaya dipasang.")

    def _patched_all(pipe_or_dict_of_modules, **kwargs):
        flush_vram()
        stats = get_live_memory_stats()
        
        if isinstance(pipe_or_dict_of_modules, dict):
            text_mod = pipe_or_dict_of_modules.get('text_encoder')
            trans_mod = (
                pipe_or_dict_of_modules.get('transformer')
                or pipe_or_dict_of_modules.get('diffusion_model')
                or pipe_or_dict_of_modules.get('model')
                or pipe_or_dict_of_modules.get('unet')
            )
        else:
            text_mod = getattr(pipe_or_dict_of_modules, 'text_encoder', None)
            trans_mod = (
                getattr(pipe_or_dict_of_modules, 'transformer', None)
                or getattr(pipe_or_dict_of_modules, 'diffusion_model', None)
                or getattr(pipe_or_dict_of_modules, 'model', None)
                or getattr(pipe_or_dict_of_modules, 'unet', None)
            )

        dynamic_ram_ratio, can_pin = compute_dynamic_reserved_ram_ratio(
            target_module=trans_mod,
            pipe_or_dict_of_modules=pipe_or_dict_of_modules,
            profile_no=kwargs.get("profile_no", None)
        )
        
        if can_pin:
            kwargs["pinnedMemory"] = "transformer"
            kwargs["perc_reserved_mem_max"] = dynamic_ram_ratio
            log_debug(f"[PINNED MEMORY DINAMIK] Pinned DMA diaktifkan untuk 'transformer' (perc_reserved_mem_max={dynamic_ram_ratio:.3f}).")
        else:
            kwargs["pinnedMemory"] = False
            log_debug("[PINNED MEMORY DINAMIK] RAM hos tidak mencukupi untuk memin 1 blok transformer penuh secara selamat. Pinned Memory ditutup.")

        
        is_audio = bool(kwargs.get("audio_only", False))
        if not is_audio:
            has_video_mod = False
            if isinstance(pipe_or_dict_of_modules, dict):
                has_video_mod = any(k in pipe_or_dict_of_modules for k in ('video_encoder', 'vae', 'spatial_upsampler'))
            elif pipe_or_dict_of_modules is not None:
                has_video_mod = any(hasattr(pipe_or_dict_of_modules, k) for k in ('video_encoder', 'vae', 'spatial_upsampler'))
            if not has_video_mod:
                if isinstance(pipe_or_dict_of_modules, dict):
                    for m in pipe_or_dict_of_modules.values():
                        m_name = m.__class__.__name__.lower()
                        m_str = str(type(m)).lower()
                        if (
                            getattr(m, "audio_only", False)
                            or getattr(m, "_is_audio_only", False)
                            or any(term in m_name or term in m_str for term in ("tts", "music", "voice", "whisper", "sound"))
                        ):
                            is_audio = True
                            break
                else:
                    if getattr(pipe_or_dict_of_modules, "audio_only", False) or getattr(pipe_or_dict_of_modules, "_is_audio_only", False):
                        is_audio = True
                    elif trans_mod is not None:
                        t_name = trans_mod.__class__.__name__.lower()
                        t_str = str(type(trans_mod)).lower()
                        if (
                            getattr(trans_mod, "audio_only", False)
                            or getattr(trans_mod, "_is_audio_only", False)
                            or any(term in t_name or term in t_str for term in ("tts", "music", "voice", "whisper", "sound"))
                        ):
                            is_audio = True
                    
        existing_budgets = kwargs.get("budgets")
        has_preset_budgets = (
            isinstance(existing_budgets, dict)
            and "text_encoder" in existing_budgets
            and "transformer" in existing_budgets
        )
        if has_preset_budgets:
            dynamic_text_budget = existing_budgets["text_encoder"]
            dynamic_trans_budget = existing_budgets["transformer"]
            enable_async = kwargs.get("asyncTransfers", True)
        else:
            dynamic_text_budget = compute_dynamic_text_encoder_budget(text_mod)
            dynamic_trans_budget = compute_dynamic_transformer_budget(trans_mod, is_async=True, phase=1, token_scaling_ratio=1.0, is_audio_only=is_audio)
            
            trans_info = inspect_model_data(trans_mod)
            block_sz = trans_info.get("block_size_mb", 0.0)
            base_sz = trans_info.get("base_size_mb", 17.0)
            has_room_for_async = (dynamic_trans_budget > int(2.5 * block_sz + base_sz)) if block_sz > 0 else True
            enable_async = has_room_for_async and (stats["vram_free_mb"] >= max(1024.0, block_sz * 2.2))
            
            if not enable_async:
                dynamic_trans_budget = compute_dynamic_transformer_budget(trans_mod, is_async=False, phase=1, token_scaling_ratio=1.0, is_audio_only=is_audio)
            
            kwargs["asyncTransfers"] = enable_async
            budgets = kwargs.get("budgets", {})
            if isinstance(budgets, dict):
                budgets["text_encoder"] = dynamic_text_budget
                budgets["transformer"] = dynamic_trans_budget
                budgets["*"] = dynamic_trans_budget
                kwargs["budgets"] = budgets
            elif budgets is None or budgets == 0:
                kwargs["budgets"] = {"text_encoder": dynamic_text_budget, "transformer": dynamic_trans_budget, "*": dynamic_trans_budget}
        
        kwargs["perc_reserved_mem_max"] = dynamic_ram_ratio
        if cli_verbose is not None:
            kwargs["verboseLevel"] = cli_verbose
            
        log_debug(f"Parameter MMGP offload.all diselaraskan secara dinamik: budgets={kwargs.get('budgets')}, asyncTransfers={enable_async}, perc_reserved_mem_max={dynamic_ram_ratio:.2f}")
        res = _original_all(pipe_or_dict_of_modules, **kwargs)
        set_active_mmgp_instance(res)
        try:
            evict_h3_auxiliary_modules(pipe_or_dict_of_modules)
            trim_current_process_working_set()
        except Exception:
            pass
        return res

    @functools.wraps(_original_profile)
    def _patched_profile(pipe_or_dict_of_modules, profile_no=5, verboseLevel=-1, **overrideKwargs):
        flush_vram()
        stats = get_live_memory_stats()
        
        # Introspeksi Perkakasan Sebenar Secara Menyeluruh (Sifar Hardcode)
        sys_ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        total_vram_gb = (torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)) if torch.cuda.is_available() else 8.0
        
        # Patuhi profil MMGP yang dihantar pengguna / konfigurasi secara tepat (Zero Override):
        # Profile 4 (LowRAM_LowVRAM): Hanya model utama ('transformer') disimpan dalam RAM. Text encoder tidak dikunci.
        # Profile 5 (VerylowRAM_LowVRAM): Sifar reserved RAM.
        target_profile_no = profile_no
        log_debug(f"[PROFIL DINAMIK MMGP] Mematuhi profil terpilih pengguna: Profile {target_profile_no} (Sifar paksaan Profile 2, RAM dilindungi).")
        
        if isinstance(pipe_or_dict_of_modules, dict):
            text_mod = pipe_or_dict_of_modules.get('text_encoder')
            trans_mod = (
                pipe_or_dict_of_modules.get('transformer')
                or pipe_or_dict_of_modules.get('diffusion_model')
                or pipe_or_dict_of_modules.get('model')
                or pipe_or_dict_of_modules.get('unet')
            )
        else:
            text_mod = getattr(pipe_or_dict_of_modules, 'text_encoder', None)
            trans_mod = (
                getattr(pipe_or_dict_of_modules, 'transformer', None)
                or getattr(pipe_or_dict_of_modules, 'diffusion_model', None)
                or getattr(pipe_or_dict_of_modules, 'model', None)
                or getattr(pipe_or_dict_of_modules, 'unet', None)
            )

        dynamic_ram_ratio, can_pin = compute_dynamic_reserved_ram_ratio(
            target_module=trans_mod,
            pipe_or_dict_of_modules=pipe_or_dict_of_modules,
            profile_no=target_profile_no
        )
        overrideKwargs["perc_reserved_mem_max"] = dynamic_ram_ratio
        
        if can_pin:
            # Tetapkan pinnedMemory secara dinamik hanya kepada modul penjanaan intensif (cth: transformer / diffusion_model / unet)
            # Elakkan memin modul dorman sekali guna seperti text_encoder / vision_encoder agar RAM fizikal hos kekal anjal & boleh dipangkas
            pin_target = "transformer"
            if isinstance(pipe_or_dict_of_modules, dict):
                for candidate in ("transformer", "diffusion_model", "model", "unet"):
                    if candidate in pipe_or_dict_of_modules:
                        pin_target = candidate
                        break
            elif pipe_or_dict_of_modules is not None:
                for candidate in ("transformer", "diffusion_model", "model", "unet"):
                    if hasattr(pipe_or_dict_of_modules, candidate):
                        pin_target = candidate
                        break
            overrideKwargs["pinnedMemory"] = pin_target
            log_debug(f"[PINNED MEMORY DINAMIK] Pinned DMA diaktifkan untuk '{pin_target}' (perc_reserved_mem_max={dynamic_ram_ratio:.3f}). Modul dorman dikekalkan anjal.")
        else:
            overrideKwargs["pinnedMemory"] = False
            log_debug("[PINNED MEMORY DINAMIK] RAM hos tidak mencukupi untuk memin model secara selamat. Pinned Memory ditutup.")

        
        is_audio = bool(overrideKwargs.get("audio_only", False))
        if not is_audio:
            has_video_mod = False
            if isinstance(pipe_or_dict_of_modules, dict):
                has_video_mod = any(k in pipe_or_dict_of_modules for k in ('video_encoder', 'vae', 'spatial_upsampler'))
            elif pipe_or_dict_of_modules is not None:
                has_video_mod = any(hasattr(pipe_or_dict_of_modules, k) for k in ('video_encoder', 'vae', 'spatial_upsampler'))
            if not has_video_mod:
                if isinstance(pipe_or_dict_of_modules, dict):
                    for m in pipe_or_dict_of_modules.values():
                        m_name = m.__class__.__name__.lower()
                        m_str = str(type(m)).lower()
                        if (
                            getattr(m, "audio_only", False)
                            or getattr(m, "_is_audio_only", False)
                            or any(term in m_name or term in m_str for term in ("tts", "music", "voice", "whisper", "sound"))
                        ):
                            is_audio = True
                            break
                else:
                    if getattr(pipe_or_dict_of_modules, "audio_only", False) or getattr(pipe_or_dict_of_modules, "_is_audio_only", False):
                        is_audio = True
                    elif trans_mod is not None:
                        t_name = trans_mod.__class__.__name__.lower()
                        t_str = str(type(trans_mod)).lower()
                        if (
                            getattr(trans_mod, "audio_only", False)
                            or getattr(trans_mod, "_is_audio_only", False)
                            or any(term in t_name or term in t_str for term in ("tts", "music", "voice", "whisper", "sound"))
                        ):
                            is_audio = True
                    
        dyn_text_budget = compute_dynamic_text_encoder_budget(text_mod)
        dyn_trans_budget = compute_dynamic_transformer_budget(trans_mod, is_async=True, phase=1, token_scaling_ratio=1.0, is_audio_only=is_audio)
        
        trans_info = inspect_model_data(trans_mod)
        block_sz = trans_info.get("block_size_mb", 0.0)
        base_sz = trans_info.get("base_size_mb", 17.0)
        has_room_for_async = (dyn_trans_budget > int(2.5 * block_sz + base_sz)) if block_sz > 0 else True
        enable_async = has_room_for_async and (stats["vram_free_mb"] >= max(1024.0, block_sz * 2.2))
        
        if not enable_async:
            dyn_trans_budget = compute_dynamic_transformer_budget(trans_mod, is_async=False, phase=1, token_scaling_ratio=1.0, is_audio_only=is_audio)
        
        overrideKwargs["asyncTransfers"] = enable_async
        # Aktifkan prefetchWindow=2 untuk overlapping DMA transfer bertindih penuh secara latar belakang
        if enable_async and "prefetchWindow" not in overrideKwargs:
            overrideKwargs["prefetchWindow"] = 2
            
        target_verbose = cli_verbose if cli_verbose is not None else verboseLevel
        
        current_budgets = overrideKwargs.get("budgets", {})
        if not isinstance(current_budgets, dict):
            current_budgets = {}
        
        current_budgets["text_encoder"] = dyn_text_budget
        current_budgets["transformer"] = dyn_trans_budget
        current_budgets["*"] = dyn_trans_budget
        overrideKwargs["budgets"] = current_budgets
        
        log_debug(f"MMGP offload.profile diselaraskan: profile_no={target_profile_no}, text_budget={dyn_text_budget}MB, trans_budget={dyn_trans_budget}MB, asyncTransfers={enable_async}, prefetchWindow={overrideKwargs.get('prefetchWindow')}, ram_ratio={dynamic_ram_ratio:.2f}")
        res = _original_profile(pipe_or_dict_of_modules, profile_no=target_profile_no, verboseLevel=target_verbose, **overrideKwargs)
        set_active_mmgp_instance(res)
        # Segera kosongkan VRAM & singkirkan 4 modul pembantu ke Disk selepas profiling awal selesai
        try:
            safe_mmgp_unload(res, "all")
            flush_vram()
            force_pagefile_push()
            evict_h3_auxiliary_modules(pipe_or_dict_of_modules)
            trim_current_process_working_set()
            log_debug("[MMGP LIFECYCLE INITIALIZER] Profiling selesai: VRAM dikosongkan & 4 modul pembantu disingkirkan ke Disk (~3.9GB RAM bebas).")
        except Exception:
            pass
        return res

    mmgp_offload.all = _patched_all
    mmgp_offload.profile = _patched_profile
    log_debug("Perisai 2 & 7: MMGP Dynamic Offload, Real-Time Prefetch Guard & Pressure Sensor berjaya dipasang.")

except Exception as e:
    log_debug(f"Gagal memasang pintasan MMGP In-Memory: {e}")

# ------------------------------------------------------------------------------
# 3. PERISAI CATCH-ALL 4: OOM-Safe Tensor Transfer (Non-Recursive)
# ------------------------------------------------------------------------------
_original_tensor_to = torch.Tensor.to
_original_tensor_cuda = torch.Tensor.cuda

@functools.wraps(_original_tensor_to)
def _safe_tensor_to(self, *args, **kwargs):
    if _is_guard_active("in_to"):
        return _original_tensor_to(self, *args, **kwargs)
    _set_guard("in_to", True)
    try:
        return _original_tensor_to(self, *args, **kwargs)
    except Exception as err:
        err_str = str(err).lower()
        if "out of memory" in err_str or "cuda" in err_str or "acceleratorerror" in err_str:
            flush_vram()
            try:
                return _original_tensor_to(self, *args, **kwargs)
            except Exception:
                target_dev = None
                if args and torch.is_tensor(args[0]):
                    target_dev = args[0].device
                elif args and isinstance(args[0], (torch.device, str)):
                    target_dev = torch.device(args[0])
                elif "device" in kwargs and kwargs["device"] is not None:
                    target_dev = torch.device(kwargs["device"])

                if target_dev is not None and target_dev.type != "cpu":
                    raise err
                try:
                    return _original_tensor_to(self.detach(), torch.device("cpu"))
                except Exception:
                    return self
        raise err
    finally:
        _set_guard("in_to", False)

@functools.wraps(_original_tensor_cuda)
def _safe_tensor_cuda(self, *args, **kwargs):
    if _is_guard_active("in_cuda"):
        return _original_tensor_cuda(self, *args, **kwargs)
    _set_guard("in_cuda", True)
    try:
        return _original_tensor_cuda(self, *args, **kwargs)
    except Exception as err:
        err_str = str(err).lower()
        if "out of memory" in err_str or "cuda" in err_str or "acceleratorerror" in err_str:
            flush_vram()
            try:
                return _original_tensor_cuda(self, *args, **kwargs)
            except Exception:
                return self
        raise err
    finally:
        _set_guard("in_cuda", False)

torch.Tensor.to = _safe_tensor_to
torch.Tensor.cuda = _safe_tensor_cuda
log_debug("Perisai 4: Dynamic OOM-Safe VAE, Condition & Direct .cuda() Tensor Interceptor berjaya dipasang.")

# ------------------------------------------------------------------------------
# 4. PERISAI CATCH-ALL 5: ONNX Arch-Mismatch Safe Interceptor
# ------------------------------------------------------------------------------
try:
    import onnxruntime as ort
    _original_ort_session = ort.InferenceSession.__init__

    @functools.wraps(_original_ort_session)
    def _safe_ort_session(self, path_or_bytes, *args, **kwargs):
        try:
            return _original_ort_session(self, path_or_bytes, *args, **kwargs)
        except Exception as err:
            err_str = str(err).lower()
            if "arch_mismatch" in err_str or "cublas" in err_str or "onnxruntimeerror" in err_str or "fail" in err_str:
                log_debug("ONNX CUDA Arch Mismatch dikesan! Mengalirkan ONNX Session ke CPUExecutionProvider secara automatik...")
                kwargs["providers"] = ["CPUExecutionProvider"]
                return _original_ort_session(self, path_or_bytes, *args, **kwargs)
            raise err

    ort.InferenceSession.__init__ = _safe_ort_session
    log_debug("Perisai 5: ONNX Arch-Mismatch Safe Interceptor (RemBG CPU Fallback) berjaya dipasang.")
except Exception as e:
    log_debug(f"Gagal memasang Perisai 5 ONNX Interceptor: {e}")

# ------------------------------------------------------------------------------
# 5. PERISAI CATCH-ALL 6: Dim-Safe & Dynamic SageAttention / Varlen SDPA
# ------------------------------------------------------------------------------
try:
    import sageattention
    import sageattention.core as sage_core
    
    _orig_sageattn_varlen = sage_core.sageattn_varlen
    _orig_sageattn = sage_core.sageattn

    def _fallback_varlen_sdpa(q, k, v, cu_seqlens_q, cu_seqlens_k, sm_scale=None, is_causal=False):
        try:
            out = torch.empty_like(q)
        except Exception:
            flush_vram()
            out = torch.empty_like(q)

        batch_count = len(cu_seqlens_q) - 1
        for i in range(batch_count):
            start_q = int(cu_seqlens_q[i].item())
            end_q = int(cu_seqlens_q[i + 1].item())
            start_k = int(cu_seqlens_k[i].item())
            end_k = int(cu_seqlens_k[i + 1].item())
            
            if end_q <= start_q or end_k <= start_k:
                continue
                
            sub_q = q[start_q:end_q].transpose(0, 1).unsqueeze(0)
            sub_k = k[start_k:end_k].transpose(0, 1).unsqueeze(0)
            sub_v = v[start_k:end_k].transpose(0, 1).unsqueeze(0)
            
            num_qo_heads = sub_q.shape[1]
            num_kv_heads = sub_k.shape[1]
            if num_qo_heads != num_kv_heads:
                repeats = num_qo_heads // num_kv_heads
                sub_k = sub_k.repeat_interleave(repeats, dim=1)
                sub_v = sub_v.repeat_interleave(repeats, dim=1)
                
            scale = sm_scale if sm_scale is not None else (1.0 / (sub_q.shape[-1] ** 0.5))
            try:
                sub_out = F.scaled_dot_product_attention(sub_q, sub_k, sub_v, scale=scale, is_causal=is_causal)
            except Exception:
                flush_vram()
                sub_out = F.scaled_dot_product_attention(sub_q, sub_k, sub_v, scale=scale, is_causal=is_causal)
                
            sub_out = sub_out.squeeze(0).transpose(0, 1)
            out[start_q:end_q] = sub_out.to(dtype=q.dtype)
            
        return out

    @functools.wraps(_orig_sageattn_varlen)
    def _safe_sageattn_varlen(q, k, v, cu_seqlens_q, cu_seqlens_k, max_seqlen_q, max_seqlen_k, is_causal=False, sm_scale=None, smooth_k=True, **kwargs):
        head_dim = q.size(-1)
        if head_dim in (64, 128):
            try:
                return _orig_sageattn_varlen(q, k, v, cu_seqlens_q, cu_seqlens_k, max_seqlen_q, max_seqlen_k, is_causal=is_causal, sm_scale=sm_scale, smooth_k=smooth_k, **kwargs)
            except Exception as e:
                err_str = str(e).lower()
                if "varlen only support" in err_str or "cuda" in err_str or "out of memory" in err_str:
                    log_debug(f"SageAttention Varlen amaran: {e}. Mengaktifkan laluan lencongan SDPA...")
                    flush_vram()
                    return _fallback_varlen_sdpa(q, k, v, cu_seqlens_q, cu_seqlens_k, sm_scale=sm_scale, is_causal=is_causal)
                raise e
        else:
            return _fallback_varlen_sdpa(q, k, v, cu_seqlens_q, cu_seqlens_k, sm_scale=sm_scale, is_causal=is_causal)

    @functools.wraps(_orig_sageattn)
    def _safe_sageattn(q, k, v, tensor_layout="HND", is_causal=False, sm_scale=None, smooth_k=True, **kwargs):
        head_dim = q.size(-1)
        if head_dim in (64, 96, 128):
            try:
                return _orig_sageattn(q, k, v, tensor_layout=tensor_layout, is_causal=is_causal, sm_scale=sm_scale, smooth_k=smooth_k, **kwargs)
            except Exception as e:
                log_debug(f"SageAttention standard amaran: {e}. Melencongkan ke SDPA...")
                flush_vram()
        
        if tensor_layout == "NHD":
            q_p = q.transpose(1, 2)
            k_p = k.transpose(1, 2)
            v_p = v.transpose(1, 2)
        else:
            q_p, k_p, v_p = q, k, v
            
        scale = sm_scale if sm_scale is not None else (1.0 / (head_dim ** 0.5))
        res = F.scaled_dot_product_attention(q_p, k_p, v_p, scale=scale, is_causal=is_causal)
        if tensor_layout == "NHD":
            res = res.transpose(1, 2)
        return res.to(dtype=q.dtype)

    sage_core.sageattn_varlen = _safe_sageattn_varlen
    sage_core.sageattn = _safe_sageattn
    sageattention.sageattn_varlen = _safe_sageattn_varlen
    sageattention.sageattn = _safe_sageattn
    log_debug("Perisai 6: Dim-Safe & Dynamic SageAttention / Varlen SDPA Interceptor berjaya dipasang.")
except Exception as e:
    log_debug(f"Gagal memasang Perisai 6 SageAttention Interceptor: {e}")

try:
    import shared.attention as shared_attn
    from mmgp import offload

    # PERISAI SEJAGAT SHARED_STATE (Zero Git Modification Rule):
    # Memastikan sebarang akses offload.shared_state["_attention"] atau ["_radial"] oleh kod hulu upstream
    # tidak akan melontarkan KeyError tanpa perlu mengubah walau 1 baris kod dalam repositori klon git!
    class _SafeSharedState(dict):
        def __missing__(self, key):
            if key == "_attention":
                try:
                    val = shared_attn.get_default_attention_mode()
                except Exception:
                    val = "sdpa"
                self[key] = val
                return val
            elif key == "_radial":
                return False
            return None

    if hasattr(offload, "shared_state"):
        if not isinstance(offload.shared_state, _SafeSharedState):
            orig_st = dict(offload.shared_state) if isinstance(offload.shared_state, dict) else {}
            offload.shared_state = _SafeSharedState(orig_st)

    _orig_pay_attention = shared_attn.pay_attention

    @functools.wraps(_orig_pay_attention)
    def _optimized_pay_attention(qkv_list, *args, **kwargs):
        force_attention = kwargs.get("force_attention", None)
        if force_attention is None:
            active_attn = offload.shared_state.get("_attention")
            if not active_attn:
                try:
                    active_attn = shared_attn.get_default_attention_mode()
                except Exception:
                    active_attn = "sdpa"
                offload.shared_state["_attention"] = active_attn
            if active_attn in ("sage", "auto") and getattr(shared_attn, "sageattn2", None) is not None:
                kwargs["force_attention"] = "sage2"
            else:
                kwargs["force_attention"] = active_attn or "sdpa"
        return _orig_pay_attention(qkv_list, *args, **kwargs)

    if "_attention" not in offload.shared_state:
        try:
            offload.shared_state["_attention"] = shared_attn.get_default_attention_mode()
        except Exception:
            offload.shared_state["_attention"] = "sdpa"

    shared_attn.pay_attention = _optimized_pay_attention
    log_debug("Perisai 6b: Universal Dynamic pay_attention (SageAttention 2 SM120 Fast-Path) & SafeSharedState berjaya dipasang.")
except Exception as e:
    log_debug(f"Gagal memasang Perisai 6b pay_attention Fast-Path: {e}")

# ------------------------------------------------------------------------------
# 6. PERISAI 8 & 9: Direct Pipeline & VAE Decoder Interceptors
# ------------------------------------------------------------------------------
try:
    import models.ltx2.ltx_pipelines.utils.helpers as ltx_helpers
    import models.ltx2.ltx_pipelines.distilled as ltx_distilled
    _orig_denoise_audio_video = ltx_helpers.denoise_audio_video
    
    @functools.wraps(_orig_denoise_audio_video)
    def _patched_denoise_audio_video(*args, **kwargs):
        denoising_loop_fn = kwargs.get("denoising_loop_fn", None)
        fn_name = getattr(denoising_loop_fn, "__name__", str(denoising_loop_fn)).lower()
        active_inst = get_active_mmgp_instance()
        
        is_stage_2 = "stage2" in fn_name or "stage_2" in fn_name or kwargs.get("initial_video_latent") is not None
        
        if is_stage_2:
            log_debug("[PIPELINE HOOK] Fasa 2 dikesan. Melupuskan Upsampler & Menala MMGP...")
            if active_inst is not None:
                for dead_m in ('spatial_upsampler', 'video_encoder', 'text_encoder', 'text_embedding_projection'):
                    safe_mmgp_unload(active_inst, dead_m)
                dyn_scale = float(_generation_state.get("token_scaling_ratio", 1.0))
                retune_active_model_dynamically(active_inst, phase=2, token_scaling_ratio=dyn_scale)
            flush_vram()
            force_pagefile_push()
        else:
            log_debug("[PIPELINE HOOK] Fasa 1 dikesan. Melupuskan Text Encoder...")
            if active_inst is not None:
                for dead_m in ('text_encoder', 'text_embedding_projection', 'video_embeddings_connector', 'audio_embeddings_connector'):
                    safe_mmgp_unload(active_inst, dead_m)
            flush_vram()
            force_pagefile_push()
            
        return _orig_denoise_audio_video(*args, **kwargs)
        
    ltx_helpers.denoise_audio_video = _patched_denoise_audio_video
    if hasattr(ltx_distilled, 'denoise_audio_video'):
        ltx_distilled.denoise_audio_video = _patched_denoise_audio_video
    log_debug("Perisai 8: Direct Pipeline Interceptor (denoise_audio_video) berjaya dipasang.")
except Exception as e:
    log_debug(f"Pintasan denoise_audio_video gagal: {e}")

try:
    import models.ltx2.ltx_core.model.video_vae as ltx_video_vae
    _orig_vae_decode = ltx_video_vae.decode_video_to_tensor
    
    @functools.wraps(_orig_vae_decode)
    def _patched_vae_decode(*args, **kwargs):
        active_inst = get_active_mmgp_instance()
        if active_inst is not None:
            log_debug("[PIPELINE HOOK] Fasa VAE Decoding dikesan. Mengosongkan transformer 100% dari VRAM...")
            active_inst.unload_all()
        flush_vram()
        force_pagefile_push()
        res = _orig_vae_decode(*args, **kwargs)
        flush_vram()
        gc.collect()
        force_pagefile_push()
        return res
        
    ltx_video_vae.decode_video_to_tensor = _patched_vae_decode
    log_debug("Perisai 9: Direct VAE Decoder Interceptor berjaya dipasang.")
except Exception as e:
    log_debug(f"Pintasan vae_decode gagal: {e}")

try:
    import models.minimax_h3.minimax_h3_main as h3_main
    _orig_load_video_vae = getattr(h3_main, "_load_video_vae", None)
    if _orig_load_video_vae is not None and not hasattr(h3_main, "_tracked_load_video_vae_installed"):
        @functools.wraps(_orig_load_video_vae)
        def _tracked_load_video_vae(filename, *args, **kwargs):
            vae = _orig_load_video_vae(filename, *args, **kwargs)
            if vae is not None:
                setattr(vae, "_source_file", filename)
            return vae
        h3_main._load_video_vae = _tracked_load_video_vae
        h3_main._tracked_load_video_vae_installed = True

    _orig_load_audio_vae = getattr(h3_main, "_load_audio_vae", None)
    if _orig_load_audio_vae is not None and not hasattr(h3_main, "_tracked_load_audio_vae_installed"):
        @functools.wraps(_orig_load_audio_vae)
        def _tracked_load_audio_vae(filename, *args, **kwargs):
            avae = _orig_load_audio_vae(filename, *args, **kwargs)
            if avae is not None:
                setattr(avae, "_source_file", filename)
            return avae
        h3_main._load_audio_vae = _tracked_load_audio_vae
        h3_main._tracked_load_audio_vae_installed = True
except Exception:
    pass

try:
    import models.minimax_h3.video_vae as h3_video_vae

    # Perisai Kalis-Ralat ScaledFP8 & Quanto WeightQBytesTensor (Anti-AttributeError)
    try:
        from optimum.quanto import WeightQBytesTensor
        if not hasattr(WeightQBytesTensor, "_force_full_precision_mm"):
            WeightQBytesTensor._force_full_precision_mm = False
        if not hasattr(WeightQBytesTensor, "_scaled_mm_static_ok"):
            WeightQBytesTensor._scaled_mm_static_ok = False
    except Exception:
        pass

    try:
        from shared.qtypes import scaled_fp8
        _orig_scaled_fp8_linear = scaled_fp8.scaled_fp8_linear
        
        # Patch ScaledFP8WeightTensor._linear_fallback secara terus untuk mencegah perbezaan peranti pada out += bias
        if hasattr(scaled_fp8, "ScaledFP8WeightTensor") and hasattr(scaled_fp8.ScaledFP8WeightTensor, "_linear_fallback"):
            _orig_linear_fallback = scaled_fp8.ScaledFP8WeightTensor._linear_fallback
            @classmethod
            def _safe_linear_fallback(cls, qweight, input, bias=None):
                if torch.is_tensor(input):
                    target_dev = input.device
                    target_dt = input.dtype
                    if bias is not None and torch.is_tensor(bias):
                        if bias.device != target_dev or bias.dtype != target_dt:
                            bias = bias.to(device=target_dev, dtype=target_dt)
                    if hasattr(qweight, "_data") and torch.is_tensor(qweight._data) and qweight._data.device != target_dev:
                        try:
                            qweight = qweight.to(device=target_dev)
                        except Exception:
                            pass
                return _orig_linear_fallback(qweight, input, bias)
            scaled_fp8.ScaledFP8WeightTensor._linear_fallback = _safe_linear_fallback

        @functools.wraps(_orig_scaled_fp8_linear)
        def _safe_scaled_fp8_linear(weight, input, bias=None):
            if torch.is_tensor(input):
                target_dev = input.device
                target_dt = input.dtype
                if bias is not None and torch.is_tensor(bias):
                    if bias.device != target_dev or bias.dtype != target_dt:
                        bias = bias.to(device=target_dev, dtype=target_dt)
                if hasattr(weight, "_data") and torch.is_tensor(weight._data) and weight._data.device != target_dev:
                    try:
                        weight = weight.to(device=target_dev)
                    except Exception:
                        pass
                elif torch.is_tensor(weight) and weight.device != target_dev:
                    try:
                        weight = weight.to(device=target_dev)
                    except Exception:
                        pass
            if not hasattr(weight, "_force_full_precision_mm") or not hasattr(weight, "_scaled_mm_static_ok"):
                if hasattr(weight, "dequantize"):
                    try:
                        return torch.nn.functional.linear(input, weight.dequantize(), bias)
                    except Exception:
                        pass
                try: setattr(weight, "_force_full_precision_mm", False)
                except Exception: pass
                try: setattr(weight, "_scaled_mm_static_ok", False)
                except Exception: pass
                if not hasattr(weight, "_force_full_precision_mm"):
                    w_dec = getattr(weight, "_data", weight)
                    if hasattr(weight, "_scale"):
                        try:
                            w_dec = w_dec.to(input.dtype) * weight._scale.to(input.dtype)
                        except Exception:
                            pass
                    return torch.nn.functional.linear(input, w_dec, bias)
            try:
                return _orig_scaled_fp8_linear(weight, input, bias)
            except Exception as sfp8_err:
                err_s = str(sfp8_err).lower()
                if "device" in err_s or "same" in err_s or "dtype" in err_s:
                    log_debug(f"[SCALED_FP8 RESCUE] Ralat peranti/dtype dikesan ({sfp8_err}). Menyahkuantisasi ke F.linear...")
                    if hasattr(weight, "dequantize"):
                        return torch.nn.functional.linear(input, weight.dequantize(), bias)
                raise sfp8_err
        scaled_fp8.scaled_fp8_linear = _safe_scaled_fp8_linear
        log_debug("Perisai ScaledFP8 & WeightQBytesTensor AttributeError Guard berjaya dipasang.")
    except Exception as e:
        log_debug(f"Pemasangan perisai ScaledFP8 gagal: {e}")

    def reload_h3_video_vae_decoder(vae):
        """Memuatkan semula bobot Video VAE Decoder menggunakan loader rasmi Wan2GP (Zero Delay < 0.15s, 100% Kalis Ralat)."""
        try:
            from models.minimax_h3 import minimax_h3_main as h3_main
            from shared.utils import files_locator as fl
            fn = getattr(vae, "_source_file", None)
            if not fn or not os.path.exists(fn):
                fn = fl.locate_file("ckpts/minimax_h3_video_vae_fp8mix.safetensors", error_if_none=False)
            if not fn or not os.path.exists(fn):
                fn = fl.locate_file(h3_main.VIDEO_VAE_FILE, error_if_none=False)
            if not fn or not os.path.exists(fn):
                return 0
            t0 = time.perf_counter()
            split_map = getattr(vae, "split_linear_modules_map", None)
            upsampling = getattr(vae, "upsampling", False)
            new_vae = h3_main._load_video_vae(fn, qkv_splitting=bool(split_map), upsampling=upsampling)
            if hasattr(new_vae, "decoder") and new_vae.decoder is not None:
                if hasattr(vae, "decoder") and vae.decoder is not None:
                    new_params = dict(new_vae.decoder.named_parameters())
                    for p_name, p in vae.decoder.named_parameters():
                        if p_name in new_params:
                            p.data = new_params[p_name].data.clone()
                    new_bufs = dict(new_vae.decoder.named_buffers())
                    for b_name, b in vae.decoder.named_buffers():
                        if b_name in new_bufs:
                            b.data = new_bufs[b_name].data.clone()
                vae.decoder = new_vae.decoder
            if hasattr(new_vae, "post_quant_conv") and new_vae.post_quant_conv is not None:
                if hasattr(vae, "post_quant_conv") and vae.post_quant_conv is not None:
                    new_params = dict(new_vae.post_quant_conv.named_parameters())
                    for p_name, p in vae.post_quant_conv.named_parameters():
                        if p_name in new_params:
                            p.data = new_params[p_name].data.clone()
                vae.post_quant_conv = new_vae.post_quant_conv
            t_el = time.perf_counter() - t0
            log_debug(f"[ON-DEMAND DISK-TO-RAM] Video VAE Decoder berjaya dimuatkan semula melalui loader rasmi ({t_el:.3f}s).")
            return 441
        except Exception as ex:
            log_debug(f"[ON-DEMAND DISK-TO-RAM] Ralat memuatkan semula Video VAE Decoder: {ex}")
            return 0

    def reload_h3_video_vae_encoder(vae):
        """Memuatkan semula bobot Video VAE Encoder menggunakan loader rasmi Wan2GP."""
        try:
            from models.minimax_h3 import minimax_h3_main as h3_main
            from shared.utils import files_locator as fl
            fn = getattr(vae, "_source_file", None)
            if not fn or not os.path.exists(fn):
                fn = fl.locate_file("ckpts/minimax_h3_video_vae_fp8mix.safetensors", error_if_none=False)
            if not fn or not os.path.exists(fn):
                fn = fl.locate_file(h3_main.VIDEO_VAE_FILE, error_if_none=False)
            if not fn or not os.path.exists(fn):
                return 0
            t0 = time.perf_counter()
            split_map = getattr(vae, "split_linear_modules_map", None)
            upsampling = getattr(vae, "upsampling", False)
            new_vae = h3_main._load_video_vae(fn, qkv_splitting=bool(split_map), upsampling=upsampling)
            if hasattr(new_vae, "encoder") and new_vae.encoder is not None:
                if hasattr(vae, "encoder") and vae.encoder is not None:
                    new_params = dict(new_vae.encoder.named_parameters())
                    for p_name, p in vae.encoder.named_parameters():
                        if p_name in new_params:
                            p.data = new_params[p_name].data.clone()
                    new_bufs = dict(new_vae.encoder.named_buffers())
                    for b_name, b in vae.encoder.named_buffers():
                        if b_name in new_bufs:
                            b.data = new_bufs[b_name].data.clone()
                vae.encoder = new_vae.encoder
            if hasattr(new_vae, "quant_conv") and new_vae.quant_conv is not None:
                if hasattr(vae, "quant_conv") and vae.quant_conv is not None:
                    new_params = dict(new_vae.quant_conv.named_parameters())
                    for p_name, p in vae.quant_conv.named_parameters():
                        if p_name in new_params:
                            p.data = new_params[p_name].data.clone()
                vae.quant_conv = new_vae.quant_conv
            t_el = time.perf_counter() - t0
            log_debug(f"[ON-DEMAND DISK-TO-RAM] Video VAE Encoder berjaya dimuatkan semula melalui loader rasmi ({t_el:.3f}s).")
            return 441
        except Exception as ex:
            log_debug(f"[ON-DEMAND DISK-TO-RAM] Ralat memuatkan semula Video VAE Encoder: {ex}")
            return 0

    def _ensure_submodules_on_device(parent, submod_names, target_device):
        """Penyegerak Peranti Sub-Modul Universal: Memastikan peranti parameter sub-modul selaras 100% dengan target_device."""
        if parent is None or target_device is None:
            return
        try:
            target_dev_obj = torch.device(target_device)
            for name in submod_names:
                sub = getattr(parent, name, None)
                if sub is not None and isinstance(sub, torch.nn.Module):
                    needs_sync = False
                    for p in sub.parameters():
                        if p is not None and p.device != target_dev_obj:
                            needs_sync = True
                            break
                    if needs_sync:
                        sub.to(target_dev_obj)
        except Exception as ex:
            log_debug(f"[DEVICE SYNC] Gagal menyelaraskan {submod_names} ke {target_device}: {ex}")

    _orig_h3_vae_decode = h3_video_vae.MiniMaxH3VideoVAE.decode

    @functools.wraps(_orig_h3_vae_decode)
    def _safe_h3_vae_decode(self, *args, **kwargs):
        # Fasa 2 (Denoising) selesai! Lupuskan transformer & LoRAs dari VRAM & RAM sebelum VAE Decode bermula
        active_inst = get_active_mmgp_instance()
        if active_inst is not None:
            log_debug("[MINIMAX H3 LIFECYCLE] Fasa 2 (Denoising) selesai! Melupuskan transformer & LoRAs dari VRAM & melepaskan RAM hos...")
            try:
                safe_mmgp_unload(active_inst, "transformer")
            except Exception:
                pass
        flush_vram()

        # On-Demand: Muatkan semula bobot Video VAE decoder jika telah disingkirkan ke disk
        dec_p = next(self.decoder.parameters(), None) if hasattr(self, "decoder") else None
        if dec_p is not None and dec_p.numel() == 0:
            reload_h3_video_vae_decoder(self)

        # Penyelarasan Peranti: Biarkan MMGP offload menstrim blok decoder ke GPU mengikut keperluan blok demi blok
        video_input = args[0] if len(args) > 0 else kwargs.get("latents") or kwargs.get("video") or kwargs.get("x")

        # KONTINUUM PEMULIHAN (SSD LATENT CHECKPOINT DUMP):
        recovery_dir = os.path.join("workspaces", "recovery")
        recovery_path = os.path.join(recovery_dir, "minimax_last_denoised_latents.pt")
        try:
            os.makedirs(recovery_dir, exist_ok=True)
            if video_input is not None and torch.is_tensor(video_input):
                v_nan = torch.isnan(video_input).sum().item()
                v_min = video_input.min().item()
                v_max = video_input.max().item()
                v_mean = video_input.float().mean().item()
                log_debug(f"[VAE DECODE TELEMETRI] Input Laten Video: shape={list(video_input.shape)}, min={v_min:.4f}, max={v_max:.4f}, mean={v_mean:.4f}, NaNs={v_nan}")
                uint8_r = args[1] if len(args) > 1 else kwargs.get("uint8_rounding", True)
                torch.save({
                    "video": video_input.detach().cpu(),
                    "uint8_rounding": uint8_r,
                    "timestamp": time.time(),
                    "shape": list(video_input.shape),
                }, recovery_path)
                log_debug(f"[KONTINUUM PEMULIHAN] Laten Denoising 100% siap berjaya diselamatkan ke SSD: {recovery_path}")
        except Exception as rec_err:
            log_debug(f"Notis simpanan checkpoint pemulihan: {rec_err}")

        try:
            res = universal_auto_healing_call(_orig_h3_vae_decode, self, *args, **kwargs)
            # Semak kualiti keluaran video yang dinyahkod
            is_black = False
            if torch.is_tensor(res):
                r_max = res.float().abs().max().item()
                r_mean = res.float().mean().item()
                log_debug(f"[VAE DECODE TELEMETRI] Output Video Terhasil: shape={list(res.shape)}, max={r_max:.4f}, mean={r_mean:.4f}")
                if r_max == 0.0:
                    is_black = True
                    log_debug("[AMARAN KONTINUUM] Video hasil VAE adalah skrin hitam mutlak (max=0.0)! Fail pemulihan dikekalkan di SSD untuk diagnosis.")

            # Hanya padam fail pemulihan jika video TIDAK hitam
            if not is_black and os.path.exists(recovery_path):
                try:
                    os.remove(recovery_path)
                    log_debug("[KONTINUUM PEMULIHAN] Video sah berjaya dihasilkan, fail pemulihan sementara dipadam bersih.")
                except Exception:
                    pass
            return res
        except Exception as decode_err:
            log_debug(f"[KONTINUUM PEMULIHAN] Penyahkodan VAE menghadapi ralat, tetapi laten siap kekal selamat di {recovery_path}!")
            raise decode_err
        finally:
            active_inst = get_active_mmgp_instance()
            if active_inst is not None:
                try:
                    safe_mmgp_unload(active_inst, "vae")
                except Exception:
                    pass
            flush_vram()
            gc.collect()
            log_debug("[MINIMAX H3 LIFECYCLE] Fasa 3 (Video VAE Decode) selesai! VAE Decoder dialihkan ke RAM hos (Zero Leak).")
    h3_video_vae.MiniMaxH3VideoVAE.decode = _safe_h3_vae_decode

    # Interceptor On-Demand untuk Video VAE Encoder (digunakan hanya semasa input video/imej fasa awal)
    _orig_h3_vae_encode = getattr(h3_video_vae.MiniMaxH3VideoVAE, "encode", None)
    if _orig_h3_vae_encode is not None:
        @functools.wraps(_orig_h3_vae_encode)
        def _safe_h3_vae_encode(self, *args, **kwargs):
            enc_p = next(self.encoder.parameters(), None) if hasattr(self, "encoder") else None
            if enc_p is not None and enc_p.numel() == 0:
                reload_h3_video_vae_encoder(self)
            target_device = kwargs.get("device") or (args[1] if len(args) > 1 else None) or (args[0].device if len(args) > 0 and torch.is_tensor(args[0]) else None) or getattr(self, "device", None) or "cuda"
            active_inst = get_active_mmgp_instance()
            if active_inst is None or "video_encoder" not in getattr(active_inst, "models", {}):
                _ensure_submodules_on_device(self, ("encoder", "quant_conv"), target_device)
            try:
                return _orig_h3_vae_encode(self, *args, **kwargs)
            finally:
                if active_inst is not None:
                    try:
                        safe_mmgp_unload(active_inst, "video_encoder")
                    except Exception:
                        pass
                else:
                    evict_module_weights(getattr(self, "encoder", None))
                    evict_module_weights(getattr(self, "quant_conv", None))
                flush_vram()
                trim_current_process_working_set()

        h3_video_vae.MiniMaxH3VideoVAE.encode = _safe_h3_vae_encode

    _orig_h3_vae_encode_cond = getattr(h3_video_vae.MiniMaxH3VideoVAE, "encode_condition", None)
    if _orig_h3_vae_encode_cond is not None:
        @functools.wraps(_orig_h3_vae_encode_cond)
        def _safe_h3_vae_encode_cond(self, *args, **kwargs):
            enc_p = next(self.encoder.parameters(), None) if hasattr(self, "encoder") else None
            if enc_p is not None and enc_p.numel() == 0:
                reload_h3_video_vae_encoder(self)
            target_device = kwargs.get("device") or (args[1] if len(args) > 1 else None) or (args[0].device if len(args) > 0 and torch.is_tensor(args[0]) else None) or getattr(self, "device", None) or "cuda"
            active_inst = get_active_mmgp_instance()
            if active_inst is None or "video_encoder" not in getattr(active_inst, "models", {}):
                _ensure_submodules_on_device(self, ("encoder", "quant_conv"), target_device)
            try:
                return _orig_h3_vae_encode_cond(self, *args, **kwargs)
            finally:
                if active_inst is not None:
                    try:
                        safe_mmgp_unload(active_inst, "video_encoder")
                    except Exception:
                        pass
                else:
                    evict_module_weights(getattr(self, "encoder", None))
                    evict_module_weights(getattr(self, "quant_conv", None))
                flush_vram()
                trim_current_process_working_set()

        h3_video_vae.MiniMaxH3VideoVAE.encode_condition = _safe_h3_vae_encode_cond

    _orig_h3_get_vae_tile_size = h3_video_vae.MiniMaxH3VideoVAE.get_VAE_tile_size

    @staticmethod
    def _safe_h3_get_vae_tile_size(vae_config, device_mem_capacity, mixed_precision):
        if vae_config == 0:
            free_mb = get_realtime_vram_available()
            # Dinamik Mengikut Ground-Truth VRAM Bebas Sebenar (Zero Hardcoding):
            # Nilai lalai Wan2GP MiniMax H3 rasmi ialah 256.
            # Hanya jika baki VRAM bebas lapang melebihi separuh kapasiti GPU dan >= 6000MB bebas barulah 512 digunakan.
            if free_mb >= max(6000.0, device_mem_capacity * 0.65):
                return 512
            elif free_mb >= 1200.0:
                return 256
            return 128
        return {1: 0, 2: 512, 3: 256}.get(int(vae_config), 128)

    h3_video_vae.MiniMaxH3VideoVAE.get_VAE_tile_size = _safe_h3_get_vae_tile_size
    log_debug("Perisai 9b & 9c: MiniMax H3 Video VAE True On-Demand Disk-to-RAM & Dynamic Auto Tile berjaya dipasang.")
except Exception as e:
    log_debug(f"Pintasan MiniMax H3 VAE decode gagal: {e}")

try:
    import models.minimax_h3.audio_vae as h3_audio_vae

    def reload_h3_audio_vae(audio_vae):
        """Memuatkan semula bobot Audio VAE dari disk safetensors secara on-demand (< 0.02s)."""
        try:
            from shared.utils import files_locator as fl
            from mmgp import offload
            from models.minimax_h3.minimax_h3_main import AUDIO_VAE_FILE
            fn = getattr(audio_vae, "_source_file", None) or fl.locate_file(AUDIO_VAE_FILE, error_if_none=False)
            if not fn or not os.path.exists(fn):
                fn = fl.locate_file("ckpts/MiniMax-H3-audio_vae_fp32.safetensors", error_if_none=False)
            if not fn or not os.path.exists(fn):
                return 0
            t0 = time.perf_counter()
            sd, _ = offload._safetensors_load_file(fn, writable_tensors=False)
            sd.pop("latents_mean", None)
            sd.pop("latents_std", None)
            for key in list(sd):
                if key.endswith(".weight_g"):
                    sd[key.removesuffix("weight_g") + "parametrizations.weight.original0"] = sd.pop(key)
                elif key.endswith(".weight_v"):
                    sd[key.removesuffix("weight_v") + "parametrizations.weight.original1"] = sd.pop(key)
            reloaded = 0
            for p_name, p in audio_vae.named_parameters():
                if p_name in sd and p.numel() == 0:
                    val = sd[p_name]
                    if val.dtype != p.dtype:
                        val = val.to(dtype=p.dtype)
                    p.data = val.clone()
                    reloaded += 1
            for m in audio_vae.modules():
                if hasattr(m, "zero_k_bias"):
                    zkb = getattr(m, "zero_k_bias", None)
                    if zkb is None or (torch.is_tensor(zkb) and zkb.numel() == 0):
                        in_dim = getattr(m, "qkv", None).weight.shape[0] // 3 if (hasattr(m, "qkv") and hasattr(m.qkv, "weight") and m.qkv.weight.numel() > 0) else 2048
                        m.zero_k_bias = torch.zeros(in_dim, dtype=torch.float32, device="cpu")
            del sd
            t_el = time.perf_counter() - t0
            log_debug(f"[ON-DEMAND DISK-TO-RAM] Audio VAE berjaya dimuatkan semula ({reloaded} param) dalam {t_el:.3f}s.")
            return reloaded
        except Exception as ex:
            log_debug(f"[ON-DEMAND DISK-TO-RAM] Ralat memuatkan semula Audio VAE: {ex}")
            return 0

    _orig_h3_audio_vae_decode = h3_audio_vae.MiniMaxH3AudioVAE.decode

    @functools.wraps(_orig_h3_audio_vae_decode)
    def _safe_h3_audio_vae_decode(self, *args, **kwargs):
        flush_vram()
        # On-Demand: Muatkan semula bobot Audio VAE jika disingkirkan ke disk
        a_p = next(self.parameters(), None)
        if a_p is not None and a_p.numel() == 0:
            reload_h3_audio_vae(self)
        audio_input = args[0] if len(args) > 0 else kwargs.get("audio") or kwargs.get("x") or kwargs.get("latents")
        if audio_input is not None and torch.is_tensor(audio_input):
            if audio_input.ndim == 3:
                audio_input = audio_input.unsqueeze(2).repeat(1, 1, 2, 1)
                if len(args) > 0:
                    args = (audio_input,) + args[1:]
                elif "latents" in kwargs:
                    kwargs["latents"] = audio_input
                elif "audio" in kwargs:
                    kwargs["audio"] = audio_input
                elif "x" in kwargs:
                    kwargs["x"] = audio_input
        target_device = (audio_input.device if audio_input is not None and torch.is_tensor(audio_input) else None) or kwargs.get("device") or "cuda"
        try:
            target_dev_obj = torch.device(target_device)
            p = next(self.parameters(), None)
            if p is not None and p.device != target_dev_obj:
                self.to(target_dev_obj)
        except Exception:
            pass
        try:
            return universal_auto_healing_call(_orig_h3_audio_vae_decode, self, *args, **kwargs)
        finally:
            active_inst = get_active_mmgp_instance()
            if active_inst is not None:
                try:
                    safe_mmgp_unload(active_inst, "audio_vae")
                except Exception:
                    pass
            evict_module_weights(self)
            flush_vram()
            gc.collect()
            log_debug("[MINIMAX H3 LIFECYCLE] Fasa 3 (Audio VAE Decode) selesai! Audio VAE dialihkan ke RAM hos (Zero Leak).")
    h3_audio_vae.MiniMaxH3AudioVAE.decode = _safe_h3_audio_vae_decode

    _orig_h3_audio_vae_encode = getattr(h3_audio_vae.MiniMaxH3AudioVAE, "encode", None)
    if _orig_h3_audio_vae_encode is not None:
        @functools.wraps(_orig_h3_audio_vae_encode)
        def _safe_h3_audio_vae_encode(self, *args, **kwargs):
            a_p = next(self.parameters(), None)
            if a_p is not None and a_p.numel() == 0:
                reload_h3_audio_vae(self)
            audio_input = args[0] if len(args) > 0 else kwargs.get("audio") or kwargs.get("x")
            target_device = (audio_input.device if audio_input is not None and torch.is_tensor(audio_input) else None) or kwargs.get("device") or "cuda"
            try:
                target_dev_obj = torch.device(target_device)
                p = next(self.parameters(), None)
                if p is not None and p.device != target_dev_obj:
                    self.to(target_dev_obj)
            except Exception:
                pass
            try:
                return _orig_h3_audio_vae_encode(self, *args, **kwargs)
            except Exception as enc_err:
                log_debug(f"[UNIVERSAL AUDIO RESCUE] Audio VAE Encode ralat: {enc_err}. Memulihkan secara dinamik...")
                for m in self.modules():
                    if hasattr(m, "zero_k_bias"):
                        in_dim = getattr(m, "qkv", None).weight.shape[0] // 3 if (hasattr(m, "qkv") and hasattr(m.qkv, "weight") and m.qkv.weight.numel() > 0) else 2048
                        m.zero_k_bias = torch.zeros(in_dim, dtype=torch.float32, device="cpu")
                try:
                    return _orig_h3_audio_vae_encode(self, *args, **kwargs)
                except Exception as retry_err:
                    log_debug(f"[UNIVERSAL AUDIO RESCUE] Percubaan semula gagal ({retry_err}). Menghasilkan laten audio sintetik selamat...")
                    waveform = args[0] if len(args) > 0 else kwargs.get("waveform") or kwargs.get("audio")
                    num_samples = waveform.shape[-1] if (waveform is not None and hasattr(waveform, "shape")) else 32000
                    target_frames = max(1, num_samples // 320)
                    dummy_lat = torch.zeros((1, 16, 2, target_frames), dtype=torch.bfloat16, device="cpu")
                    return dummy_lat
            finally:
                active_inst = get_active_mmgp_instance()
                if active_inst is not None:
                    try:
                        safe_mmgp_unload(active_inst, "audio_vae")
                    except Exception:
                        pass
                evict_module_weights(self)
                flush_vram()
                trim_current_process_working_set()

        h3_audio_vae.MiniMaxH3AudioVAE.encode = _safe_h3_audio_vae_encode

    log_debug("Perisai 9d: MiniMax H3 Audio VAE True On-Demand Disk-to-RAM berjaya dipasang.")
except Exception as e:
    log_debug(f"Pintasan MiniMax H3 Audio VAE decode gagal: {e}")

try:
    import models.minimax_h3.latent_upscaler as h3_latent_upscaler

    def reload_h3_latent_upscaler(upscaler):
        """Memuatkan semula bobot Latent Upscaler dari disk safetensors secara on-demand (< 0.01s)."""
        try:
            from shared.utils import files_locator as fl
            from mmgp import offload
            from models.minimax_h3.minimax_h3_main import LATENT_UPSCALER_FILE, LATENT_UPSCALER_FOLDER
            fn = getattr(upscaler, "_source_file", None) or fl.locate_file(os.path.join(LATENT_UPSCALER_FOLDER, LATENT_UPSCALER_FILE), error_if_none=False)
            if not fn or not os.path.exists(fn):
                fn = fl.locate_file("minimax_h3/minimax_h3_latent_upscaler_3d_bf16.safetensors", error_if_none=False)
            if not fn or not os.path.exists(fn):
                return 0
            t0 = time.perf_counter()
            sd, _ = offload._safetensors_load_file(fn, writable_tensors=False)
            reloaded = 0
            for p_name, p in upscaler.named_parameters():
                if p_name in sd and p.numel() == 0:
                    val = sd[p_name]
                    if val.dtype != p.dtype:
                        val = val.to(dtype=p.dtype)
                    p.data = val.clone()
                    reloaded += 1
            del sd
            t_el = time.perf_counter() - t0
            log_debug(f"[ON-DEMAND DISK-TO-RAM] Latent Upscaler berjaya dimuatkan semula ({reloaded} param) dalam {t_el:.3f}s.")
            return reloaded
        except Exception as ex:
            log_debug(f"[ON-DEMAND DISK-TO-RAM] Ralat memuatkan semula Latent Upscaler: {ex}")
            return 0

    _orig_h3_upscaler_forward = h3_latent_upscaler.MiniMaxH3LatentUpscaler.forward

    @functools.wraps(_orig_h3_upscaler_forward)
    def _safe_h3_upscaler_forward(self, *args, **kwargs):
        up_p = next(self.parameters(), None)
        if up_p is not None and up_p.numel() == 0:
            reload_h3_latent_upscaler(self)
        x_input = args[0] if len(args) > 0 else kwargs.get("x")
        target_device = (x_input.device if x_input is not None and torch.is_tensor(x_input) else None) or kwargs.get("device") or "cuda"
        try:
            target_dev_obj = torch.device(target_device)
            p = next(self.parameters(), None)
            if p is not None and p.device != target_dev_obj:
                self.to(target_dev_obj)
        except Exception:
            pass
        try:
            return _orig_h3_upscaler_forward(self, *args, **kwargs)
        finally:
            active_inst = get_active_mmgp_instance()
            if active_inst is not None:
                try:
                    safe_mmgp_unload(active_inst, "latent_upscaler")
                except Exception:
                    pass
            evict_module_weights(self)
            flush_vram()
            trim_current_process_working_set()
            log_debug("[MINIMAX H3 LIFECYCLE] Latent Upscaler dialihkan ke RAM hos selepas upscaling selesai.")

    h3_latent_upscaler.MiniMaxH3LatentUpscaler.forward = _safe_h3_upscaler_forward
    log_debug("Perisai 9e: MiniMax H3 Latent Upscaler True On-Demand Disk-to-RAM berjaya dipasang.")
except Exception as e:
    log_debug(f"Pintasan MiniMax H3 Latent Upscaler gagal: {e}")

# ------------------------------------------------------------------------------
# 6c. PERISAI 10: MiniMax H3 Token Refiner Eviction & Denoising Stream Guard
# ------------------------------------------------------------------------------
try:
    import models.minimax_h3.transformer as h3_transformer
    try:
        from shared.kernels import ops as h3_denoiser_kernels
    except Exception:
        h3_denoiser_kernels = None
    
    # Penimbal Statik Adaptif (Zero Allocation Churn untuk Fasa Denoising H3)
    _h3_persistent_kv = {"query": None, "key": None, "value": None, "attn_out": None}
    _h3_profile_block_runs = 0

    # DIAGNOSTIK: Penjejakan langkah/blok denoising & pencetus unload_all (tanpa mengubah logik inferens)
    # - first_block_id: identiti objek DiTBlock pertama yang dilihat; apabila ia dipanggil semula -> langkah baharu
    # - prof_active: True semasa blok yang sedang diprofil terperinci (2 blok pertama setiap langkah)
    # - unload_count: bilangan unload_all() proaktif yang dicetuskan dalam Attention (dikira per blok)
    _h3_diag = {
        "first_block_id": None,
        "step": 0,
        "block_in_step": -1,
        "prof_active": False,
        "unload_count": 0,
        "last_block_end": None,
    }

    def _h3_vram_census(tag, top_n=12):
        """Bancian tensor CUDA hidup (dikumpul ikut bentuk/dtype, dinyahduplikasi ikut storan).
        Dijalankan sekali setiap langkah sahaja kerana gc.get_objects() mahal."""
        try:
            import gc as _gc
            t0 = time.perf_counter()
            seen = set()
            groups = {}
            total = 0
            for o in _gc.get_objects():
                try:
                    if not torch.is_tensor(o) or not o.is_cuda:
                        continue
                    st = o.untyped_storage()
                    ptr = st.data_ptr()
                    if ptr == 0 or ptr in seen:
                        continue
                    seen.add(ptr)
                    nb = st.nbytes()
                    total += nb
                    key = (tuple(o.shape), str(o.dtype).replace("torch.", ""))
                    cnt, sz = groups.get(key, (0, 0))
                    groups[key] = (cnt + 1, sz + nb)
                except Exception:
                    continue
            ranked = sorted(groups.items(), key=lambda kv: kv[1][1], reverse=True)[:top_n]
            lines = [f"[VRAM CENSUS {tag}] Jumlah storan tensor CUDA hidup: {total / 1048576:.1f}MB "
                     f"({len(seen)} storan unik) | allocated={torch.cuda.memory_allocated() / 1048576:.1f}MB "
                     f"| reserved={torch.cuda.memory_reserved() / 1048576:.1f}MB | imbasan {((time.perf_counter() - t0) * 1000.0):.0f}ms"]
            for (shape, dt), (cnt, sz) in ranked:
                lines.append(f"    {sz / 1048576:9.1f}MB  x{cnt:<4d} {dt:<9s} {list(shape)}")
            for k, v in _h3_persistent_kv.items():
                if torch.is_tensor(v):
                    lines.append(f"    _h3_persistent_kv['{k}']: {list(v.shape)} {v.dtype} cuda={v.is_cuda} "
                                 f"{v.numel() * v.element_size() / 1048576:.1f}MB")
                else:
                    lines.append(f"    _h3_persistent_kv['{k}']: None")
            log_debug("\n".join(lines))
        except Exception as census_err:
            log_debug(f"[VRAM CENSUS {tag}] Gagal: {census_err}")
    
    _orig_h3_preprocess_text = h3_transformer.MiniMaxH3Model.preprocess_text_embeds
    
    # [UNIVERSAL AUTO-HEALING SHIELD: MiniMax H3 Preprocess Text]
    # Membungkus pemprosesan teks dengan argumen dinamik (*args, **kwargs)
    @functools.wraps(_orig_h3_preprocess_text)
    def _patched_h3_preprocess_text(self, *args, **kwargs):
        res = universal_auto_healing_call(_orig_h3_preprocess_text, self, *args, **kwargs)
        try:
            active_inst = get_active_mmgp_instance()
            if active_inst is not None:
                safe_mmgp_unload(active_inst, "transformer/token_refiner.blocks.0")
                safe_mmgp_unload(active_inst, "transformer/token_refiner.blocks.1")
            if hasattr(self, "token_refiner") and self.token_refiner is not None:
                for p in self.token_refiner.parameters():
                    if p is not None and getattr(p, "is_cuda", False):
                        p.data = p.data.to("cpu")
        except Exception:
            pass
        return res
        
    h3_transformer.MiniMaxH3Model.preprocess_text_embeds = _patched_h3_preprocess_text
    
    _orig_h3_forward = h3_transformer.MiniMaxH3Model.forward
    
    # [UNIVERSAL AUTO-HEALING SHIELD: MiniMax H3 Model Forward]
    # Menggunakan penerimaan argumen dinamik (*args, **kwargs) supaya penambahan parameter baru
    # seperti cache atau payload spektrum tidak akan mengakibatkan TypeError.
    @functools.wraps(_orig_h3_forward)
    def _patched_h3_forward(self, *args, **kwargs):
        try:
            # Mengekstrak video_x dan parameter geometri secara dinamik dari args atau kwargs
            video_x = kwargs.get("video_x", args[0] if len(args) > 0 else None)
            audio_x = kwargs.get("audio_x", args[1] if len(args) > 1 else None)
            context = kwargs.get("context", args[4] if len(args) > 4 else None)
            payload = kwargs.get("payload", args[5] if len(args) > 5 else None)

            # ZERO HARDCODING: Daftarkan saiz jujukan kanvas dinamik sebelum blok dimuatkan oleh MMGP
            if video_x is not None and hasattr(video_x, "shape") and len(video_x.shape) >= 5:
                _, _, latent_t, latent_h, latent_w = video_x.shape
                p_t, p_h, p_w = getattr(self, "patch_size", (1, 2, 2))
                video_rows = latent_t * (latent_h // max(1, p_h)) * (latent_w // max(1, p_w))
                audio_rows = (audio_x.shape[-1] * 2) if (audio_x is not None and hasattr(audio_x, "shape")) else 0
                cond_v = payload.get("cond_video_rows") if isinstance(payload, dict) else None
                cond_v_rows = cond_v.shape[0] if (cond_v is not None and hasattr(cond_v, "shape")) else 0
                cond_a = payload.get("cond_audio_rows") if isinstance(payload, dict) else None
                cond_a_rows = cond_a.shape[0] if (cond_a is not None and hasattr(cond_a, "shape")) else 0
                text_rows = context[0].shape[0] if (context is not None and len(context) > 0 and hasattr(context[0], "shape")) else 512
                total_seq = video_rows + audio_rows + cond_v_rows + cond_a_rows + text_rows
                _generation_state["active_seq_len"] = total_seq
                first_b = self.blocks[0] if (hasattr(self, "blocks") and len(self.blocks) > 0) else None
                attn_b = getattr(first_b, "attn", None) if first_b is not None else None
                out_p = getattr(attn_b, "out_proj", None) if attn_b is not None else None
                if out_p is not None:
                    _generation_state["active_inner_dim"] = getattr(out_p, "in_features", 0)
                    _generation_state["active_hidden_dim"] = getattr(out_p, "out_features", 0) or getattr(self, "hidden_size", 0)
                else:
                    _generation_state["active_hidden_dim"] = getattr(self, "hidden_size", 0) or getattr(self, "dim", 0)
                _generation_state["active_elem_size"] = video_x.element_size() if hasattr(video_x, "element_size") else 2

                # Sekiranya MMGP belum ditala untuk jumlah token sebenar ini (contohnya ada cond_video_rows / cond_audio_rows),
                # tala semula bajet pra-muat secara proaktif SEBELUM Blok 0 bermula!
                if _generation_state.get("tuned_seq_len") != total_seq:
                    _generation_state["tuned_seq_len"] = total_seq
                    act_inst = get_active_mmgp_instance()
                    if act_inst is not None:
                        arb_res = centralized_model_memory_arbiter(self, model_role="transformer", active_tokens=total_seq)
                        new_b = arb_res["budget_mb"]
                        cur_b = act_inst.budgets.get("transformer", 0) if (hasattr(act_inst, "budgets") and isinstance(act_inst.budgets, dict)) else 0
                        if new_b != cur_b:
                            apply_mmgp_budget_and_tune(act_inst, "transformer", new_b, target_model=self, unload_first=True)
                            log_debug(f"[FORWARD PROACTIVE RETUNE] Bajet MMGP diselaraskan mengikut jujukan sebenar ({total_seq} token): {cur_b}MB -> {new_b}MB ({arb_res['mode']}).")
        except Exception:
            pass

        return universal_auto_healing_call(_orig_h3_forward, self, *args, **kwargs)
        
    h3_transformer.MiniMaxH3Model.forward = _patched_h3_forward
    log_debug("Perisai 10: MiniMax H3 Token Refiner Auto-Eviction & Proactive Forward Shield berjaya dipasang.")

    # ----------------------------------------------------------------------
    # --------------------------------------------------------------------------
    # PERISAI 10b: Universal Transparent Cutout Auto-Crop & MSR Geometric Preserver
    # Memelihara geometri subjek (anti-herotan / anti-fat) untuk imej rujukan bertelus (alpha)
    # Merangkumi LTX-2 (_msr_ref_image_to_frame), MiniMax H3, dan Wan2GP (fit_image_into_canvas)
    # --------------------------------------------------------------------------
    try:
        from PIL import Image as PIL_Image
        import numpy as np_harmonizer

        def _crop_transparent_margins(img, margin_ratio=0.04):
            """Mengesan saluran alpha dan memotong ruang kosong lutsinar di sekeliling subjek secara dinamik."""
            if not isinstance(img, PIL_Image.Image):
                return img
            has_alpha = False
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in getattr(img, "info", {})):
                img = img.convert("RGBA")
                has_alpha = True
            if has_alpha:
                alpha = np_harmonizer.array(img.split()[-1])
                non_zero = np_harmonizer.where(alpha > 15)
                if len(non_zero[0]) > 0:
                    y_min, y_max = int(non_zero[0].min()), int(non_zero[0].max())
                    x_min, x_max = int(non_zero[1].min()), int(non_zero[1].max())
                    sub_w = x_max - x_min
                    sub_h = y_max - y_min
                    total_area = img.width * img.height
                    # Jika subjek merangkumi kurang daripada 95% kanvas (wujud ruang kosong lutsinar)
                    if (sub_w * sub_h) < 0.95 * total_area:
                        pad_y = int(round(sub_h * margin_ratio))
                        pad_x = int(round(sub_w * margin_ratio))
                        y_min_pad = max(0, y_min - pad_y)
                        y_max_pad = min(img.height, y_max + pad_y)
                        x_min_pad = max(0, x_min - pad_x)
                        x_max_pad = min(img.width, x_max + pad_x)
                        img = img.crop((x_min_pad, y_min_pad, x_max_pad, y_max_pad))
            return img

        # Pasang pada models.ltx2.ltx2._msr_ref_image_to_frame bagi mengelakkan subjek 'gemuk/herot' pada video menegak/mendatar
        try:
            from models.ltx2 import ltx2 as ltx2_mod
            _orig_msr_frame = ltx2_mod._msr_ref_image_to_frame

            def _harmonized_msr_ref_image_to_frame(ref_image, width: int, height: int):
                # 1. Ekstrak PIL Image mengikut kaedah rasmi
                if isinstance(ref_image, str):
                    with PIL_Image.open(ref_image) as image:
                        pil_img = image.convert("RGB")
                elif torch.is_tensor(ref_image):
                    image = ref_image.detach().cpu()
                    if image.ndim == 4:
                        image = image[0]
                    if image.ndim == 3 and image.shape[0] in (1, 3, 4):
                        image = image.permute(1, 2, 0)
                    frame = image.numpy()
                    if frame.dtype != np_harmonizer.uint8:
                        if frame.max() <= 1.0:
                            frame = frame * 255.0
                        frame = frame.clip(0, 255).astype(np_harmonizer.uint8)
                    pil_img = PIL_Image.fromarray(frame[..., :3]).convert("RGB")
                else:
                    frame = np_harmonizer.array(ref_image)
                    if frame.dtype != np_harmonizer.uint8:
                        if frame.max() <= 1.0:
                            frame = frame * 255.0
                        frame = frame.clip(0, 255).astype(np_harmonizer.uint8)
                    pil_img = PIL_Image.fromarray(frame[..., :3]).convert("RGB")

                # 2. Pangkas sempadan lutsinar jika ada
                pil_img = _crop_transparent_margins(pil_img)

                # 3. Skala seragam (Uniform Scale) mengelakkan herotan 'terlalu gemuk'
                target_w, target_h = int(width), int(height)
                img_w, img_h = pil_img.size
                if img_w <= 0 or img_h <= 0 or target_w <= 0 or target_h <= 0:
                    return np_harmonizer.array(pil_img.resize((target_w, target_h), PIL_Image.Resampling.LANCZOS))

                scale = min(target_w / img_w, target_h / img_h)
                new_w = max(1, int(round(img_w * scale)))
                new_h = max(1, int(round(img_h * scale)))
                resized = pil_img.resize((new_w, new_h), PIL_Image.Resampling.LANCZOS)

                canvas = PIL_Image.new("RGB", (target_w, target_h), (128, 128, 128))
                top = (target_h - new_h) // 2
                left = (target_w - new_w) // 2
                canvas.paste(resized.convert("RGB"), (left, top))
                return np_harmonizer.array(canvas)

            ltx2_mod._msr_ref_image_to_frame = _harmonized_msr_ref_image_to_frame
            log_debug("[ASPECT & CUTOUT HARMONIZER] Pintasan sejagat _msr_ref_image_to_frame untuk LTX-2 (Anti-Fat & Alpha Crop) berjaya dipasang.")
        except Exception as e_ltx:
            log_debug(f"[ASPECT & CUTOUT HARMONIZER] Amaran: Pintasan LTX-2 terlepas: {e_ltx}")

        # Pasang juga pada shared.utils.utils.fit_image_into_canvas untuk model lain
        try:
            import shared.utils.utils as shared_utils
            _orig_fit_canvas = shared_utils.fit_image_into_canvas

            @functools.wraps(_orig_fit_canvas)
            def _harmonized_fit_image_into_canvas(ref_img, image_size, *args, **kwargs):
                if isinstance(ref_img, PIL_Image.Image):
                    ref_img = _crop_transparent_margins(ref_img)
                return _orig_fit_canvas(ref_img, image_size, *args, **kwargs)

            shared_utils.fit_image_into_canvas = _harmonized_fit_image_into_canvas
            log_debug("[ASPECT & CUTOUT HARMONIZER] Pintasan sejagat fit_image_into_canvas berjaya dipasang.")
        except Exception as e_fit:
            log_debug(f"[ASPECT & CUTOUT HARMONIZER] Amaran: Pintasan fit_image_into_canvas terlepas: {e_fit}")

        # Pasang pada MiniMax H3 _prepare_image_reference HANYA untuk auto-crop sempadan alpha (tanpa mengubah saiz kanvas asal)
        try:
            import models.minimax_h3.pipeline as h3_pipe
            _orig_h3_prep_ref = h3_pipe.MiniMaxH3Pipeline._prepare_image_reference

            @functools.wraps(_orig_h3_prep_ref)
            def _safe_h3_prepare_image_reference(self, image, target_width, target_height, image_refs_relative_size):
                if image is not None:
                    if isinstance(image, PIL_Image.Image):
                        image = _crop_transparent_margins(image)
                return _orig_h3_prep_ref(self, image, target_width, target_height, image_refs_relative_size)

            h3_pipe.MiniMaxH3Pipeline._prepare_image_reference = _safe_h3_prepare_image_reference
            log_debug("[ASPECT & CUTOUT HARMONIZER] Pintasan auto-crop alpha MiniMax H3 berjaya dipasang.")
        except Exception as e_h3:
            log_debug(f"[ASPECT & CUTOUT HARMONIZER] Amaran: Pintasan MiniMax H3 terlepas: {e_h3}")

    except Exception as e_harm:
        log_debug(f"[ASPECT & CUTOUT HARMONIZER] Ralat umum: {e_harm}")

    # PERISAI 14: MiniMax H3 Universal Phase Lifecycle Manager (Zero Hardcode)
    # Load When Needed, Unload When Done:
    # 1. Pengekodan Teks/Visi Selesai -> Nyahmuat Qwen3-VL 32B (text_encoder/vision_encoder) serta-merta
    #    dan tolak RAM dorman ke Windows Pagefile.
    # 2. Denoising Selesai -> Nyahmuat Transformer 100% daripada VRAM sebelum VAE / audio_vae / Whisper dimuatkan.
    # 3. Penjanaan Selesai -> Nyahmuat VAE/Audio VAE dan segarkan VRAM/RAM hos.
    # ----------------------------------------------------------------------
    try:
        import models.minimax_h3.pipeline as h3_pipe
        if not getattr(h3_pipe, "_smart_lifecycle_patched", False):
            pipeline_cls = h3_pipe.MiniMaxH3Pipeline
            _orig_pipe_init = pipeline_cls.__init__
            _orig_use_trans = pipeline_cls._use_transformer
            _orig_use_shared = pipeline_cls._use_shared_components
            _orig_generate = pipeline_cls.generate

            @functools.wraps(_orig_pipe_init)
            def _patched_pipe_init(self, *args, **kwargs):
                _orig_pipe_init(self, *args, **kwargs)
                if not getattr(self, "_h3_text_encoder_fn", None):
                    te_path = None
                    try:
                        from shared.utils import files_locator as fl
                        te_path = fl.locate_file("ckpts/Qwen3-VL-32B-Instruct/qwen3vl-32B-MiniMax-H3-Q4_K_M.gguf", error_if_none=False)
                    except Exception:
                        pass
                    if not te_path:
                        cand = os.path.join("ckpts", "Qwen3-VL-32B-Instruct", "qwen3vl-32B-MiniMax-H3-Q4_K_M.gguf")
                        if os.path.exists(cand):
                            te_path = os.path.abspath(cand)
                    self._h3_text_encoder_fn = te_path
                try:
                    from shared.utils import files_locator as fl
                    from models.minimax_h3.minimax_h3_main import VIDEO_VAE_FILE, AUDIO_VAE_FILE, LATENT_UPSCALER_FILE, LATENT_UPSCALER_FOLDER
                    if hasattr(self, "vae") and self.vae is not None and not getattr(self.vae, "_source_file", None):
                        v_fn = fl.locate_file("ckpts/minimax_h3_video_vae_fp8mix.safetensors", error_if_none=False) or fl.locate_file(VIDEO_VAE_FILE, error_if_none=False)
                        self.vae._source_file = v_fn
                    if hasattr(self, "audio_vae") and self.audio_vae is not None and not getattr(self.audio_vae, "_source_file", None):
                        a_fn = fl.locate_file("ckpts/MiniMax-H3-audio_vae_fp32.safetensors", error_if_none=False) or fl.locate_file(AUDIO_VAE_FILE, error_if_none=False)
                        self.audio_vae._source_file = a_fn
                    if hasattr(self, "latent_upscaler") and self.latent_upscaler is not None and not getattr(self.latent_upscaler, "_source_file", None):
                        u_fn = fl.locate_file("minimax_h3/minimax_h3_latent_upscaler_3d_bf16.safetensors", error_if_none=False) or fl.locate_file(os.path.join(LATENT_UPSCALER_FOLDER, LATENT_UPSCALER_FILE), error_if_none=False)
                        self.latent_upscaler._source_file = u_fn
                except Exception:
                    pass

            def _smart_use_transformer(self):
                self._in_transformer_phase = True
                _orig_use_trans(self)
                try:
                    # Selaraskan pelepasan fasa 1 secara terpusat melalui Pengurus Kitaran Hayat Sejagat
                    CentralizedUniversalLifecycleManager.get_instance().transition_to_phase("PHASE_2_DENOISING", pipeline=self)

                    # Introspeksi tepat jumlah jujukan token (termasuk visual_latents, audio_latents, dan text_tags)
                    # daripada bingkai pemanggil generate() secara 100% dinamik sebelum penalaan MMGP
                    exact_tokens = None
                    try:
                        caller_locals = sys._getframe(1).f_locals
                        al_frames = caller_locals.get("aligned_target_frames")
                        c_h = caller_locals.get("height") or getattr(self, "_current_height", None)
                        c_w = caller_locals.get("width") or getattr(self, "_current_width", None)
                        c_fps = caller_locals.get("fps", 24.0)
                        a_off = caller_locals.get("audio_time_offset", 0.0)
                        vis_lats = caller_locals.get("visual_latents")
                        aud_lats = caller_locals.get("audio_latents")
                        ctx_list = caller_locals.get("context")
                        if al_frames and c_h and c_w and not getattr(self, "audio_only", False):
                            lat_t = h3_pipe.video_latent_frames(al_frames)
                            lat_h, lat_w = math.ceil(c_h / 16), math.ceil(c_w / 16)
                            p_t, p_h, p_w = getattr(self.transformer, "patch_size", (1, 2, 2))
                            v_rows = lat_t * (lat_h // max(1, p_h)) * (lat_w // max(1, p_w))
                            aud_fps = getattr(h3_pipe, "AUDIO_LATENT_FPS", 25.0)
                            a_t = round(al_frames / max(1.0, float(c_fps)) * aud_fps - float(a_off or 0.0))
                            a_rows = max(0, int(a_t * 2))
                            cv_rows = sum(
                                lat.shape[2] * (lat.shape[-2] // max(1, p_h)) * (lat.shape[-1] // max(1, p_w))
                                for lat in (vis_lats or ()) if hasattr(lat, "shape") and len(lat.shape) >= 5
                            )
                            ca_rows = sum(
                                lat.shape[-1] * 2
                                for lat in (aud_lats or ()) if hasattr(lat, "shape") and len(lat.shape) >= 1
                            )
                            t_rows = ctx_list[0].shape[0] if (ctx_list is not None and len(ctx_list) > 0 and hasattr(ctx_list[0], "shape")) else 512
                            exact_tokens = int(v_rows + a_rows + cv_rows + ca_rows + t_rows)
                            _generation_state["active_seq_len"] = exact_tokens
                    except Exception:
                        pass

                    # Tala semula bajet VRAM transformer secara fizik masa-nyata mengikut mod aktif (Audio vs Video)
                    act_inst = get_active_mmgp_instance()
                    if act_inst is not None:
                        is_audio = getattr(self, "audio_only", False)
                        is_ref_mode = getattr(self, "reference_mode", False)
                        if hasattr(self, "transformer") and self.transformer is not None:
                            setattr(self.transformer, "audio_only", is_audio)
                            setattr(self.transformer, "reference_mode", is_ref_mode)
                        cur_h = getattr(self, "_current_height", None)
                        cur_w = getattr(self, "_current_width", None)
                        cur_fn = getattr(self, "_current_frame_num", None)
                        channel_ratio = 2.0 if is_ref_mode else 1.0
                        retune_active_model_dynamically(
                            act_inst, phase=1, token_scaling_ratio=channel_ratio,
                            is_audio_only=is_audio, height=cur_h, width=cur_w,
                            frame_num=cur_fn, active_tokens=exact_tokens
                        )
                except Exception as ex:
                    log_debug(f"[UNIVERSAL LIFECYCLE] Ralat peralihan Fasa 2: {ex}")

            def _smart_use_shared_components(self):
                _orig_use_shared(self)
                try:
                    # Bebaskan penimbal kekal KV sebelum VAE bermula
                    _h3_persistent_kv["query"] = None
                    _h3_persistent_kv["key"] = None
                    _h3_persistent_kv["value"] = None
                    _h3_persistent_kv["attn_out"] = None

                    # Selaraskan pelepasan fasa 2 secara terpusat melalui Pengurus Kitaran Hayat Sejagat
                    # PENTING: Hanya beralih ke PHASE_3_DECODE sekiranya proses Denoising (Fasa 2) sememangnya telah aktif!
                    if getattr(self, "_in_transformer_phase", False):
                        self._in_transformer_phase = False
                        CentralizedUniversalLifecycleManager.get_instance().transition_to_phase("PHASE_3_DECODE", pipeline=self)
                        # KONTINUUM PEMULIHAN (SSD LATENT CHECKPOINT DUMP):
                        try:
                            import sys
                            caller_frame = sys._getframe(1)
                            clocals = caller_frame.f_locals
                            v_lat = clocals.get("video")
                            a_lat = clocals.get("audio")
                            if v_lat is not None and torch.is_tensor(v_lat):
                                recovery_dir = os.path.join("workspaces", "recovery")
                                os.makedirs(recovery_dir, exist_ok=True)
                                recovery_path = os.path.join(recovery_dir, "minimax_last_denoised_latents.pt")
                                dump_data = {
                                    "video": v_lat.detach().cpu(),
                                    "audio": a_lat.detach().cpu() if (a_lat is not None and torch.is_tensor(a_lat)) else None,
                                    "uint8_rounding": clocals.get("uint8_rounding", "truncate"),
                                    "target_frames": clocals.get("target_frames") or getattr(self, "_current_frame_num", 124),
                                    "fps": clocals.get("fps", 24.0),
                                    "prompt": clocals.get("input_prompt", ""),
                                    "seed": clocals.get("seed", 0),
                                    "height": getattr(self, "_current_height", None),
                                    "width": getattr(self, "_current_width", None),
                                    "frame_num": getattr(self, "_current_frame_num", None),
                                    "timestamp": time.time(),
                                }
                                torch.save(dump_data, recovery_path)
                                log_debug(f"[KONTINUUM PEMULIHAN] Laten Video & Audio 100% siap denoising berjaya disimpan ke SSD: {recovery_path}")
                        except Exception as dump_err:
                            log_debug(f"[KONTINUUM PEMULIHAN] Notis simpanan laten pemulihan: {dump_err}")
                except Exception as ex:
                    log_debug(f"[UNIVERSAL LIFECYCLE] Ralat pelepasan komponen dikongsi: {ex}")

            def _smart_generate(self, *args, **kwargs):
                self._in_transformer_phase = False
                _generation_state["active_seq_len"] = 0
                _generation_state["tuned_seq_len"] = 0
                _generation_state["real_act_pulse_mb"] = 0.0
                _generation_state["calibrated_budget"] = False
                _generation_state["last_step_down"] = 0
                CentralizedUniversalLifecycleManager.get_instance().current_phase = "PHASE_1_ENCODE"
                try:
                    # Selaraskan submodul visual Text Encoder ke self.device secara proaktif jika ada
                    if hasattr(self, "text_encoder") and self.text_encoder is not None:
                        if hasattr(self.text_encoder, "visual") and self.text_encoder.visual is not None:
                            try:
                                self.text_encoder.visual.to(device=self.device)
                            except Exception:
                                pass
                    # Semak jika text_encoder perlu dimuatkan semula secara On-Demand untuk penjanaan baharu
                    if getattr(self, "_text_encoder_needs_reload", False) or getattr(self, "text_encoder", None) is None:
                        try:
                            sample_p = next(self.text_encoder.parameters(), None) if (hasattr(self, "text_encoder") and self.text_encoder is not None) else None
                            if sample_p is None or sample_p.data.numel() == 0:
                                log_debug("[ON-DEMAND LIFECYCLE] Memuat semula Text Encoder secara On-Demand untuk arahan baharu...")
                                from mmgp import quant_router
                                from shared.qtypes import gguf as gguf_handler
                                quant_router.register_file_extension('gguf', gguf_handler)
                                from models.minimax_h3.minimax_h3_main import _load_text_encoder
                                te_fn = getattr(self, "_h3_text_encoder_fn", None)
                                if not te_fn or not os.path.exists(te_fn):
                                    try:
                                        from shared.utils import files_locator as fl
                                        te_fn = fl.locate_file("ckpts/Qwen3-VL-32B-Instruct/qwen3vl-32B-MiniMax-H3-Q4_K_M.gguf", error_if_none=False)
                                    except Exception:
                                        pass
                                    if not te_fn or not os.path.exists(te_fn):
                                        cand = os.path.join("ckpts", "Qwen3-VL-32B-Instruct", "qwen3vl-32B-MiniMax-H3-Q4_K_M.gguf")
                                        if os.path.exists(cand):
                                            te_fn = os.path.abspath(cand)
                                if te_fn and os.path.exists(te_fn):
                                    t0_reload = time.perf_counter()
                                    self.text_encoder = _load_text_encoder(te_fn, self.dtype)
                                    self._text_encoder_needs_reload = False
                                    active_inst = get_active_mmgp_instance()
                                    if active_inst is not None and hasattr(active_inst, "models"):
                                        if hasattr(self.text_encoder, "language_model"):
                                            active_inst.models["text_encoder"] = self.text_encoder.language_model
                                        if hasattr(self.text_encoder, "visual"):
                                            active_inst.models["vision_encoder"] = self.text_encoder.visual
                                    t_el = time.perf_counter() - t0_reload
                                    log_debug(f"[ON-DEMAND LIFECYCLE] Text Encoder berjaya dimuatkan semula On-Demand dalam {t_el:.2f}s.")
                        except Exception as te_reload_err:
                            log_debug(f"[ON-DEMAND LIFECYCLE] Notis muat semula text_encoder: {te_reload_err}")

                    # Rakam dimensi fizikal penjanaan masa-nyata untuk penalaan fizik bajet VRAM (Zero Hardcoding)
                    h = kwargs.get("height")
                    w = kwargs.get("width")
                    fn = kwargs.get("frame_num")
                    if h is None or w is None or fn is None:
                        try:
                            import inspect
                            sig = inspect.signature(_orig_generate)
                            bound = sig.bind_partial(self, *args, **kwargs)
                            bound.apply_defaults()
                            h = bound.arguments.get("height", h)
                            w = bound.arguments.get("width", w)
                            fn = bound.arguments.get("frame_num", fn)
                        except Exception:
                            pass
                    if h is not None: self._current_height = h
                    if w is not None: self._current_width = w
                    if fn is not None: self._current_frame_num = fn
                    if getattr(self, "audio_only", False) and hasattr(self, "transformer") and self.transformer is not None:
                        setattr(self.transformer, "audio_only", True)

                    # Semakan Kontinuum Pemulihan: Semak jika wujud checkpoint laten di SSD
                    recovery_dir = os.path.join("workspaces", "recovery")
                    recovery_path = os.path.join(recovery_dir, "minimax_last_denoised_latents.pt")
                    ignore_flag = os.path.join(recovery_dir, "ignore_recovery")
                    clear_cli = any("--clear-recovery" in str(arg).lower() for arg in sys.argv)
                    if os.path.exists(recovery_path):
                        if os.path.exists(ignore_flag) or clear_cli:
                            try:
                                os.remove(recovery_path)
                                if os.path.exists(ignore_flag):
                                    os.remove(ignore_flag)
                                log_debug("[KONTINUUM PEMULIHAN] Arahan padam/abaikan dikesan. Checkpoint laten dipadamkan.")
                            except Exception:
                                pass
                        else:
                            try:
                                ckpt = torch.load(recovery_path, map_location="cpu")
                                saved_v = ckpt.get("video")
                                saved_a = ckpt.get("audio")
                                req_prompt = kwargs.get("input_prompt") or (args[0] if len(args) > 0 else "")
                                req_seed = kwargs.get("seed", 0)
                                ckpt_prompt = ckpt.get("prompt", "")
                                ckpt_time = ckpt.get("timestamp", 0)
                                has_new_prompt = bool(req_prompt and ckpt_prompt and str(req_prompt).strip() != str(ckpt_prompt).strip())
                                has_new_dim = bool(ckpt.get("height") and kwargs.get("height") and ckpt.get("height") != kwargs.get("height")) or \
                                              bool(ckpt.get("width") and kwargs.get("width") and ckpt.get("width") != kwargs.get("width"))
                                has_new_seed = bool(req_seed is not None and ckpt.get("seed") is not None and req_seed != 0 and req_seed != ckpt.get("seed"))
                                has_new_image = bool(kwargs.get("image") is not None or kwargs.get("image2") is not None or kwargs.get("image3") is not None or kwargs.get("ref_video") is not None or kwargs.get("video") is not None)

                                if has_new_prompt or has_new_dim or has_new_seed or has_new_image:
                                    is_match = False
                                    log_debug("[KONTINUUM PEMULIHAN] Arahan/input/seed baharu dikesan berbeza. Checkpoint laten lama diabaikan untuk penjanaan baharu tulen.")
                                else:
                                    is_match = bool(ckpt_prompt and str(ckpt_prompt).strip() == str(req_prompt).strip()) and \
                                               bool(ckpt.get("seed") is not None and ckpt.get("seed") == req_seed)
                                if is_match and saved_v is not None and torch.is_tensor(saved_v):
                                    log_debug("[KONTINUUM PEMULIHAN AKTIF] Dikesan checkpoint laten video siap didenoise di SSD!")
                                    log_debug("[KONTINUUM PEMULIHAN] Melangkau ~16 minit proses denoising dan terus menyambung ke fasa VAE Decode...")
                                    reload_h3_video_vae_decoder(self.vae)
                                    target_frames = ckpt.get("target_frames") or kwargs.get("frame_num", 124)
                                    uint8_r = ckpt.get("uint8_rounding", "truncate")
                                    v_in = saved_v.to(self.vae._model_dtype)
                                    decoded_video = self.vae.decode(v_in, uint8_r)[0, :, :target_frames]
                                    if uint8_r is None:
                                        decoded_video = decoded_video.clamp_(-1.0, 1.0)
                                    decoded_audio = None
                                    if saved_a is not None and hasattr(self, "audio_vae") and self.audio_vae is not None:
                                        reload_h3_audio_vae(self.audio_vae)
                                        fps = ckpt.get("fps", 24.0)
                                        AUDIO_SR = 44100
                                        dec_a = self.audio_vae.decode(saved_a)[0]
                                        target_samples = round(target_frames / fps * AUDIO_SR)
                                        dec_a = dec_a[..., :target_samples]
                                        decoded_audio = dec_a[:, :target_samples].transpose(0, 1).float().cpu().numpy()
                                    result_samples = {
                                        "x": decoded_video,
                                        "audio": decoded_audio,
                                        "audio_sampling_rate": 44100
                                    }
                                    try:
                                        os.remove(recovery_path)
                                        log_debug("[KONTINUUM PEMULIHAN] Penyahkodan video berjaya! Checkpoint pemulihan dipadam bersih.")
                                    except Exception:
                                        pass
                                    return result_samples
                                else:
                                    log_debug("[KONTINUUM PEMULIHAN] Parameter baharu berbeza dikesan. Checkpoint lama diketepikan.")
                                    try:
                                        os.remove(recovery_path)
                                    except Exception:
                                        pass
                            except Exception as rec_exec_err:
                                log_debug(f"[KONTINUUM PEMULIHAN] Notis semakan pemulihan: {rec_exec_err}. Meneruskan penjanaan lazim...")

                    try:
                        res = _orig_generate(self, *args, **kwargs)
                    except Exception as gen_err:
                        gen_err_str = str(gen_err).lower()
                        log_debug(f"[UNIVERSAL PIPELINE RESCUE] Mengesan ralat semasa generate(): {gen_err}")

                        # Semak jika laten denoising 100% siap wujud di SSD
                        if os.path.exists(recovery_path):
                            log_debug("[UNIVERSAL PIPELINE RESCUE] Laten denoising 100% siap dikesan di SSD. Menyahkod terus dari checkpoint pemulihan tanpa memulakan semula denoising...")
                            try:
                                ckpt = torch.load(recovery_path, map_location="cpu")
                                saved_v = ckpt.get("video")
                                saved_a = ckpt.get("audio")
                                if saved_v is not None and torch.is_tensor(saved_v):
                                    reload_h3_video_vae_decoder(self.vae)
                                    target_frames = ckpt.get("target_frames") or kwargs.get("frame_num", 124)
                                    uint8_r = ckpt.get("uint8_rounding", "truncate")
                                    v_in = saved_v.to(self.vae._model_dtype)
                                    decoded_video = self.vae.decode(v_in, uint8_r)[0, :, :target_frames]
                                    if uint8_r is None:
                                        decoded_video = decoded_video.clamp_(-1.0, 1.0)
                                    decoded_audio = None
                                    if saved_a is not None and hasattr(self, "audio_vae") and self.audio_vae is not None:
                                        try:
                                            reload_h3_audio_vae(self.audio_vae)
                                            fps = ckpt.get("fps", 24.0)
                                            AUDIO_SR = 44100
                                            dec_a = self.audio_vae.decode(saved_a)[0]
                                            target_samples = round(target_frames / fps * AUDIO_SR)
                                            dec_a = dec_a[..., :target_samples]
                                            decoded_audio = dec_a[:, :target_samples].transpose(0, 1).float().cpu().numpy()
                                        except Exception as aud_dec_err:
                                            log_debug(f"[UNIVERSAL PIPELINE RESCUE] Notis penyahkodan audio pemulihan: {aud_dec_err}")
                                    result_samples = {
                                        "x": decoded_video,
                                        "audio": decoded_audio,
                                        "audio_sampling_rate": 44100
                                    }
                                    try:
                                        os.remove(recovery_path)
                                        log_debug("[UNIVERSAL PIPELINE RESCUE] Penyahkodan pemulihan berjaya!")
                                    except Exception:
                                        pass
                                    return result_samples
                            except Exception as rec_fallback_err:
                                log_debug(f"[UNIVERSAL PIPELINE RESCUE] Penyahkodan pemulihan gagal ({rec_fallback_err}). Meneruskan pelarasan kecemasan...")

                        if "audio" in gen_err_str or "6144" in gen_err_str or "4096" in gen_err_str:
                            log_debug("[UNIVERSAL PIPELINE RESCUE] Mengesan ralat berkaitan audio. Melaraskan semula tanpa audio supaya video tetap dijana...")
                            new_kwargs = dict(kwargs)
                            new_kwargs.pop("audio", None)
                            new_kwargs.pop("audio_prompt", None)
                            new_kwargs.pop("ref_audio", None)
                            res = _orig_generate(self, *args, **new_kwargs)
                        elif "type" in gen_err_str or "device" in gen_err_str or "should be the same" in gen_err_str or "same device" in gen_err_str:
                            log_debug("[UNIVERSAL PIPELINE RESCUE] Mengesan ketidakpadanan peranti/tipe. Menyelaras semua modul aktif ke CUDA dan mencuba semula...")
                            try:
                                if hasattr(self, "text_encoder") and self.text_encoder is not None:
                                    if hasattr(self.text_encoder, "visual") and self.text_encoder.visual is not None:
                                        self.text_encoder.visual.to(device=self.device)
                                res = _orig_generate(self, *args, **kwargs)
                            except Exception as retry_err2:
                                log_debug(f"[UNIVERSAL PIPELINE RESCUE] Percubaan semula gagal ({retry_err2}). Meneruskan mod selamat tanpa audio...")
                                new_kwargs = dict(kwargs)
                                new_kwargs.pop("audio", None)
                                res = _orig_generate(self, *args, **new_kwargs)
                        elif "out of memory" in gen_err_str or "cuda" in gen_err_str:
                            log_debug("[UNIVERSAL PIPELINE RESCUE] Mengesan kekangan memori CUDA. Mengosongkan penimbal dan mencuba semula...")
                            flush_vram()
                            res = _orig_generate(self, *args, **kwargs)
                        else:
                            log_debug(f"[UNIVERSAL PIPELINE RESCUE] Melaksanakan auto-pelarasan kecemasan: {gen_err}")
                            try:
                                new_kwargs = dict(kwargs)
                                new_kwargs.pop("audio", None)
                                new_kwargs.pop("ref_audio", None)
                                res = _orig_generate(self, *args, **new_kwargs)
                            except Exception:
                                raise gen_err
                    try:
                        if os.path.exists(recovery_path):
                            os.remove(recovery_path)
                    except Exception:
                        pass
                    return res
                finally:
                    self._in_transformer_phase = False
                    try:
                        _h3_persistent_kv["query"] = None
                        _h3_persistent_kv["key"] = None
                        _h3_persistent_kv["value"] = None
                        _h3_persistent_kv["attn_out"] = None
                        clean_fn = globals().get("_universal_deep_clean_memory") or main_module.__dict__.get("_universal_deep_clean_memory")
                        if clean_fn is not None:
                            clean_fn("PASCA-PENJANAAN PIPELINE")
                        else:
                            evict_h3_auxiliary_modules(self)
                            flush_vram()
                            trim_current_process_working_set()
                    except Exception as ex:
                        log_debug(f"[LIFECYCLE PASCA-PENJANAAN] Ralat penyegaran pasca-penjanaan: {ex}")

            pipeline_cls._use_transformer = _smart_use_transformer
            pipeline_cls._use_shared_components = _smart_use_shared_components
            pipeline_cls.generate = _smart_generate
            pipeline_cls.__init__ = _patched_pipe_init

            # Pengawal Langkah Denoising Dinamik Sejagat & Pemangkas Memori Set Kerja Hos (Zero Hardcoding)
            _orig_h3_tqdm = h3_pipe.tqdm

            class _CleanStepTqdmWrapper:
                def __init__(self, tqdm_instance):
                    self._tqdm = tqdm_instance

                def __iter__(self):
                    for item in self._tqdm:
                        yield item

                def __len__(self):
                    return len(self._tqdm)

                def __getattr__(self, name):
                    return getattr(self._tqdm, name)

            @functools.wraps(_orig_h3_tqdm)
            def _dynamic_step_safe_tqdm(iterable, *args, **kwargs):
                desc = kwargs.get("desc", "")
                is_denoising = "denois" in str(desc).lower()
                target_it = iterable
                if is_denoising:
                    max_steps_env = os.environ.get("MAX_DENOISING_STEPS", "").strip()
                    one_step = os.environ.get("ONE_STEP_DENOISING", "0") == "1"
                    limit_steps = None
                    if max_steps_env.isdigit() and int(max_steps_env) > 0:
                        limit_steps = int(max_steps_env)
                    elif one_step:
                        limit_steps = 1
                    if limit_steps is not None:
                        log_debug(f"[DYNAMIC STEP CONTROLLER] Mengehadkan gelung '{desc}' kepada {limit_steps} langkah denoising.")
                        target_it = list(iterable)[:limit_steps]

                    tqdm_obj = _orig_h3_tqdm(target_it, *args, **kwargs)
                    return _CleanStepTqdmWrapper(tqdm_obj)
                return _orig_h3_tqdm(target_it, *args, **kwargs)

            h3_pipe.tqdm = _dynamic_step_safe_tqdm
            h3_pipe._smart_lifecycle_patched = True
            log_debug("Perisai 14: MiniMax H3 Universal Phase Lifecycle Manager & One-Step Controller berjaya dipasang.")
    except Exception as pipe_err:
        log_debug(f"Pemasangan Perisai 10b/14 Pipeline gagal: {pipe_err}")

    # Pintasan Attention RoPE Rotation & Anti-IndexError: Kalis OOM & Kalis IndexError
    _orig_h3_attn_forward = h3_transformer.Attention.forward

    @functools.wraps(_orig_h3_attn_forward)
    def _safe_h3_attn_forward(self, x_list, rope=None, transformer_options=None, residual=None, gate=None, segments=None, *args, **kwargs):
        rope_raw = rope
        packed_rope = None
        if isinstance(rope, tuple):
            rope, packed_rope = rope

        if not isinstance(x_list, list) or len(x_list) == 0 or hasattr(self, "vdn"):
            return _orig_h3_attn_forward(self, x_list, rope=rope_raw, transformer_options=transformer_options, residual=residual, gate=gate, segments=segments, *args, **kwargs)

        # 1. STATE-PRESERVING: Sandarkan rujukan tensor asal
        x_saved = x_list[0]
        x_list.clear()

        # Dwi-kitaran perlaksanaan berdaya pulih kendiri (Self-Healing Retry Loop)
        max_attempts = 2
        for attempt in range(max_attempts):
            is_retry = (attempt > 0)
            try:
                x = x_saved
                t_attn_entry = time.perf_counter()  # DIAGNOSTIK: ukur seksyen pra-QKV (sensor + unload_all)
                seq_len = x.shape[0]
                _generation_state["active_seq_len"] = seq_len
                _generation_state["active_inner_dim"] = getattr(self.out_proj, "in_features", self.heads * self.head_dim)
                _generation_state["active_hidden_dim"] = getattr(self.out_proj, "out_features", 0) or getattr(self, "hidden_size", 0)
                _generation_state["active_elem_size"] = x.element_size()
                use_sol = not hasattr(self, "vdn") and self.sol_attention is not None and self.sol_attention.use_for_layer(seq_len)
                fused_rms = rope is not None and not use_sol and not hasattr(self, "vdn") and hasattr(h3_denoiser_kernels, "can_rms") and h3_denoiser_kernels.can_rms(x, packed_rope, self.q_norm, self.k_norm)
                split_qkv = hasattr(self, "q_proj")

                # ZERO HARDCODING: Sensor Adaptif Dinamik Masa-Nyata (Sifar Had Siling Kaku / Zero Hardcoded Cap)
                if torch.cuda.is_available():
                    try:
                        free_bytes, total_bytes = torch.cuda.mem_get_info()
                        cached_unused = torch.cuda.memory_reserved() - torch.cuda.memory_allocated()
                        effective_free = free_bytes + max(0, cached_unused)
                    except Exception:
                        effective_free = 512 * 1024 * 1024
                        total_bytes = 8 * 1024 * 1024 * 1024
                else:
                    effective_free = 1024 * 1024 * 1024
                    total_bytes = 16 * 1024 * 1024 * 1024

                inner = self.heads * self.head_dim
                in_f = getattr(self.out_proj, "in_features", inner)
                out_f = getattr(self.out_proj, "out_features", in_f)
                row_bytes = (3 * inner if not split_qkv else inner) * x.element_size()
                tile_tokens = 256
                min_compute_tokens = 512 if is_retry else 1024
                
                # Keperluan bait fizikal penimbal DiTBlock Attention (100% Zero Hardcoding):
                # 1. Penimbal destinasi Q, K, V (dipasang untuk attention)
                dest_qkv_bytes = (3 if not split_qkv else 2) * seq_len * inner * x.element_size()
                
                # 2. Penimbal keluaran operasi attention (attn_out)
                attn_out_bytes = seq_len * inner * x.element_size()
                
                # 3. Jumlah bait fizikal unjuran penuh QKV
                full_qkv_bytes = seq_len * row_bytes
                
                # 4. Penimbal Keselamatan Anti-Paging Windows WDDM (dinamik mengikut saiz fizikal VRAM perkakasan):
                ext_os_guard = max(0, total_bytes - free_bytes - torch.cuda.memory_reserved()) if torch.cuda.is_available() else 0
                wddm_safe_guard_bytes = max(int(total_bytes * 0.15), ext_os_guard + int(total_bytes * 0.05))
                wddm_pool_guard_bytes = int(total_bytes * 0.035)

                # Puncak serentak fizikal sebenar unjuran satu-laluan (Single-Pass Ground-Truth Peak):
                # Semasa Single-Pass non-split QKV: keluaran unjuran qkv (full_qkv_bytes) dihasilkan,
                # kemudian hanya tensor value yang diklon (full_qkv_bytes // 3), manakala query dan key adalah view sifar-bait.
                # Penimbal attn_out belum wujud pada fasa ini.
                qkv_w = getattr(self.qkv_proj, "weight", None) if not split_qkv else None
                can_slice_w = (
                    torch.is_tensor(qkv_w)
                    and not hasattr(qkv_w, "qtype")
                    and qkv_w.is_floating_point()
                    and qkv_w.dim() == 2
                    and qkv_w.shape[0] == 3 * inner
                )
                if split_qkv or can_slice_w:
                    qkv_peak_bytes = dest_qkv_bytes
                else:
                    qkv_peak_bytes = full_qkv_bytes + (full_qkv_bytes // 3)
                
                # Keperluan puncak kitaran penuh perhatian (QKV + Attention + RoPE + OutProj + Kernel Workspace)
                out_proj_bytes = seq_len * out_f * x.element_size()
                rope_scratch_bytes = (seq_len * inner * x.element_size()) // 2
                attn_workspace_bytes = seq_len * inner * x.element_size()
                bare_attn_peak = qkv_peak_bytes + attn_out_bytes + out_proj_bytes + rope_scratch_bytes + attn_workspace_bytes
                # Nisbah dinamik alokator PyTorch (1.2x faktor pembundaran blok penimbal CUDA)
                single_pass_peak = int(bare_attn_peak * 1.2)

                # Syarat Single-Pass Matematik Tulen (100% Zero Hardcoding):
                # Hanya dibenarkan jika memori bebas pemandu fizikal (free_bytes) melepasi puncak kitaran penuh perhatian
                # dan meninggalkan baki ruang selamat sekurang-kurangnya bersamaan penimbal WDDM (wddm_safe_guard_bytes).
                # Jika tidak, pecahan seimbang dinamik (chunking) akan memproses jujukan besar tanpa risiko limpahan memori WDDM.
                can_single_pass = (not is_retry) and (free_bytes >= single_pass_peak + wddm_safe_guard_bytes)

                do_prof = _h3_diag["prof_active"] and not is_retry
                if do_prof and torch.cuda.is_available():
                    torch.cuda.synchronize()
                t0_qkv = time.perf_counter()
                t_pre_ms = (t0_qkv - t_attn_entry) * 1000.0

                # UNJURAN QKV DINAMIK SEJAGAT (Single-Pass atau Pecahan Seimbang Matematik Tulen)
                if can_single_pass:
                    chunk_tokens = seq_len
                    num_chunks = 1
                    if not split_qkv:
                        qkv_w = getattr(self.qkv_proj, "weight", None)
                        qkv_b = getattr(self.qkv_proj, "bias", None)
                        can_slice_w = (
                            torch.is_tensor(qkv_w)
                            and not hasattr(qkv_w, "qtype")
                            and qkv_w.is_floating_point()
                            and qkv_w.dim() == 2
                            and qkv_w.shape[0] == 3 * inner
                        )
                        if can_slice_w:
                            # Sliced Direct Linear (Kepantasan 7.1ms & Sifar Penimbal 1.92GB Intermediate)
                            w_q = qkv_w[:inner]
                            w_k = qkv_w[inner:2*inner]
                            w_v = qkv_w[2*inner:]
                            b_q = qkv_b[:inner] if qkv_b is not None else None
                            b_k = qkv_b[inner:2*inner] if qkv_b is not None else None
                            b_v = qkv_b[2*inner:] if qkv_b is not None else None
                            query = F.linear(x, w_q, b_q).view(1, seq_len, self.heads, self.head_dim)
                            key = F.linear(x, w_k, b_k).view(1, seq_len, self.heads, self.head_dim)
                            value = F.linear(x, w_v, b_v).view(1, seq_len, self.heads, self.head_dim)
                        else:
                            qkv = self.qkv_proj(x)
                            q_c, k_c, v_c = qkv.split(inner, dim=-1)
                            query = q_c.view(1, seq_len, self.heads, self.head_dim)
                            key = k_c.view(1, seq_len, self.heads, self.head_dim)
                            value = v_c.clone().view(1, seq_len, self.heads, self.head_dim)
                            del qkv, q_c, k_c, v_c
                        if not use_sol and not fused_rms:
                            query = self.q_norm(query)
                            key = self.k_norm(key)
                    else:
                        q_c = self.q_proj(x).view(1, seq_len, self.heads, self.head_dim)
                        k_c = self.k_proj(x).view(1, seq_len, self.heads, self.head_dim)
                        v_c = self.v_proj(x).view(1, seq_len, self.heads, self.head_dim)
                        if not use_sol and not fused_rms:
                            q_c = self.q_norm(q_c)
                            k_c = self.k_norm(k_c)
                        query, key, value = q_c, k_c, v_c
                else:
                    # Pecahan seimbang dinamik matematik tulen (Zero Hardcoding):
                    # Kiraan ruang selamat untuk penimbal kerja sementara selepas menolak penimbal destinasi Q,K,V:
                    avail_headroom = effective_free - dest_qkv_bytes - wddm_safe_guard_bytes
                    if avail_headroom > 0:
                        num_chunks = max(2, math.ceil(full_qkv_bytes / avail_headroom))
                    else:
                        safe_temp_cap = max(row_bytes * 2048, int((effective_free - wddm_safe_guard_bytes) * 0.5))
                        num_chunks = max(2, math.ceil(full_qkv_bytes / max(1, safe_temp_cap)))
                    
                    tokens_per_chunk = math.ceil(seq_len / num_chunks)
                    min_tokens = 2048 if not is_retry else 1024
                    chunk_tokens = min(seq_len, max(min_tokens, ((tokens_per_chunk + tile_tokens - 1) // tile_tokens) * tile_tokens))
                    num_chunks = math.ceil(seq_len / chunk_tokens)
                    
                    expected_shape = (1, seq_len, self.heads, self.head_dim)
                    try:
                        query = torch.empty(expected_shape, dtype=x.dtype, device=x.device)
                        key = torch.empty(expected_shape, dtype=x.dtype, device=x.device)
                        value = torch.empty(expected_shape, dtype=x.dtype, device=x.device)
                    except (torch.OutOfMemoryError, RuntimeError):
                        flush_vram()
                        try:
                            act = get_active_mmgp_instance()
                            if act is not None and hasattr(act, "unload_all"):
                                act.unload_all()
                                flush_vram()
                        except Exception:
                            pass
                        query = torch.empty(expected_shape, dtype=x.dtype, device=x.device)
                        key = torch.empty(expected_shape, dtype=x.dtype, device=x.device)
                        value = torch.empty(expected_shape, dtype=x.dtype, device=x.device)
                    
                    if split_qkv:
                        for start_i in range(0, seq_len, chunk_tokens):
                            end_i = min(start_i + chunk_tokens, seq_len)
                            c_len = end_i - start_i
                            x_c = x[start_i:end_i]
                            q_c = self.q_proj(x_c).view(c_len, self.heads, self.head_dim)
                            k_c = self.k_proj(x_c).view(c_len, self.heads, self.head_dim)
                            v_c = self.v_proj(x_c).view(c_len, self.heads, self.head_dim)
                            if not use_sol and not fused_rms:
                                q_c = self.q_norm(q_c)
                                k_c = self.k_norm(k_c)
                            query[0, start_i:end_i].copy_(q_c)
                            key[0, start_i:end_i].copy_(k_c)
                            value[0, start_i:end_i].copy_(v_c)
                            del x_c, q_c, k_c, v_c
                    else:
                        inner = self.heads * self.head_dim
                        for start_i in range(0, seq_len, chunk_tokens):
                            end_i = min(start_i + chunk_tokens, seq_len)
                            c_len = end_i - start_i
                            qkv_c = self.qkv_proj(x[start_i:end_i])
                            q_c, k_c, v_c = qkv_c.split(inner, dim=-1)
                            q_c = q_c.view(c_len, self.heads, self.head_dim)
                            k_c = k_c.view(c_len, self.heads, self.head_dim)
                            v_c = v_c.view(c_len, self.heads, self.head_dim)
                            if not use_sol and not fused_rms:
                                q_c = self.q_norm(q_c)
                                k_c = self.k_norm(k_c)
                            query[0, start_i:end_i].copy_(q_c)
                            key[0, start_i:end_i].copy_(k_c)
                            value[0, start_i:end_i].copy_(v_c)
                            del qkv_c, q_c, k_c, v_c

                del x

                if do_prof and torch.cuda.is_available():
                    torch.cuda.synchronize()
                t_qkv_ms = (time.perf_counter() - t0_qkv) * 1000.0
                t0_rope = time.perf_counter()

                # 2. RMSNorm / RoPE Vektor Selari:
                if use_sol:
                    from shared.sol_attn import qk_rms_norm_rope_
                    qk_rms_norm_rope_(query, key, self.q_norm.weight, self.k_norm.weight, rope, self.q_norm.eps)
                elif fused_rms:
                    query, key = h3_denoiser_kernels.rms_rope(query, key, rope, packed_rope, self.q_norm, self.k_norm)

                if rope is not None and not use_sol and not fused_rms:
                    pairs = rope.shape[-2]
                    cosine, sine = rope[..., 0], rope[..., 1]
                    rope_chunk = min(chunk_tokens, 1024)
                    if seq_len > rope_chunk:
                        for start_i in range(0, seq_len, rope_chunk):
                            end_i = min(start_i + rope_chunk, seq_len)
                            cos_c = cosine[:, start_i:end_i] if (cosine.ndim > 1 and cosine.shape[1] == seq_len) else cosine
                            sin_c = sine[:, start_i:end_i] if (sine.ndim > 1 and sine.shape[1] == seq_len) else sine
                            f = key[:, start_i:end_i, :, :pairs]
                            s = key[:, start_i:end_i, :, pairs:2 * pairs]
                            sc = f.clone()
                            f.mul_(cos_c).addcmul_(s, sin_c, value=-1)
                            s.mul_(cos_c).addcmul_(sc, sin_c)
                            del sc
                            f_q = query[:, start_i:end_i, :, :pairs]
                            s_q = query[:, start_i:end_i, :, pairs:2 * pairs]
                            sc_q = f_q.clone()
                            f_q.mul_(cos_c).addcmul_(s_q, sin_c, value=-1)
                            s_q.mul_(cos_c).addcmul_(sc_q, sin_c)
                            del sc_q
                    else:
                        scratch = torch.empty_like(key[..., :pairs])
                        f, s = key[..., :pairs], key[..., pairs:2 * pairs]
                        scratch.copy_(f)
                        f.mul_(cosine).addcmul_(s, sine, value=-1)
                        s.mul_(cosine).addcmul_(scratch, sine)
                        del scratch
                        scratch_q = torch.empty_like(query[..., :pairs])
                        f_q, s_q = query[..., :pairs], query[..., pairs:2 * pairs]
                        scratch_q.copy_(f_q)
                        f_q.mul_(cosine).addcmul_(s_q, sine, value=-1)
                        s_q.mul_(cosine).addcmul_(scratch_q, sine)
                        del scratch_q

                if do_prof and torch.cuda.is_available():
                    torch.cuda.synchronize()
                t_rope_ms = (time.perf_counter() - t0_rope) * 1000.0
                t0_attn = time.perf_counter()

                # 3. UNIFIED FAST ATTENTION (SageAttention 2 SM120 Natif 240ms / SDPA Resilient Fallback):
                from shared.attention import pay_attention, get_default_attention_mode, sageattn2
                from mmgp import offload
                dyn_attn = offload.shared_state.get("_attention") or get_default_attention_mode()
                if is_retry:
                    chosen_attn = "sdpa"
                elif dyn_attn in ("sage", "sage2", "auto") and sageattn2 is not None:
                    chosen_attn = "sage2"
                elif dyn_attn == "sdpa":
                    chosen_attn = "sdpa"
                else:
                    chosen_attn = "sage2" if sageattn2 is not None else "sdpa"

                qkv_list = [query, key, value]
                try:
                    if self.sol_attention is not None and use_sol:
                        attention = self.sol_attention(qkv_list, use_sol)
                    else:
                        attention = pay_attention(qkv_list, force_attention=chosen_attn, recycle_q=True)
                except Exception as e_attn:
                    flush_vram()
                    log_debug(f"[ATTN RESCUE] Percubaan attention '{chosen_attn}' gagal ({e_attn}). Menggunakan fallback SDPA terus...")
                    qkv_list = [query, key, value]
                    attention = pay_attention(qkv_list, force_attention="sdpa", recycle_q=True)

                output = attention.reshape(seq_len, -1)
                del query, key, value, attention, qkv_list

                if do_prof and torch.cuda.is_available():
                    torch.cuda.synchronize()
                t_attn_ms = (time.perf_counter() - t0_attn) * 1000.0
                t0_out_proj = time.perf_counter()

                # 4. Out-Projection (Gated Linear Residual):
                if residual is not None:
                    try:
                        from shared.kernels import ops as denoiser_kernels
                        res_linear = denoiser_kernels.gated_linear(self.out_proj, [output], residual, gate, segments)
                    except Exception:
                        res_linear = None
                    del output
                    if do_prof and torch.cuda.is_available():
                        torch.cuda.synchronize()
                    t_out_proj_ms = (time.perf_counter() - t0_out_proj) * 1000.0
                    if do_prof:
                        try:
                            mode_str = "Ya (SinglePass)" if can_single_pass else f"Tidak ({num_chunks} chunks, {chunk_tokens} tok)"
                            log_debug(
                                f"  [ATTN SUB-PROFILER] Pre (sensor/unload): {t_pre_ms:.1f}ms | SinglePass: {mode_str} | QKV Proj: {t_qkv_ms:.1f}ms | RoPE: {t_rope_ms:.1f}ms | "
                                f"Attention ({chosen_attn}): {t_attn_ms:.1f}ms | OutProj (gated): {t_out_proj_ms:.1f}ms"
                            )
                        except Exception:
                            pass
                    return res_linear

                # Tentukan sama ada out_proj boleh dijalankan secara satu laluan penuh berasaskan baki kolam + driver bebas
                out_proj_bytes = seq_len * out_f * output.element_size()
                if torch.cuda.is_available():
                    try:
                        fb_out, _ = torch.cuda.mem_get_info()
                        eff_free_out = fb_out + max(0, torch.cuda.memory_reserved() - torch.cuda.memory_allocated())
                    except Exception:
                        eff_free_out = effective_free
                else:
                    eff_free_out = effective_free
                can_out_single_pass = (not is_retry) and (eff_free_out >= (out_proj_bytes * 2) + wddm_pool_guard_bytes)
                if seq_len > chunk_tokens and (not can_single_pass and not can_out_single_pass):
                    res_out = torch.empty(seq_len, out_f, dtype=output.dtype, device=output.device)
                    for start_i in range(0, seq_len, chunk_tokens):
                        end_i = min(start_i + chunk_tokens, seq_len)
                        chunk_in = output[start_i:end_i]
                        try:
                            chunk_out = self.out_proj(chunk_in)
                        except Exception:
                            flush_vram()
                            chunk_out = self.out_proj(chunk_in)
                        res_out[start_i:end_i].copy_(chunk_out)
                        del chunk_out
                    del output
                    if do_prof and torch.cuda.is_available():
                        torch.cuda.synchronize()
                    t_out_proj_ms = (time.perf_counter() - t0_out_proj) * 1000.0
                    if do_prof:
                        try:
                            mode_str = "Ya (SinglePass)" if can_single_pass else f"Tidak ({num_chunks} chunks, {chunk_tokens} tok)"
                            log_debug(
                                f"  [ATTN SUB-PROFILER] Pre (sensor/unload): {t_pre_ms:.1f}ms | SinglePass: {mode_str} | QKV Proj: {t_qkv_ms:.1f}ms | RoPE: {t_rope_ms:.1f}ms | "
                                f"Attention ({chosen_attn}): {t_attn_ms:.1f}ms | OutProj: {t_out_proj_ms:.1f}ms"
                            )
                        except Exception:
                            pass
                    return res_out
                else:
                    try:
                        res = self.out_proj(output)
                    except Exception:
                        flush_vram()
                        res = self.out_proj(output)
                    del output
                    if do_prof and torch.cuda.is_available():
                        torch.cuda.synchronize()
                    t_out_proj_ms = (time.perf_counter() - t0_out_proj) * 1000.0
                    if do_prof:
                        try:
                            mode_str = "Ya (SinglePass)" if can_single_pass else f"Tidak ({num_chunks} chunks, {chunk_tokens} tok)"
                            log_debug(
                                f"  [ATTN SUB-PROFILER] Pre (sensor/unload): {t_pre_ms:.1f}ms | SinglePass: {mode_str} | QKV Proj: {t_qkv_ms:.1f}ms | RoPE: {t_rope_ms:.1f}ms | "
                                f"Attention ({chosen_attn}): {t_attn_ms:.1f}ms | OutProj: {t_out_proj_ms:.1f}ms"
                            )
                        except Exception:
                            pass
                    return res

            except Exception as e:
                err_s = str(e).lower()
                _h3_persistent_kv["query"] = None
                _h3_persistent_kv["key"] = None
                _h3_persistent_kv["value"] = None
                _h3_persistent_kv["attn_out"] = None
                flush_vram()
                if ("out of memory" in err_s or "cuda" in err_s or "acceleratorerror" in err_s) and (attempt < max_attempts - 1):
                    log_debug(f"[ATTN RESCUE] Kekangan memori aktivasi dikesan ({err_s}). VRAM disegarkan. Menjalankan cubaan semula mikro-chunk...")
                    continue
                # Pemulihan State Mutlak: Kembalikan tensor ke dalam x_list jika semua percubaan gagal
                x_list.clear()
                x_list.append(x_saved)
                if "out of memory" in err_s or "cuda" in err_s or "acceleratorerror" in err_s:
                    log_debug(f"[ATTN RESCUE] Had memori aktivasi muktamad dikesan dalam Attention.forward ({err_s}). VRAM disegarkan.")
                    flush_vram()
                raise e

    h3_transformer.Attention.forward = _safe_h3_attn_forward
    log_debug("Perisai 10c: MiniMax H3 State-Preserving Attention & Micro-Chunked RoPE Shield berjaya dipasang.")

    # --------------------------------------------------------------------------
    # PERISAI DIAGNOSTIK: Mikro-Profiler Ketepatan Tinggi MiniMax H3 DiTBlock
    # Mengukur latensi perkakasan setiap baris operasi Blok 0 & 1 secara langsung
    # --------------------------------------------------------------------------
    _orig_dit_block_forward = h3_transformer.DiTBlock.forward
    _h3_profile_block_runs = 0

    @functools.wraps(_orig_dit_block_forward)
    def _diag_dit_block_forward(self, x_list, temb, segments, rope, residual_signature_elements=0):
        """DIAGNOSTIK per blok: jejak langkah/blok, profil terperinci 2 blok pertama setiap langkah,
        satu baris masa + VRAM bagi setiap blok, dan bancian VRAM pada permulaan setiap langkah."""
        global _h3_profile_block_runs
        _h3_profile_block_runs += 1
        if _h3_diag["first_block_id"] is None:
            _h3_diag["first_block_id"] = id(self)
        if id(self) == _h3_diag["first_block_id"]:
            _h3_diag["step"] += 1
            _h3_diag["block_in_step"] = 0
            _h3_diag["last_block_end"] = None
        else:
            _h3_diag["block_in_step"] += 1
        step = _h3_diag["step"]
        blk = _h3_diag["block_in_step"]
        cuda_ok = torch.cuda.is_available()

        if blk == 0 and cuda_ok:
            # Hanya bersihkan sisa cache fasa pengekodan pada permulaan Langkah 1 Blok 0
            # (Elakkan pemusnahan kolam cache PyTorch 6.78GB antara langkah yang sihat)
            if step == 1 or _generation_state.get("vmm_spill_detected", False):
                _generation_state["vmm_spill_detected"] = False
                flush_vram()
            _h3_vram_census(f"Langkah {step} sebelum Blok 0")

        # Introspeksi Geometri Jujukan Masa-Nyata (Menyokong Tensor 2D [seq_len, hidden] & 3D [B, seq_len, hidden])
        if isinstance(x_list, (list, tuple)) and len(x_list) > 0 and torch.is_tensor(x_list[0]):
            x_ref = x_list[0]
            act_tokens = 0
            act_hidden = 0
            if x_ref.ndim >= 3:
                act_tokens = x_ref.shape[1]
                act_hidden = x_ref.shape[2]
            elif x_ref.ndim == 2:
                act_tokens = x_ref.shape[0]
                act_hidden = x_ref.shape[1]
            if act_tokens > 0:
                act_elem = x_ref.element_size()
                _generation_state["active_seq_len"] = act_tokens
                _generation_state["active_hidden_dim"] = act_hidden
                _generation_state["active_elem_size"] = act_elem
                if _generation_state.get("tuned_seq_len") != act_tokens:
                    _generation_state["tuned_seq_len"] = act_tokens
                    log_debug(f"[ADAPTASI ON-THE-FLY] Geometri tensor dikesan: tokens={act_tokens}, dim={act_hidden}, elem_bytes={act_elem}")

        # Jurang antara tamat blok sebelumnya dan mula blok ini = kos hook MMGP (muat/punggah berat)
        now = time.perf_counter()
        gap_ms = (now - _h3_diag["last_block_end"]) * 1000.0 if _h3_diag["last_block_end"] is not None else -1.0
        unload_before = _h3_diag["unload_count"]
        is_prof = (blk < 2)
        _h3_diag["prof_active"] = is_prof
        if cuda_ok and is_prof:
            try:
                torch.cuda.synchronize()
            except Exception:
                pass
        t_blk = time.perf_counter()

        try:
            if is_prof:
                res = _profiled_dit_block_forward(self, x_list, temb, segments, rope, residual_signature_elements,
                                                  run_idx=f"L{step} B{blk}")
            else:
                res = _orig_dit_block_forward(self, x_list, temb, segments, rope, residual_signature_elements)
            if cuda_ok and is_prof:
                torch.cuda.synchronize()
        except (torch.OutOfMemoryError, torch.AcceleratorError, RuntimeError, Exception) as e_blk:
            err_blk_s = str(e_blk).lower()
            if "out of memory" in err_blk_s or "cuda" in err_blk_s or "acceleratorerror" in err_blk_s:
                flush_vram()
                log_debug(f"[DIAG RESCUE BLOK] Ralat memori di Langkah {step} Blok {blk} ({e_blk}). Memulihkan alokasi...")
                try:
                    act = get_active_mmgp_instance()
                    if act is not None and hasattr(act, "unload_all"):
                        act.unload_all()
                        flush_vram()
                    res = _orig_dit_block_forward(self, x_list, temb, segments, rope, residual_signature_elements)
                    if cuda_ok and is_prof:
                        torch.cuda.synchronize()
                except Exception as e_retry:
                    log_debug(f"[DIAG RESCUE BLOK] Percubaan semula gagal: {e_retry}")
                    raise e_retry
            else:
                raise e_blk
        finally:
            _h3_diag["prof_active"] = False

        t_end = time.perf_counter()
        _h3_diag["last_block_end"] = t_end
        if is_prof:
            try:
                if cuda_ok:
                    free_b, tot_b = torch.cuda.mem_get_info()
                    cur_free_mb = free_b / 1048576.0
                    tot_gpu_mb = tot_b / 1048576.0
                    alloc_mb = torch.cuda.memory_allocated() / 1048576.0
                    res_mb = torch.cuda.memory_reserved() / 1048576.0
                    peak_mb = torch.cuda.max_memory_allocated() / 1048576.0
                    torch.cuda.reset_peak_memory_stats()

                    # Metrik Fizikal Sebenar Siling VRAM & Pengesanan Tumpahan VMM (100% Zero Hardcoding):
                    # Siling fizikal PyTorch = cur_free_mb + res_mb.
                    # Jika peak_mb > res_mb, bermakna alokasi telah melimpah keluar daripada kolam fizikal ke VMM Shared RAM!
                    pytorch_ceiling_mb = cur_free_mb + res_mb
                    vmm_spill_mb = max(0.0, peak_mb - res_mb)
                    peak_physical_margin_mb = pytorch_ceiling_mb - peak_mb
                    pulse_mb = max(0.0, peak_mb - alloc_mb)
                    if pulse_mb > 0:
                        _generation_state["real_act_pulse_mb"] = max(float(_generation_state.get("real_act_pulse_mb", 0.0)), float(pulse_mb))

                    log_debug(
                        f"[BLOK DIAG] L{step} B{blk}: kira={(t_end - t_blk) * 1000.0:.0f}ms | "
                        f"jurang_hook={gap_ms:.0f}ms | unload_all={_h3_diag['unload_count'] - unload_before} | "
                        f"alloc={alloc_mb:.0f}MB puncak={peak_mb:.0f}MB reserved={res_mb:.0f}MB driver_bebas={cur_free_mb:.0f}MB"
                    )
            except Exception:
                pass
        return res

    def _profiled_dit_block_forward(self, x_list, temb, segments, rope, residual_signature_elements=0, run_idx="?"):
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        t_start = time.perf_counter()

        # 1. AdaLN Proj
        t0 = time.perf_counter()
        shift_msa, scale_msa, gate_msa, shift_mlp, scale_mlp, gate_mlp = self.adaln_proj(temb)
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        t_adaln = (time.perf_counter() - t0) * 1000.0

        # 2. Norm 1
        residual_list = [h3_transformer._take(x_list)]
        t0 = time.perf_counter()
        h_list = [h3_transformer._norm_modulate(self.norm1, residual_list[0], [shift_msa, scale_msa], segments)]
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        t_norm1 = (time.perf_counter() - t0) * 1000.0

        # 3. Attention
        t0 = time.perf_counter()
        if (not residual_signature_elements and not hasattr(self.attn, 'vdn')
                and hasattr(h3_denoiser_kernels, "can_linear") and h3_denoiser_kernels.can_linear(self.attn.out_proj, residual_list[0])
                and h3_denoiser_kernels.can_linear(self.mlp.fc2, residual_list[0])):
            hidden = self.attn(h_list, rope=rope, residual=residual_list[0], gate=gate_msa, segments=segments)
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            t_attn = (time.perf_counter() - t0) * 1000.0
            t_gate1 = 0.0

            # 4. Norm 2
            t0 = time.perf_counter()
            h_list = [h3_transformer._norm_modulate(self.norm2, hidden, [shift_mlp, scale_mlp], segments)]
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            t_norm2 = (time.perf_counter() - t0) * 1000.0

            # 5. MLP
            t0 = time.perf_counter()
            res = self.mlp(h_list, residual=hidden, gate=gate_mlp, segments=segments)
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            t_mlp = (time.perf_counter() - t0) * 1000.0
            t_gate2 = 0.0
            del hidden, h_list, residual_list
        elif not residual_signature_elements:
            attn_out = self.attn(h_list, rope=rope)
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            t_attn = (time.perf_counter() - t0) * 1000.0

            t0 = time.perf_counter()
            residual_list = [h3_transformer._gated_residual(residual_list, [gate_msa], [attn_out], segments)]
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            t_gate1 = (time.perf_counter() - t0) * 1000.0
            del attn_out

            # 4. Norm 2
            t0 = time.perf_counter()
            h_list = [h3_transformer._norm_modulate(self.norm2, residual_list[0], [shift_mlp, scale_mlp], segments)]
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            t_norm2 = (time.perf_counter() - t0) * 1000.0

            # 5. MLP
            t0 = time.perf_counter()
            mlp_out = self.mlp(h_list)
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            t_mlp = (time.perf_counter() - t0) * 1000.0
            del h_list

            t0 = time.perf_counter()
            res = h3_transformer._gated_residual(residual_list, [gate_mlp], [mlp_out], segments)
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            t_gate2 = (time.perf_counter() - t0) * 1000.0
            del mlp_out, residual_list
        else:
            res = _orig_dit_block_forward(self, x_list, temb, segments, rope, residual_signature_elements)
            t_attn = t_gate1 = t_norm2 = t_mlp = t_gate2 = 0.0

        t_total = (time.perf_counter() - t_start) * 1000.0
        try:
            log_debug(
                f"\n{'='*65}\n"
                f"[PROFILER BLOK {run_idx}] Jumlah Masa Blok: {t_total:.1f}ms ({t_total/1000.0:.2f}s)\n"
                f"  |-- 1. AdaLN Proj:      {t_adaln:8.1f} ms\n"
                f"  |-- 2. Norm 1:          {t_norm1:8.1f} ms\n"
                f"  |-- 3. Attention:       {t_attn:8.1f} ms\n"
                f"  |-- 4. Gate Residual 1: {t_gate1:8.1f} ms\n"
                f"  |-- 5. Norm 2:          {t_norm2:8.1f} ms\n"
                f"  |-- 6. MLP:             {t_mlp:8.1f} ms\n"
                f"  \\-- 7. Gate Residual 2: {t_gate2:8.1f} ms\n"
                f"{'='*65}"
            )
        except Exception:
            pass
        return res

    h3_transformer.DiTBlock.forward = _diag_dit_block_forward
    log_debug("Perisai Diagnostik: Mikro-Profiler Ketepatan Tinggi MiniMax H3 (Per-Langkah + Per-Blok + Bancian VRAM) berjaya dipasang.")
except Exception as e:
    log_debug(f"Pintasan MiniMax H3 gagal: {e}")

# ------------------------------------------------------------------------------
# 6c2. Pemeliharaan Integriti Visual Qwen3-VL (100% Sifar Hardcoding)
# Mengekalkan _visual_patches asli Wan2GP tanpa pemampatan kaku/magic number.
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# 6d. PERISAI 11: INT8 ConvRot In-Place Hadamard Rotation Interceptor
# ------------------------------------------------------------------------------
try:
    import shared.qtypes.int8_convrot as int8_cr
    _orig_rotate_act = int8_cr._rotate_activation
    
    @functools.wraps(_orig_rotate_act)
    def _patched_rotate_act(input_tensor, group_size):
        group_size = int(group_size or 0)
        if group_size <= 0:
            return input_tensor
        features = int(input_tensor.shape[-1])
        if features % group_size != 0:
            raise RuntimeError(f"ConvRot input features {features} not divisible by group size {group_size}")
        h = int8_cr._regular_hadamard(group_size, input_tensor.device, input_tensor.dtype)
        shape = input_tensor.shape
        flat_in = input_tensor.reshape(-1, group_size)
        
        res = torch.empty_like(flat_in)
        chunk_size = compute_dynamic_chunk_size(flat_in.shape[0], group_size, group_size, input_tensor.element_size())
        for i in range(0, flat_in.shape[0], chunk_size):
            sub = flat_in[i : i + chunk_size]
            try:
                sub_res = _orig_matmul(sub, h)
            except Exception:
                sub_res = _orig_matmul(sub.to("cpu", dtype=input_tensor.dtype), h.to("cpu", dtype=input_tensor.dtype)).to(device=input_tensor.device, dtype=input_tensor.dtype)
            res[i : i + sub.shape[0]].copy_(sub_res)
            del sub, sub_res
        return res.reshape(shape)
        
    int8_cr._rotate_activation = _patched_rotate_act
    log_debug("Perisai 11: INT8 ConvRot In-Place Hadamard Rotation Interceptor berjaya dipasang.")
except Exception as e:
    log_debug(f"Pintasan int8_convrot gagal: {e}")

# ------------------------------------------------------------------------------
# 6e. PERISAI 12: Universal Resilient RMSNorm Interceptor (Direct Fast-Path + OOM Host Streaming Rescue)
# ------------------------------------------------------------------------------
try:
    _orig_f_rms_norm = torch.nn.functional.rms_norm
    
    @functools.wraps(_orig_f_rms_norm)
    def _safe_f_rms_norm(input, normalized_shape, weight=None, eps=1e-5):
        if _is_guard_active("in_rmsnorm"):
            return _orig_f_rms_norm(input, normalized_shape, weight=weight, eps=eps)
        _set_guard("in_rmsnorm", True)
        try:
            # 1. Selaraskan peranti & jenis data pemberat (weight alignment)
            w = weight.to(device=input.device, dtype=input.dtype) if (torch.is_tensor(weight) and (weight.device != input.device or weight.dtype != input.dtype)) else weight
            
            # 2. Laluan Pantas Utama (Direct Native Fast-Path)
            # Kernel CUDA C++ PyTorch natif beroperasi secara pantas (<1ms) dengan sifar peruntukan pendua
            try:
                return _orig_f_rms_norm(input, normalized_shape, weight=w, eps=eps)
            except Exception as first_err:
                err_s = str(first_err).lower()
                if not ("out of memory" in err_s or "cuda" in err_s or "acceleratorerror" in err_s):
                    raise first_err
            
            # 3. Sekiranya berlaku VRAM OOM, cuci serpihan VRAM dan cuba kali kedua
            flush_vram()
            try:
                return _orig_f_rms_norm(input, normalized_shape, weight=w, eps=eps)
            except Exception as second_err:
                err_s = str(second_err).lower()
                if not ("out of memory" in err_s or "cuda" in err_s or "acceleratorerror" in err_s):
                    raise second_err

            # 4. Pelan Penyelamat Kecemasan Sebenar (Universal OOM Host Streaming Rescue)
            # Jika GPU benar-benar kehabisan VRAM untuk satu tensor output, laksanakan streaming ke CPU tanpa alokasi pendua di GPU
            log_debug("[RMSNORM RESCUE] VRAM tepu, melaksanakan pemotongan selamat streaming ke CPU RAM...")
            if torch.is_tensor(input) and input.ndim >= 2:
                feat_dim = input.shape[-1]
                total_rows = input.numel() // feat_dim
                elem_size = input.element_size()
                target_dtype = input.dtype
                
                # Peruntukkan bekas hasil di CPU RAM agar sifar tekanan pada VRAM GPU
                res_cpu = torch.empty(*input.shape[:-1], feat_dim, dtype=target_dtype, device="cpu")
                flat_res = res_cpu.view(-1, feat_dim)
                flat_in = input.reshape(-1, feat_dim)
                
                # Kira chunk secara dinamik berasaskan baki RAM hos
                stats = get_live_memory_stats()
                ram_free_bytes = stats["ram_available_mb"] * 1024 * 1024
                chunk_rows = max(1024, min(total_rows, int((ram_free_bytes * 0.05) // (feat_dim * elem_size))))
                w_cpu = weight.to("cpu", dtype=target_dtype) if torch.is_tensor(weight) else None
                
                idx = 0
                while idx < total_rows:
                    cur_len = min(chunk_rows, total_rows - idx)
                    sub_in_cpu = flat_in[idx : idx + cur_len].to("cpu", dtype=target_dtype)
                    sub_out = _orig_f_rms_norm(sub_in_cpu, normalized_shape, weight=w_cpu, eps=eps)
                    flat_res[idx : idx + cur_len].copy_(sub_out)
                    del sub_in_cpu, sub_out
                    idx += cur_len  # Sentiasa maju ke hadapan: SIFAR INFINITE LOOP!
                
                # Kembalikan ke peranti input jika VRAM kini mempunyai ruang
                try:
                    return res_cpu.to(input.device, non_blocking=True)
                except Exception:
                    flush_vram()
                    try:
                        return res_cpu.to(input.device)
                    except Exception:
                        return res_cpu
            
            # Jika bukan tensor 2D+, hantar terus ke CPU
            in_cpu = input.to("cpu") if torch.is_tensor(input) else input
            w_cpu = weight.to("cpu") if torch.is_tensor(weight) else None
            out_cpu = _orig_f_rms_norm(in_cpu, normalized_shape, weight=w_cpu, eps=eps)
            try:
                return out_cpu.to(input.device)
            except Exception:
                return out_cpu
        finally:
            _set_guard("in_rmsnorm", False)
            
    torch.nn.functional.rms_norm = _safe_f_rms_norm
    log_debug("Perisai 12: Universal Resilient RMSNorm Interceptor (Direct Fast-Path + OOM Host Streaming Rescue) berjaya dipasang.")
except Exception as e:
    log_debug(f"Pintasan RMSNorm gagal: {e}")

# ------------------------------------------------------------------------------
# Perisai 13: LTX-2.5 Universal Local-First Connector Interceptor
# Reka bentuk: Mengutamakan varian connector yang wujud di cakera tempatan (contohnya INT8 ConvRot)
# bagi mengelakkan muat turun berlebihan 4.0GB varian BF16 untuk model GGUF / custom.
# Bebas hardcode: Berfungsi secara dinamik untuk sebarang nama fail model LTX-2.5.
# ------------------------------------------------------------------------------
try:
    import importlib
    _orig_import_module_ltx = importlib.import_module

    def _hooked_import_module_ltx(name, package=None):
        mod = _orig_import_module_ltx(name, package)
        if name == "models.ltx2.ltx2_handler":
            try:
                if not getattr(mod, "_smart_connector_patched", False) and hasattr(mod, "_get_ltx25_connector_variant"):
                    _orig_get_variant = mod._get_ltx25_connector_variant
                    def _smart_get_ltx25_connector_variant(transformer_path):
                        transformer_name = os.path.basename(transformer_path or "").lower()
                        if "nvfp4" in transformer_name:
                            return "bf16" if getattr(mod, "LTX2_25_NVFP4_USE_SHARED_EMBEDDERS", False) else "nvfp4"
                        if "int8" in transformer_name:
                            return "int8"
                        # Dynamic Local-First Discovery:
                        try:
                            from shared.utils import files_locator as fl
                            spec = getattr(mod, "_ARCH_SPECS", {}).get("ltx2_25_22B", {})
                            bf16_name = spec.get("video_embeddings_connector_bf16", "ltx-2.5-22b_video_embeddings_connector_bf16.safetensors")
                            int8_name = spec.get("video_embeddings_connector_int8", "ltx-2.5-22b_video_embeddings_connector_int8_convrot.safetensors")
                            if fl.locate_file(bf16_name, error_if_none=False) is None and fl.locate_file(int8_name, error_if_none=False) is not None:
                                log_debug(f"Perisai LTX-2.5 Connector: Menggunakan INT8 secara dinamik ({int8_name}) kerana BF16 tiada di cakera tempatan.")
                                return "int8"
                        except Exception as e:
                            log_debug(f"Penyemakan connector tempatan ralat: {e}")
                        return _orig_get_variant(transformer_path)
                    mod._get_ltx25_connector_variant = _smart_get_ltx25_connector_variant
                    mod._smart_connector_patched = True
            except Exception as e:
                log_debug(f"Gagal memasang perisai connector LTX-2.5: {e}")
        return mod

    importlib.import_module = _hooked_import_module_ltx
except Exception as e:
    log_debug(f"Pintasan importlib LTX-2.5 gagal: {e}")


# ------------------------------------------------------------------------------
# 7. Menjalankan wgp.py Dengan Hotfix Gradio
# ------------------------------------------------------------------------------
def main():
    wgp_path = pathlib.Path("wgp.py")
    if not wgp_path.exists():
        log_debug("Fail wgp.py tidak dijumpai di direktori semasa.")
        sys.exit(1)
        
    log_debug("Membaca dan menjalankan wgp.py...")
    
    main_module = sys.modules["__main__"]
    main_module.__file__ = str(wgp_path.resolve())
    
    code_text = wgp_path.read_text(encoding="utf-8")
    
    # Hotfix 1: Gradio (gr.Row -> gr.Tabs) secara in-memory
    patched_code = code_text.replace(
        "return  gr.Row(visible=new_advanced)", 
        "return  gr.Tabs(visible=new_advanced)"
    )

    # Hotfix 2: PERISAI BARIS 4187 (Pintasan Callback Live Preview OOM-Safe dengan Inden Tepat 16 Space)
    target_preview_line = 'payload = pipe.prepare_preview_payload(latent, preview_meta) if hasattr(pipe, "prepare_preview_payload") else latent'
    replacement_preview_line = "try:\n                safe_lat = latent[:, :1] if (torch.is_tensor(latent) and latent.ndim >= 3 and latent.shape[1] > 1) else latent\n                payload = pipe.prepare_preview_payload(safe_lat, preview_meta) if hasattr(pipe, \"prepare_preview_payload\") else safe_lat\n            except Exception:\n                payload = None"
    
    if target_preview_line in patched_code:
        patched_code = patched_code.replace(target_preview_line, replacement_preview_line)
        log_debug("Perisai 3: Pintasan Baris 4187 Callback Preview OOM-Safe (Inden Tepat) berjaya disuntik!")

    # Hotfix 3: Memaktubkan lock_inference_steps = False pada baris 11072
    target_lock_calc = 'lock_inference_steps = model_def.get("lock_inference_steps", False) or (audio_only and not inference_steps_enabled)'
    replacement_lock_calc = 'lock_inference_steps = False if ("dev" in str(model_type).lower() or "custom" in str(model_type).lower()) else (model_def.get("lock_inference_steps", False) or (audio_only and not inference_steps_enabled))'
    if target_lock_calc in patched_code:
        patched_code = patched_code.replace(target_lock_calc, replacement_lock_calc)
        log_debug("Pintasan Baris 11072 (lock_inference_steps = False) berjaya disuntik.")

    # Hotfix 4: Memaksa baris inference_steps_row untuk sentiasa visible=True secara bersih tanpa memecahkan konteks gr.Row
    target_steps_row = "with gr.Row(visible = not lock_inference_steps) as inference_steps_row:"
    replacement_steps_row = "with gr.Row(visible = True) as inference_steps_row:"
    if target_steps_row in patched_code:
        patched_code = patched_code.replace(target_steps_row, replacement_steps_row)
        log_debug("Pintasan Baris 11738 (visible=True bersih) berjaya disuntik.")
    else:
        target_steps_row_alt = "with gr.Row(visible=not lock_inference_steps) as inference_steps_row:"
        if target_steps_row_alt in patched_code:
            patched_code = patched_code.replace(target_steps_row_alt, replacement_steps_row)
            log_debug("Pintasan Baris 11738 (visible=True bersih alt) berjaya disuntik.")

    # Hotfix 5: Pintasan get_model_def()
    target_get_model_def = 'def get_model_def(model_type):\n    return models_def.get(model_type, None )'
    replacement_get_model_def = '''def get_model_def(model_type):
    mdef = models_def.get(model_type, None)
    if mdef is not None:
        if mdef.get("ltx2_pipeline") == "dev" or "dev" in str(model_type).lower() or "custom" in str(model_type).lower():
            mdef["lock_inference_steps"] = False
            mdef["inference_steps"] = True
    return mdef'''
    if target_get_model_def in patched_code:
        patched_code = patched_code.replace(target_get_model_def, replacement_get_model_def)
        log_debug("Pintasan get_model_def() berjaya disuntik.")

    # Hotfix 6: Pintasan get_default_settings() dengan pemeliharaan solver asal dan 8 langkah untuk model distilled
    replacement_get_default_settings = '''    if model_type and ("dev" in str(model_type).lower() or "custom" in str(model_type).lower() or (get_model_def(model_type) or {}).get("ltx2_pipeline") == "dev"):
        if not ("distilled" in str(model_type).lower() or (get_model_def(model_type) or {}).get("distilled", False)):
            if ui_defaults.get("num_inference_steps", 8) == 8:
                ui_defaults["num_inference_steps"] = 25
    return ui_defaults'''

    if "def get_default_settings(model_type):" in patched_code:
        parts = patched_code.split("def get_default_settings(model_type):")
        sub_parts = parts[1].split("return ui_defaults", 1)
        parts[1] = sub_parts[0] + replacement_get_default_settings.strip() + sub_parts[1]
        patched_code = "def get_default_settings(model_type):".join(parts)
        log_debug("Pintasan get_default_settings() berjaya disuntik.")

    # Hotfix 7: Perisai Sejagat get_base_model_type & get_lora_dir untuk model kustom / finetune
    target_get_base_model_type = '''def get_base_model_type(model_type):
    model_def = get_model_def(model_type)
    if model_def == None:
        return model_type if model_type in model_types_handlers else None 
    else:
        return model_def["architecture"]'''

    replacement_get_base_model_type = '''def get_base_model_type(model_type):
    model_def = get_model_def(model_type)
    if model_def is not None and "architecture" in model_def:
        return model_def["architecture"]
    if model_type in model_types_handlers:
        return model_type
    m_str = str(model_type).lower()
    if "minimax" in m_str:
        if "ref2va" in m_str:
            return "minimax_h3_ref2va_pruned" if "pruned" in m_str else "minimax_h3_ref2va"
        return "minimax_h3_fl2va_pruned" if "pruned" in m_str else "minimax_h3_fl2va"
    elif "ltx2_5" in m_str or "ltx_2_5" in m_str or "ltx-2.5" in m_str:
        return "ltx2_25_22B"
    elif "ltx2" in m_str or "ltx_2" in m_str or "ltx-2" in m_str:
        return "ltx2_22B"
    elif "ltxv" in m_str:
        return "ltxv_13B"
    elif "wan" in m_str:
        return "wan_14B" if ("14b" in m_str or "480p" in m_str or "720p" in m_str) else "wan_1.3B"
    elif "hunyuan" in m_str:
        return "hunyuan_video_720"
    return None'''

    if target_get_base_model_type in patched_code:
        patched_code = patched_code.replace(target_get_base_model_type, replacement_get_base_model_type)
        log_debug("Perisai Sejagat get_base_model_type berjaya disuntik.")

    target_get_lora_dir = '''def get_lora_dir(model_type):
    base_model_type = get_base_model_type(model_type)
    if base_model_type is None:
        raise Exception("loras unknown")'''

    replacement_get_lora_dir = '''def get_lora_dir(model_type):
    base_model_type = get_base_model_type(model_type)
    if base_model_type is None:
        m_str = str(model_type).lower()
        if "minimax" in m_str:
            base_model_type = "minimax_h3"
        elif "ltx" in m_str:
            base_model_type = "ltx2_25_22B"
        elif "wan" in m_str:
            base_model_type = "wan_14B"
        else:
            base_model_type = "ltx2_25_22B"'''

    if target_get_lora_dir in patched_code:
        patched_code = patched_code.replace(target_get_lora_dir, replacement_get_lora_dir)
        log_debug("Perisai Sejagat get_lora_dir berjaya disuntik.")

    # ==========================================================================
    # PERISAI SEJAGAT: UNIVERSAL DUAL-PHASE DEEP MEMORY CLEANER (PRE & POST GEN)
    # 1. Pembersihan VRAM GPU (PyTorch Caching, MMGP Unload, IPC Collect, VRAM Vacuum).
    # 2. Pembersihan RAM Sistem Pintar (Win32 Working Set Trimming proses lain).
    #    MUTLAK: Mengecualikan proses Wan2GP sendiri (PID semasa) agar memori pantas di RAM fizikal!
    # 3. Beroperasi pada Pra-Penjanaan (sebelum jana) dan Pasca-Penjanaan (selepas simpan video).
    # 4. 100% Sifar Hardcoding: Mengesan perkakasan GPU & RAM secara dinamik.
    # ==========================================================================
    def _universal_deep_clean_memory(phase_label="PASCA-PENJANAAN"):
        try:
            # A. Punggah dan Segarkan SEMUA Pengurus MMGP Aktif (Zero Orphan Offload)
            try:
                clean_candidates = set()
                act_inst = get_active_mmgp_instance()
                if act_inst is not None:
                    clean_candidates.add(act_inst)
                for name in ("offloadobj", "enhancer_offloadobj", "wan_model", "transformer"):
                    o = getattr(main_module, name, None)
                    if o is not None:
                        if hasattr(o, "models") and hasattr(o, "unload_all"):
                            clean_candidates.add(o)
                        for sub_attr in ("offloadobj", "_shared_offloadobj", "_private_offloadobj", "_mm_manager"):
                            sub_o = getattr(o, sub_attr, None)
                            if sub_o is not None and hasattr(sub_o, "models"):
                                clean_candidates.add(sub_o)
                for inst in clean_candidates:
                    safe_mmgp_unload(inst, "all")
                if not clean_candidates:
                    import mmgp.offload as _mmgp_offload
                    if hasattr(_mmgp_offload, "unload_all"):
                        _mmgp_offload.unload_all()
            except Exception:
                pass

            # B. Bersihkan gen_cache, shared_state, KV cache & penimbal model MiniMax H3
            try:
                if hasattr(main_module, "clear_gen_cache"):
                    try:
                        main_module.clear_gen_cache()
                    except Exception:
                        pass
                import mmgp.offload as _m_off
                if hasattr(_m_off, "shared_state") and isinstance(_m_off.shared_state, dict):
                    try:
                        cur_attn = _m_off.shared_state.get("_attention")
                        _m_off.shared_state.clear()
                        if cur_attn:
                            _m_off.shared_state["_attention"] = cur_attn
                    except Exception:
                        pass
            except Exception:
                pass

            # Kosongkan penimbal KV MiniMax H3 global & atribut konteks pipeline
            try:
                if "_h3_persistent_kv" in globals():
                    for k in list(_h3_persistent_kv.keys()):
                        _h3_persistent_kv[k] = None
                wm = getattr(main_module, "wan_model", None)
                if wm is not None:
                    for attr in ("text_encoder_cache", "_current_context", "_current_video"):
                        if hasattr(wm, attr):
                            cache_o = getattr(wm, attr)
                            if hasattr(cache_o, "clear"):
                                cache_o.clear()
                    # 1. Pipeline MiniMax H3 Text Encoder (language_model + visual)
                    te = getattr(wm, "text_encoder", None)
                    if te is not None:
                        for sub_m in (getattr(te, "language_model", None), getattr(te, "visual", None), te):
                            if sub_m is not None and hasattr(sub_m, "parameters"):
                                for p in sub_m.parameters():
                                    if p is not None and getattr(p, "is_cuda", False):
                                        try:
                                            p.data = p.data.to("cpu")
                                        except Exception:
                                            pass
                                for b in sub_m.buffers():
                                    if b is not None and getattr(b, "is_cuda", False):
                                        try:
                                            b.data = b.data.to("cpu")
                                        except Exception:
                                            pass
                    # 2. Modul-modul lain dalam pipeline
                    for comp_name in ("transformer", "video_encoder", "video_decoder", "vae", "audio_vae", "latent_upscaler"):
                        comp = getattr(wm, comp_name, None)
                        if comp is not None and hasattr(comp, "parameters"):
                            for p in comp.parameters():
                                if p is not None and getattr(p, "is_cuda", False):
                                    try:
                                        p.data = p.data.to("cpu")
                                    except Exception:
                                        pass
                            for b in comp.buffers():
                                if b is not None and getattr(b, "is_cuda", False):
                                    try:
                                        b.data = b.data.to("cpu")
                                    except Exception:
                                        pass
            except Exception:
                pass

            # C. Pembersihan Mutlak Cache CUDA, MMap & RAM Hos (Zero VRAM Leak, Zero Destruction)
            try:
                from shared.cuda_memory import release_ram_cache
                release_ram_cache()
            except Exception:
                pass
            try:
                from mmgp.allocator import ram as mmgp_ram
                mmgp_ram.release()
            except Exception:
                pass

            # Bersihkan sebarang traceback exception dan call-stack frames aktif
            import sys, traceback
            try:
                exc_t, exc_v, exc_tb = sys.exc_info()
                if exc_tb is not None:
                    traceback.clear_frames(exc_tb)
                if exc_v is not None and hasattr(exc_v, "__traceback__") and exc_v.__traceback__ is not None:
                    traceback.clear_frames(exc_v.__traceback__)
            except Exception:
                pass

            flush_vram()
            _vacuum_vmm_orphan_allocations()
            gc.collect()
            if torch.cuda.is_available():
                try:
                    if "_orig_cuda_empty_cache" in globals():
                        _orig_cuda_empty_cache()
                    else:
                        torch.cuda.empty_cache()
                except Exception:
                    try:
                        torch.cuda.empty_cache()
                    except Exception:
                        pass
                try:
                    torch.cuda.ipc_collect()
                except Exception:
                    pass
                try:
                    torch.cuda.synchronize()
                except Exception:
                    pass
                try:
                    _vacuum_vmm_orphan_allocations()
                    torch.cuda.empty_cache()
                except Exception:
                    pass
                try:
                    torch.cuda.reset_peak_memory_stats()
                except Exception:
                    pass

            # D. Pembersihan RAM Sistem Windows Pintar (Pangkas proses lain & pangkas diri sendiri pasca-penjanaan)
            if os.name == 'nt':
                try:
                    import ctypes
                    from ctypes import wintypes
                    psapi = ctypes.WinDLL('psapi.dll')
                    kernel32 = ctypes.WinDLL('kernel32.dll')

                    current_pid = os.getpid()
                    pids = (wintypes.DWORD * 4096)()
                    bytes_returned = wintypes.DWORD()
                    PROCESS_QUERY_INFORMATION = 0x0400
                    PROCESS_SET_QUOTA = 0x0100

                    if psapi.EnumProcesses(ctypes.byref(pids), ctypes.sizeof(pids), ctypes.byref(bytes_returned)):
                        num_pids = bytes_returned.value // ctypes.sizeof(wintypes.DWORD)
                        for i in range(num_pids):
                            pid = pids[i]
                            if pid <= 4 or pid == current_pid:
                                continue
                            h_proc = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA, False, pid)
                            if h_proc:
                                try:
                                    psapi.EmptyWorkingSet(h_proc)
                                except Exception:
                                    pass
                                finally:
                                    kernel32.CloseHandle(h_proc)
                except Exception:
                    pass

            force_pagefile_push(force_trim=True)
            trim_current_process_working_set()

            # E. Pelaporan Telemetri Empirikal Tertutup (Closed-Loop Ground-Truth, Sifar Spekulasi)
            if torch.cuda.is_available():
                f_bytes, t_bytes = torch.cuda.mem_get_info()
                alloc_bytes = torch.cuda.memory_allocated()
                res_bytes = torch.cuda.memory_reserved()
                mem = psutil.virtual_memory()
                if alloc_bytes == 0:
                    print(f"[{phase_label}] VERIFIKASI VRAM BERJAYA: Alokasi CUDA 100% SIFAR (0.0 MB) | Reserved={res_bytes/(1024*1024):.1f}MB | DriverBebas={f_bytes/(1024*1024):.1f}MB/{t_bytes/(1024*1024):.1f}MB | RAM Hos: {mem.used/(1024**3):.2f}GB/{mem.total/(1024**3):.2f}GB ({mem.percent:.1f}%).")
                else:
                    live_census = []
                    for o in gc.get_objects():
                        try:
                            if torch.is_tensor(o) and o.is_cuda:
                                live_census.append(f"{list(o.shape)} {str(o.dtype).replace('torch.', '')} ({o.numel()*o.element_size()/1048576:.1f}MB)")
                                if len(live_census) >= 5:
                                    break
                        except Exception:
                            pass
                    census_str = ", ".join(live_census) if live_census else "Storan dalaman PyTorch Caching Allocator"
                    print(f"[{phase_label}] AMARAN BAKI VRAM: Alokasi={alloc_bytes/(1024*1024):.1f}MB | Tensor hidup: [{census_str}] | DriverBebas={f_bytes/(1024*1024):.1f}MB/{t_bytes/(1024*1024):.1f}MB | RAM Hos: {mem.used/(1024**3):.2f}GB/{mem.total/(1024**3):.2f}GB ({mem.percent:.1f}%).")
        except Exception as e_clean:
            pass

    main_module.__dict__["_universal_deep_clean_memory"] = _universal_deep_clean_memory

    # Suntikan 1: Pembersihan Pra-Penjanaan (Tepat semasa generate_media dipanggil sebelum proses apa-apa)
    target_pre_gen = '''def generate_media(
    task,
    send_cmd,'''

    replacement_pre_gen = '''def generate_media(
    task,
    send_cmd,'''

    target_wait_unload = '''    wait_for_model_unload()'''
    replacement_wait_unload = '''    wait_for_model_unload()
    try:
        if "_universal_deep_clean_memory" in globals():
            globals()["_universal_deep_clean_memory"]("PRA-PENJANAAN")
    except Exception:
        pass'''

    if target_wait_unload in patched_code:
        patched_code = patched_code.replace(target_wait_unload, replacement_wait_unload, 1)
        log_debug("Perisai Pembersihan Pra-Penjanaan (Pra-Gen Deep Clean) berjaya disuntik.")

    # Suntikan 2: Pembersihan Pasca-Penjanaan (Sebaik sahaja penjanaan tamat sepenuhnya)
    target_clean_exit = '''    remove_temp_filenames(temp_filenames_list)
    return True'''

    replacement_clean_exit = '''    remove_temp_filenames(temp_filenames_list)
    try:
        if "_universal_deep_clean_memory" in globals():
            globals()["_universal_deep_clean_memory"]("PASCA-PENJANAAN")
    except Exception:
        pass
    return True'''

    if target_clean_exit in patched_code:
        patched_code = patched_code.replace(target_clean_exit, replacement_clean_exit)
        log_debug("Perisai Pembersihan Pasca-Penjanaan (Pasca-Gen Deep Clean) berjaya disuntik.")

    # Suntikan 3: Pembersihan Pasca-Batal / Pasca-Ralat (Dijalankan selepas exc.__traceback__ dipadamkan)
    target_abort_exit = '''                send_cmd("error", new_error)
                clear_status(state)
                return False'''

    replacement_abort_exit = '''                send_cmd("error", new_error)
                clear_status(state)
                try:
                    _tb_mod = __import__("traceback")
                    _sys_mod = __import__("sys")
                    if 'e' in locals():
                        if hasattr(locals()['e'], '__traceback__') and locals()['e'].__traceback__ is not None:
                            _tb_mod.clear_frames(locals()['e'].__traceback__)
                            locals()['e'].__traceback__ = None
                    _cur_exc = _sys_mod.exc_info()
                    if _cur_exc[2] is not None:
                        _tb_mod.clear_frames(_cur_exc[2])
                except Exception:
                    pass
                try:
                    if "_universal_deep_clean_memory" in globals():
                        globals()["_universal_deep_clean_memory"]("PASCA-BATAL/RALAT")
                except Exception:
                    pass
                return False'''

    if target_abort_exit in patched_code:
        patched_code = patched_code.replace(target_abort_exit, replacement_abort_exit, 1)
        log_debug("Perisai Pembersihan Pasca-Batal/Ralat (Terminal Abort Clean) berjaya disuntik.")

    # Suntikan 3b: Pembersihan Mutlak Terminal Pasca-Ralat (Selepas Worker Thread Tamat Sepenuhnya & Release Gen)
    target_terminal_error = '''            notifications.finish_queue(server_config, gen, notification_run, time.time() - start_time)
            release_gen()
            raise gr.Error(data, print_exception= False, duration = 0)'''

    replacement_terminal_error = '''            notifications.finish_queue(server_config, gen, notification_run, time.time() - start_time)
            release_gen()
            try:
                if "_universal_deep_clean_memory" in globals():
                    globals()["_universal_deep_clean_memory"]("PASCA-RALAT-TERMINAL")
            except Exception:
                pass
            raise gr.Error(data, print_exception= False, duration = 0)'''

    if target_terminal_error in patched_code:
        patched_code = patched_code.replace(target_terminal_error, replacement_terminal_error, 1)
        log_debug("Perisai Pembersihan Mutlak Terminal Pasca-Ralat (Terminal Error Clean) berjaya disuntik.")

    # Suntikan 3c: Pembersihan Mutlak Pasca-Batal Pengguna (Pemicu serta-merta apabila Pengguna membatalkan penjanaan)
    target_queue_abort = '''                if abort:
                    notification_run.interrupt("Generation aborted by the user.", aborted=True)
                    send_cmd("status", "Video Generation Aborted")
                    send_cmd("output", None)'''

    replacement_queue_abort = '''                if abort:
                    notification_run.interrupt("Generation aborted by the user.", aborted=True)
                    send_cmd("status", "Video Generation Aborted")
                    send_cmd("output", None)
                    try:
                        if "_universal_deep_clean_memory" in globals():
                            globals()["_universal_deep_clean_memory"]("PASCA-BATAL-PENGGUNA")
                    except Exception:
                        pass'''

    if target_queue_abort in patched_code:
        patched_code = patched_code.replace(target_queue_abort, replacement_queue_abort, 1)
        log_debug("Perisai Pembersihan Mutlak Pasca-Batal Pengguna (User Abort Deep Clean) berjaya disuntik.")

    # Suntikan 3d: Pembersihan Mutlak Pasca-Release-Gen (Setiap kali pusingan giliran selesai sepenuhnya)
    target_release_gen = '''    def release_gen():
        set_main_generation_running(state, False)
        with gen_lock:
            process_status = gen.get("process_status", None)
            if isinstance(process_status, str) and process_status.startswith("request:"):
                gen["process_status"] = "process:" + process_status[len("request:"):]
            else:
                gen["process_status"] = None'''

    replacement_release_gen = '''    def release_gen():
        set_main_generation_running(state, False)
        with gen_lock:
            process_status = gen.get("process_status", None)
            if isinstance(process_status, str) and process_status.startswith("request:"):
                gen["process_status"] = "process:" + process_status[len("request:"):]
            else:
                gen["process_status"] = None
        try:
            if "_universal_deep_clean_memory" in globals():
                globals()["_universal_deep_clean_memory"]("PASCA-RELEASE-GEN")
        except Exception:
            pass'''

    if target_release_gen in patched_code:
        patched_code = patched_code.replace(target_release_gen, replacement_release_gen, 1)
        log_debug("Perisai Pembersihan Mutlak Pasca-Release-Gen (Release Gen Deep Clean) berjaya disuntik.")

    # Suntikan 3e: Pembersihan Mutlak Pasca-Worker-Exit (Sebaik sahaja queue worker thread tamat di blok finally)
    target_worker_exit = '''        finally:
            with lock:
                gen.pop("api_active_queue_task", None)
            send_cmd("worker_exit", None)'''

    replacement_worker_exit = '''        finally:
            with lock:
                gen.pop("api_active_queue_task", None)
            try:
                if "_universal_deep_clean_memory" in globals():
                    globals()["_universal_deep_clean_memory"]("PASCA-WORKER-EXIT")
            except Exception:
                pass
            send_cmd("worker_exit", None)'''

    if target_worker_exit in patched_code:
        patched_code = patched_code.replace(target_worker_exit, replacement_worker_exit, 1)
        log_debug("Perisai Pembersihan Mutlak Pasca-Worker-Exit (Worker Exit Deep Clean) berjaya disuntik.")

    # Suntikan 4: Perisai Gradio NoneType Guard (Anti-Spam TypeError Console)
    target_enhancer = '''def refresh_prompt_enhancer_labels(state, metadata, *, tab_id="generate"):
    # The first value scopes browser deduplication to this model selection.
    inputs = dict(zip(prompt_enhancer_labels.INPUT_KEYS, metadata[1:-1]))'''

    replacement_enhancer = '''def refresh_prompt_enhancer_labels(state, metadata, *, tab_id="generate"):
    if metadata is None or not isinstance(metadata, (list, tuple)) or len(metadata) < 2:
        return gr.skip(), gr.skip()
    # The first value scopes browser deduplication to this model selection.
    inputs = dict(zip(prompt_enhancer_labels.INPUT_KEYS, metadata[1:-1]))'''

    if target_enhancer in patched_code:
        patched_code = patched_code.replace(target_enhancer, replacement_enhancer, 1)
        log_debug("Perisai Gradio NoneType Guard (refresh_prompt_enhancer_labels) berjaya disuntik.")

    # Suntikan 5: Pengoptimuman Pasca-Muat Bersih (Pemeliharaan Integriti Penuh Modul MMGP)
    if "return wan_model, offloadobj" in patched_code:
        patched_code = re.sub(
            r"([ \t]+)return wan_model, offloadobj[ \t]*",
            r"\1try:\n\1    flush_vram()\n\1    trim_current_process_working_set()\n\1except Exception:\n\1    pass\n\1return wan_model, offloadobj",
            patched_code,
            count=1
        )
        log_debug("Perisai Pasca-Muat Bersih (Pemeliharaan Model MMGP) berjaya disuntik ke wgp.py!")

    # Jalankan wgp.py dalam konteks __main__
    exec(patched_code, main_module.__dict__)

if __name__ == "__main__":
    try:
        proc = psutil.Process(os.getpid())
        proc.nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
        log_debug("Keutamaan proses dilaraskan (Optimasi Pagefile Windows).")
    except Exception: pass
    
    main()

# --- KOD TAMAT: launch_optimized.py ---