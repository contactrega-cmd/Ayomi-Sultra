# Dashboard Early Warning System (EWS) Inflasi Pangan Sulawesi Tenggara
### Terintegrasi PIHPS Bank Indonesia (21 Komoditas), SP2KP Kemendag RI & Inflasi BPS Sultra

Aplikasi dashboard pemantauan laju inflasi pangan strategis dan deteksi dini gejolak harga di **Provinsi Sulawesi Tenggara** (cakupan 17 Kabupaten/Kota), yang memadukan data harga multi-tingkat dari **PIHPS Bank Indonesia** (Kota Kendari, Kota Bau-Bau, dan Rata-rata Provinsi), **SP2KP Kemendag RI** (15 Kabupaten lainnya), dan rilis **BPS Sultra** untuk menghasilkan rekomendasi kebijakan intervensi TPID (Prinsip 4K).

---

## 🌟 Fitur Utama Dashboard

### 1. Cakupan 21 Komoditas Pangan Lengkap (10 Kategori PIHPS)
* **Beras (6 Varian)**: Beras Kualitas Bawah I & II, Beras Kualitas Medium I & II, Beras Kualitas Super I & II.
* **Daging & Telur (4 Varian)**: Daging Ayam Ras Segar, Daging Sapi Kualitas 1 & 2, Telur Ayam Ras Segar.
* **Aneka Bawang (2 Varian)**: Bawang Merah Ukuran Sedang, Bawang Putih Ukuran Sedang.
* **Aneka Cabai (4 Varian)**: Cabai Merah Besar, Cabai Merah Keriting, Cabai Rawit Hijau, Cabai Rawit Merah.
* **Minyak Goreng & Gula (5 Varian)**: Minyak Goreng Curah, Kemasan Bermerk 1 & 2, Gula Pasir Kualitas Premium & Lokal.

### 2. Pemantauan Perkembangan Inflasi & Harga Pangan Harian
* Menyediakan data harga harian penuh (2024–2026) serta analisis perkembangan inflasi BPS (YoY, MtM, YtD, dan disagregasi *Volatile Food*).
* Mendukung pemilih rentang waktu dan frekuensi pada grafik kartu: Harian, Mingguan, atau Bulanan.

### 3. Tampilan Kartu Komoditas (*Visual Commodity Cards with Smooth Area Chart*)
* Garis aksen biru atas (*Blue Top Border*).
* Ikon spesifik per rumpun komoditas.
* Lencana Status EWS dan ikon panah tren (↗ merah untuk kenaikan, ↘ hijau untuk penurunan).
* Kurva halus SVG (*Catmull-Rom spline*) dengan area gradien berarsir serta peta disparitas harga 17 Kab/Kota.

### 4. Mesin Rekomendasi Kebijakan TPID 4K (*Smart Mitigation*) & KAD
* **Keterjangkauan Harga**: Operasi Pasar Khusus, Gerakan Pangan Murah (GPM), Penyaluran Beras SPHP Bulog.
* **Ketersediaan Pasokan**: Kerja Sama Antar Daerah (KAD) berdasarkan disparitas harga 17 Kabupaten/Kota, aktivasi stok cadangan pangan.
* **Kelancaran Distribusi**: Fasilitasi Ongkos Angkut (FOTA) untuk menjembatani daerah defisit ke daerah surplus.
* **Komunikasi Efektif**: Publikasi stok pangan dan transparansi harga wajar untuk mencegah *panic buying*.

### 5. Analisis Disparitas & Transmisi Rantai Pasok
* **Tabel Disparitas Wilayah**: Selisih harga komoditas antar daerah di Pasar Tradisional.
* **Tabel Rantai Pasok Kota Kendari**: Margin berjenjang dari Produsen $\rightarrow$ Pedagang Besar (Grosir) $\rightarrow$ Pasar Tradisional (Eceran).

---

## 📁 Struktur Direktori

```
ews-inflasi-dashboard/
├── data/
│   ├── pihps_sultra_all.json      # Dataset JSON master PIHPS (Kendari, Bau-Bau, Sultra)
│   ├── sp2kp_daily_sultra.json    # Dataset harga harian SP2KP 17 Kab/Kota
│   └── bps_inflation_2024_2026.json # Dataset inflasi resmi BPS Sultra
├── scraper/
│   ├── sync_live_pihps_bi.py      # Scraper live PIHPS Bank Indonesia
│   ├── sp2kp_daily_scraper.py     # Scraper harian SP2KP Kemendag RI
│   └── generate_alps_17_kabkota.py # Penyusun data pantauan harga 17 Kab/Kota
├── build_index_html.py            # Script penyusun file dashboard mandiri
├── index.html                     # Antarmuka dashboard utama (Tailwind CSS & SVG Chart)
├── server.py                      # Backend server lokal & bridge API live sync
└── README.md                      # Dokumentasi proyek
```

---

## 🚀 Cara Menjalankan Dashboard

### Opsi 1: Menjalankan Server Live Sync (Rekomendasi Utama)
Server ini memungkinkan Anda menggunakan tombol **`🔄 Sinkronkan Data`** langsung dari browser dengan 1-klik:

```bash
cd /Users/regaprasetyo/.gemini/antigravity/scratch/ews-inflasi-dashboard
python3 server.py
```
Lalu buka browser Anda di:
👉 **`http://localhost:8080`**

### Opsi 2: Membuka File Mandiri Langsung (*Offline Mode*)
Anda juga dapat langsung membuka file `index.html` tanpa menyalakan server:
```bash
open /Users/regaprasetyo/.gemini/antigravity/scratch/ews-inflasi-dashboard/index.html
```

---

## 🔄 Pembaruan Data Manual (Jika Diperlukan)

Jika Anda ingin memperbarui dataset secara manual melalui terminal:
```bash
# 1. Update data harga pangan PIHPS BI & SP2KP:
python3 scraper/sync_live_pihps_bi.py
python3 scraper/sp2kp_daily_scraper.py

# 2. Perbarui data 17 Kab/Kota & kompilasi ulang dashboard:
python3 scraper/generate_alps_17_kabkota.py
python3 build_index_html.py
```
