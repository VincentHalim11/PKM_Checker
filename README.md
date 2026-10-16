# PKM Checker

**PKM Checker** adalah aplikasi desktop berbasis Flutter yang dikembangkan untuk membantu memeriksa kesesuaian format penulisan dokumen PDF proposal Program Kreativitas Mahasiswa (PKM). Aplikasi ini menggabungkan antarmuka desktop dengan mesin validasi berbasis Python untuk mendeteksi potensi ketidaksesuaian format dokumen.

## ✨ Fitur Utama

### 1. Pemeriksaan Format PDF
PKM Checker membantu memeriksa beberapa aspek format dokumen, meliputi:

- **Ukuran halaman:** memeriksa kesesuaian ukuran halaman dengan A4.
- **Jenis font:** mendeteksi penggunaan font yang tidak sesuai dengan aturan.
- **Ukuran font:** mengidentifikasi ukuran teks yang berpotensi tidak sesuai ketentuan.
- **Margin:** memeriksa posisi teks, gambar, dan tabel terhadap batas margin yang ditentukan.
- **Line spacing:** memeriksa jarak antarbaris paragraf.
- **Alignment:** memeriksa kesesuaian perataan teks.
- **Nomor halaman:** memeriksa jenis dan ukuran font, posisi, urutan, serta kelengkapan nomor halaman.
- **Struktur dokumen:** membantu memeriksa halaman awal dan jumlah halaman bagian inti berdasarkan aturan skema yang didukung.

### 2. Visualisasi Temuan
Hasil pemeriksaan dapat ditampilkan langsung pada PDF dengan penanda warna:

- 🔴 **Merah:** ketidaksesuaian ukuran font.
- 🔵 **Biru:** ketidaksesuaian jenis font.
- 🟣 **Ungu:** potensi pelanggaran margin.

Pengguna juga dapat memilih daftar temuan untuk menuju halaman terkait pada dokumen.

### 3. Ekspor PDF dengan Highlight
PKM Checker menyediakan fitur ekspor PDF hasil pemeriksaan dengan highlight permanen dan halaman legenda warna. Fitur ini membantu pengguna menemukan bagian dokumen yang perlu diperiksa atau diperbaiki.

Dokumen sumber tetap dipertahankan; hasil pemeriksaan disimpan sebagai file terpisah.

### 4. Aplikasi Desktop Windows
Aplikasi dikembangkan untuk Windows 64-bit. Pada versi rilis, mesin validasi Python dikemas bersama aplikasi sehingga pengguna tidak perlu memasang Python secara terpisah.

## 🛠️ Teknologi yang Digunakan

| Teknologi | Kegunaan |
|---|---|
| Flutter | Antarmuka aplikasi desktop |
| Dart | Logika antarmuka dan integrasi layanan |
| Python | Mesin validasi format PDF |
| PyMuPDF | Ekstraksi konten PDF, pemeriksaan, dan pembuatan highlight permanen |
| PyInstaller | Mengemas mesin validasi Python menjadi executable Windows |
| Inno Setup | Membuat installer aplikasi Windows |

## 📥 Download dan Instalasi

Untuk memperoleh versi aplikasi yang siap digunakan:

1. Buka halaman [Releases PKM Checker](https://github.com/VincentHalim11/PKM_Checker/releases).
2. Pilih versi rilis yang tersedia.
3. Unduh installer Windows (`.exe`) dari bagian **Assets**.
4. Jalankan installer dan ikuti petunjuk yang ditampilkan.
5. Buka PKM Checker melalui shortcut yang tersedia setelah instalasi.

Jika belum ada rilis yang dipublikasikan, installer akan tersedia setelah pengembang mengunggahnya ke halaman Releases.

## 🚀 Cara Penggunaan

1. Jalankan aplikasi PKM Checker.
2. Pilih dokumen PDF proposal yang ingin diperiksa.
3. Pilih skema PKM yang sesuai apabila diminta.
4. Jalankan proses validasi dan tunggu hasil pemeriksaan.
5. Tinjau status dan rincian hasil pemeriksaan.
6. Pilih kategori temuan untuk melihat lokasi terkait pada PDF.
7. Perbaiki dokumen sumber sesuai kebutuhan.
8. Gunakan fitur ekspor untuk menyimpan salinan PDF dengan highlight dan legenda.

## 📊 Status Pemeriksaan

Hasil pemeriksaan menggunakan status berikut:

- **PASS:** pemeriksaan tidak menemukan ketidaksesuaian berdasarkan aturan yang diperiksa.
- **FAIL:** ditemukan ketidaksesuaian yang perlu diperiksa atau diperbaiki.
- **REVIEW:** hasil perlu ditinjau lebih lanjut karena pemeriksaan otomatis belum dapat memberikan kesimpulan yang kuat.

## 📁 Struktur Repository

```text
PKM_Checker/
├── flutter_app/
│   ├── lib/
│   │   ├── screens/
│   │   └── services/
│   └── windows/
├── python_engine/
│   ├── src/
│   │   └── validator.py
│   └── test/
└── README.md
```

Keterangan:

- `flutter_app/` berisi aplikasi desktop dan antarmuka pengguna.
- `python_engine/` berisi mesin validasi PDF berbasis Python serta kode pengujian.
- `README.md` berisi dokumentasi proyek.

## ⚠️ Catatan

PKM Checker merupakan alat bantu pemeriksaan format dokumen secara otomatis. Hasil validasi tidak menggantikan pemeriksaan manual terhadap dokumen maupun peninjauan berdasarkan pedoman resmi PKM yang berlaku.

Pemeriksaan margin dilakukan berdasarkan posisi konten yang terdeteksi dalam PDF. Hasil tersebut tidak selalu dapat membuktikan nilai pengaturan margin asli pada dokumen Word. Elemen tertentu, seperti tabel, gambar, halaman hasil pemindaian, atau struktur PDF yang kompleks, juga dapat memengaruhi ketepatan deteksi.

Pengguna tetap disarankan meninjau temuan sebelum melakukan perbaikan pada dokumen sumber.

## 📌 Repository

GitHub: [VincentHalim11/PKM_Checker](https://github.com/VincentHalim11/PKM_Checker)

---

Dikembangkan untuk membantu proses pemeriksaan format penulisan proposal PKM secara lebih praktis melalui aplikasi desktop.
