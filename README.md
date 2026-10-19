# Wan2GP Launch Optimized

Launcher pelindung dinamik dan pengimbang memori (*dynamic memory arbiter*) untuk [Wan2GP](https://github.com/deepbeepmeep/Wan2GP). Direka khas untuk memastikan model Wan2GP (MiniMax H3, Wan2.1, LTX, FLUX, dsb.) dapat dijana pada GPU 8GB (seperti RTX 5050 Laptop GPU) dan persekitaran awan seperti Google Colab tanpa isu Out-Of-Memory (OOM) atau gangguan pemacu WDDM Windows.

---

## Ciri-Ciri Utama

1. **Zero Hardcoding**:
   - Tiada had memori statik atau nombor magik.
   - Menggunakan introspeksi objek modul secara langsung (`inspect_model_data`), pemetaan blok MMGP (`blocks_of_modules_sizes`), dan fizik perkakasan CUDA masa nyata.
2. **Perisai Sejagat (Universal Monkey-Patch Shields)**:
   - Resilient Convolutions (1D/2D/3D & Transposed fallback).
   - Universal Device & Dtype Harmonizers (LayerNorm, GroupNorm, SDPA, Cat, Stack, In-Place ops).
   - GGUF Universal Dynamic Memory Footprint & Resilient Kernels.
   - OOM-Safe Sparse Embedding Interceptor & Tiga Serangkai (`index_copy_`, `copy_`, `index_select`).
   - SageAttention 2 Fast-Path & SafeSharedState.
   - MiniMax H3 True On-Demand Disk-to-RAM VAE & Micro-Chunked RoPE.
3. **Penyelarasan Bebas Ralat (Zero Git Clone Modifications)**:
   - Memastikan repositori klon hulu Wan2GP kekal 100% bersih tanpa sebarang konflik `git pull`.

---

## Cara Penggunaan

### 1. Di Komputer Tempatan (Local PC)

Salin `launch_optimized.py` ke dalam folder Wan2GP anda:
```powershell
# Jalankan pelancar yang telah dioptimumkan
python launch_optimized.py
```

Untuk menyegerakkan perubahan dari `Wan2GP\launch_optimized.py` ke repositori ini:
```powershell
.\sync_repo.ps1 "Mesej komit anda"
git push origin master
```

### 2. Di Google Colab

Klonkan repositori Wan2GP dan gantikan/masukkan `launch_optimized.py`:
```python
# Di dalam notebook Colab:
!git clone https://github.com/deepbeepmeep/Wan2GP.git
!git clone https://github.com/amirudinebrelle/wan2gp-launch-optimized.git
!cp wan2gp-launch-optimized/launch_optimized.py Wan2GP/
%cd Wan2GP
!python launch_optimized.py --listen --server-port 7860
```
