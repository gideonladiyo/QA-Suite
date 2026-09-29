# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Pengguna utamanya adalah pemilik workspace yang sama, bekerja secara lokal untuk mencatat aktivitas QA, menjalankan utilitas developer, mengelola koneksi data, mengedit gambar, dan menyimpan informasi sensitif.

## Product Purpose

Workbench menyatukan pekerjaan teknis harian yang biasanya tersebar di banyak alat kecil ke dalam satu workspace lokal. Keberhasilan berarti pengguna dapat berpindah dari laporan, alat pemrosesan, koneksi project, editor gambar, dan vault tanpa kehilangan konteks atau mempelajari pola interaksi baru.

## Positioning

Satu meja kerja lokal yang menggabungkan dokumentasi QA dan utilitas developer dengan data tetap berada di perangkat pengguna, bukan dashboard publik atau produk kolaborasi generik.

## Operating Context

- Digunakan berulang sepanjang hari di desktop, dengan dukungan layar kecil untuk akses sesekali.
- Berisi data teknis padat, laporan bertahap, request API, JSON, token, koneksi database, gambar, serta secret.
- Bahasa antarmuka utama adalah Bahasa Indonesia, sementara istilah teknis yang lazim tetap dipertahankan.
- Navigasi cepat melalui sidebar dan command palette merupakan bagian penting dari penggunaan harian.

## Capabilities and Constraints

- Seluruh fungsi dan alur yang ada harus dipertahankan selama redesign.
- Tetap menggunakan Vue 3, TypeScript, Vite, Pinia, dan Vue Router.
- Aplikasi bersifat local/self-hosted dan tidak menambahkan telemetry atau panggilan eksternal yang tidak diperlukan.
- Light mode dan dark mode harus sama-sama didukung.
- Modul keamanan tetap mengikuti aturan masking, lock, dan konfirmasi yang sudah ada.
- Nama lama yang terlalu khusus pada QA diganti dengan identitas yang lebih general. Nama kerja yang didelegasikan untuk redesign ini adalah **Workbench**.

## Brand Commitments

- Nama produk: **Workbench**.
- Nada bahasa langsung, tenang, teknis, dan tidak memakai klaim marketing.
- Identitas harus terasa seperti alat kerja yang matang, bukan template SaaS atau dashboard AI generik.

## Evidence on Hand

- Implementasi frontend yang sudah berjalan di `frontend/src/`.
- Dokumen fitur dan batasan di `PRD_*.md`, `SYSTEM_ARCHITECTURE.md`, dan `AGENT_INSTRUCTIONS.md`.
- Tidak ada testimonial, logo pelanggan, metrik promosi, atau aset pemasaran; redesign tidak boleh mengarangnya.

## Product Principles

1. Fungsi dan keterbacaan selalu lebih penting daripada dekorasi.
2. Satu pola interaksi harus terasa konsisten di seluruh modul.
3. Informasi sensitif tetap privat, tersamarkan, dan eksplisit statusnya.
4. Kepadatan layar mendukung kerja cepat tanpa berubah menjadi cockpit.
5. Setiap elemen visual harus membantu orientasi, pemindaian, atau tindakan.

## Accessibility & Inclusion

Target minimum adalah WCAG AA untuk kontras, navigasi keyboard penuh, focus state yang terlihat, status yang tidak bergantung pada warna, dan layout responsif tanpa horizontal page scroll.
