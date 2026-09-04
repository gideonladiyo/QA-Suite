# Personal QA & Developer Utilities Portal

Workspace lokal berbasis Vue 3, Vite, TypeScript, Tailwind CSS, Pinia, dan Vue Router. Arah visual mengikuti [DESIGN.md](DESIGN.md).

## Tahap implementasi

| Tahap | Lingkup | Status |
|---|---|---|
| 1 | Fondasi frontend, shell, komponen reusable, tema, dan navigasi | Implemented |
| 2 | Fondasi FastAPI/Postgres, autentikasi lokal, migrasi, dan QA Reports | Implemented |
| 3 | Micro Utilities: HTTP Client, JSONizer, Dummy Data, Base64/JWT | Implemented |
| 4 | Supabase Hub | Belum dikerjakan |
| 5 | Vault dan keamanan secret | Belum dikerjakan |

QA Reports menyimpan laporan harian dan seluruh aktivitas ke PostgreSQL dalam satu transaksi. Alur utama: daftar laporan → tambah/buka → isi aktivitas yang bisa dilipat → simpan → salin untuk Slack atau unduh `.md`/`.txt`. Template custom, hapus dengan konfirmasi, backup/pemulihan JSON, HTML, salin dari kemarin, filter, metrik bulanan, dan CSV tersedia. Tidak perlu finalisasi atau konfigurasi pengiriman untuk mengekspor. Micro Tools memiliki empat workspace fungsional; modul tahap 4–5 masih berupa penjelasan fitur. Halaman `/components` menyediakan demonstrasi komponen dengan data contoh di memori. Preferensi tema, palet warna, dan ID template terakhir disimpan di localStorage, bukan isi laporan; sesi memakai cookie HttpOnly.

Status di atas merujuk source code. Container yang sudah berjalan tidak otomatis memakai perubahan; pembaruan memerlukan build/deploy yang disengaja. Migrasi `0002_micro_tools` menambah tabel riwayat dan preset; `0003_qa_report_templates` menambah template serta salinan format pada laporan tanpa mengubah isi laporan lama.

## Jalankan dengan Docker

Dari root proyek:

```sh
python backend/scripts/init_env.py
docker compose up --build -d
docker compose ps
```

Buka [QA Portal](http://localhost:8080), lalu buat akun lokal pertama dengan username dan password pilihanmu (12–128 karakter). Akun ini untuk satu workspace; belum ada pemulihan password otomatis. Script setup menghasilkan secret aplikasi/database acak di `.env`, tidak mencetak nilainya, dan tidak menimpa file yang sudah ada. Python 3.11+ cukup untuk script setup; backend memakai Python 3.12 di container.

Port hanya dipublikasikan ke loopback host. Nginx dan backend berjalan sebagai pengguna non-root. Routing SPA tetap bekerja saat membuka URL langsung atau refresh halaman. PostgreSQL dan backend tidak membuka port ke host. Jangan membagikan `.env` atau mempublikasikan port ke jaringan umum.

Untuk menghentikan:

```sh
docker compose down
```

Compose berisi frontend, backend, dan database. Migrasi Alembic dijalankan sebelum API mulai menerima request. Nginx meneruskan `/api/` ke backend; frontend tidak menerima `.env` backend atau server secret. Data persisten ada di volume `qa-portal_postgres_data`. Hindari `docker compose down -v` karena opsi itu menghapus volume beserta datanya. Simpan backup `.env` dan database secara terpisah dan aman.

## Development

Gunakan Node.js 24 LTS dan pnpm 11.19.0. Node minimal 22.12; Node 20.15 yang lama tidak memenuhi persyaratan toolchain.

```sh
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

Buka [development server](http://127.0.0.1:5173). Jalankan Compose terlebih dahulu; Vite memproksikan `/api` ke port 8080. Semua font dan ikon dibundel lokal, tanpa CDN runtime. Backend dependencies dikunci melalui `backend/constraints.txt`.

Untuk Docker/WSL, simpan salinan proyek di filesystem Linux WSL agar file watcher dan bind mount lebih cepat. Proyek Windows saat ini tetap dapat digunakan untuk build image karena tidak memakai bind mount.

## Pemeriksaan

```sh
cd frontend
pnpm typecheck
pnpm lint
pnpm test
pnpm build
pnpm test:worker
```

Tes mencakup pencegahan submit berulang, label/error input, navigasi tabs, sorting/pagination tabel, konfirmasi destruktif, output teks yang aman, kegagalan clipboard, pencarian command, dan preferensi tema.

Tes frontend juga mencakup URL coverage aman, kalender lokal, tampilan read-only, pembuatan laporan beserta aktivitas dalam satu request, unduhan teks, kegagalan preview setelah simpan, kegagalan simpan tanpa kehilangan draft, konfirmasi meninggalkan editor, konflik tanggal, dan input yang tetap ada ketika sesi habis. Tes backend memeriksa simpan/baca ulang di PostgreSQL serta kecocokan persis format teks dengan contoh laporan.

Backend (database pengujian terpisah, tidak menggunakan data aplikasi):

```sh
docker compose -f docker-compose.test.yml run --build --rm tests
docker compose -f docker-compose.test.yml down
```

Perintah menjalankan migrasi, pytest, Ruff, dan mypy. Data uji memakai tmpfs dan dibuang ketika container database uji dihentikan. Jangan memakai `.env` aplikasi untuk tes.

## Palet warna workspace

Buka **Settings → Identitas workspace**. Pilih **Portal original**, **Ocean**, **Forest**, **Sunset**, atau **Slate**, periksa preview, lalu klik **Terapkan palet**. Pemilihan preset belum mengubah warna aplikasi sampai diterapkan. **Batalkan perubahan** mengembalikan preview ke palet aktif.

Bagian **Sesuaikan warna atau impor palet** menyediakan color picker dan kode HEX untuk Utama, Sekunder, Aksen, dan Highlight. Tempel tepat empat kode HEX (3/6 digit, dipisahkan spasi/koma/titik koma) atau tautan Color Hunt/Coolors berisi empat warna, lalu **Muat ke preview**. Impor mengurutkan warna dari gelap ke terang; peran masing-masing warna bisa disesuaikan sebelum diterapkan. Tidak ada pengunduhan CSS, eksekusi tema, maupun permintaan jaringan saat impor.

Preset tambahan memakai kombinasi swatch dari [Material Design 2014](https://m2.material.io/design/color/the-color-system.html), bukan implementasi penuh tema Material. Palet awal berasal dari [Color Hunt](https://colorhunt.co/palette/f8b2b2af719d8b639b403d88). Warna dasar dipertahankan dalam preferensi; turunannya disesuaikan untuk keterbacaan teks/tombol di mode terang maupun gelap. Warna status sukses, peringatan, dan error tetap terpisah.

Palet disimpan di localStorage browser ini (`qa-portal:color-palette`), bukan PostgreSQL atau backup laporan. Tema terang/gelap tetap pengaturan terpisah. Jika penyimpanan ditolak browser, palet masih berlaku selama sesi dengan peringatan. Pilih **Portal original → Terapkan palet** untuk menghapus override dan kembali ke token CSS asli. Tidak memerlukan migrasi database atau dependensi baru.

## Pemakaian QA Reports

Lihat juga bagian **Micro Tools** di bawah untuk alat developer.

1. Buka [Daftar QA Reports](http://localhost:8080/qa-reports). Baris diurutkan menurut tanggal laporan, terlama di atas dan terbaru di bawah. Jika ada lebih dari 20 laporan, gunakan pagination atau **Ke laporan terbaru** untuk halaman terakhir. Filter disimpan dalam bagian yang bisa dibuka/tutup agar daftar terlihat dulu.
2. Klik **Tambah laporan** untuk membuka halaman input baru. Form kosong tidak membuat data sebelum disimpan. Atau pilih judul laporan yang sudah ada, lalu **Edit laporan**.
3. **Langkah 1 — Identitas laporan:** pilih format/template, lalu isi tanggal, judul, serta identitas dan isian tingkat laporan yang diperlukan. Belum ada isian aktivitas. Pilih **Lanjut ke aktivitas**.
4. **Langkah 2 — Isian per aktivitas:** isi seluruh kolom aktivitas yang dipakai template pada tahap ini. Format standar mencakup kode tiket, Environment, Result, coverage, Current issues, dan Current Status. Link/issue/status boleh dikosongkan; status kosong mengikuti Result. Klik **Tambah aktivitas** untuk tiket berikutnya. Aktivitas bisa dilipat; field wajib yang belum valid terbuka otomatis saat simpan. Tombol **Kembali** mempertahankan isian dan hubungan link/issue saat aktivitas diurutkan ulang.
5. Klik **Simpan laporan** di langkah terakhir. Tombol **Lanjut** hanya berpindah tahap; belum menyimpan ke database. Card aksi berada dalam alur halaman, tidak sticky. Setelah berhasil, halaman menampilkan laporan tersimpan dengan format **Slack (mrkdwn)**, **Markdown (.md)**, atau **Teks biasa (.txt)** untuk salin/unduh. **Simpan & ekspor Slack .md** juga tersedia di langkah terakhir. Preview dan unduhan hanya menggunakan versi yang berhasil disimpan.
6. Satu tanggal hanya memiliki satu laporan. Membuat laporan dengan tanggal yang sama menghasilkan pemberitahuan beserta tautan untuk membuka laporan yang sudah ada, bukan menimpanya. Mengubah tanggal ke tanggal yang sudah terisi juga ditolak.
7. **Hapus laporan** tersedia pada daftar dan halaman laporan. Konfirmasi menampilkan judul, tanggal, serta jumlah aktivitas. Hapus bersifat permanen untuk laporan beserta aktivitas/link; versi yang berubah di tab lain ditolak. Laporan final/terkirim juga dapat dihapus, tetapi pesan yang sebelumnya dikirim ke layanan luar tidak ikut dihapus.

### Template laporan custom

1. Buka **QA Reports → Template laporan** untuk melihat tabel template beserta jumlah penggunaan dan tanggal pembaruan. Klik **Tambah template** atau **Edit** untuk membuka halaman editor terpisah. Beri nama, lalu sesuaikan format awal atau tempel format sendiri. Gunakan **Sisipkan placeholder & lihat panduan** untuk memasukkan variabel tanpa mengetik sintaksnya. **Simpan template** kembali ke daftar; **Gunakan** pada tabel langsung membuka form laporan.
2. Placeholder bawaan seperti `{{report_date}}` dan `{{author_name}}` mengikuti data laporan. Bungkus bagian per tiket dengan `{{#activities}}` dan `{{/activities}}`; di dalamnya gunakan `{{activity_code}}`, `{{environment}}`, `{{result}}`, `{{coverage_links}}`, `{{current_issue}}`, atau `{{current_status}}`. Blok aktivitas boleh digunakan beberapa kali untuk bagian yang terpisah.
3. Tambahkan placeholder sendiri, misalnya `{{nama_proyek}}` di luar blok untuk diisi sekali per laporan, atau `{{next_step}}` di dalam blok untuk diisi per aktivitas. Placeholder berulang dalam lingkup yang sama cukup diisi sekali. Preview contoh dan daftar kolom langsung mengikuti perubahan format.
4. Klik **Simpan & buat laporan**. Alurnya mengikuti template: **Identitas laporan → Isian per aktivitas**, lalu preview dan simpan. Hanya kolom yang digunakan yang muncul, sesuai urutan placeholder; tanpa `{{coverage_links}}` tidak ada input coverage. Template tanpa blok aktivitas cukup satu tahap. Tanggal/judul tetap diperlukan untuk arsip laporan. Template terakhir diingat di browser; **Format standar QA** memakai alur dua tahap yang sama.
5. Laporan menyimpan salinan format dan isian custom. Mengedit atau menghapus template tidak mengubah laporan lama. Saat mengedit laporan lama, pertahankan **format tersimpan** atau pilih versi template terbaru secara eksplisit.

Backup JSON versi 3 menyertakan template serta isian custom per laporan dan per aktivitas. Backup versi 1/2 tetap dapat dipulihkan. Migrasi `0004_activity_template_values` menambah penyimpanan isian per aktivitas tanpa mengubah data lama. Template bukan kode yang dieksekusi; tidak ada skrip, kondisi, atau blok aktivitas bersarang. Result yang tidak digunakan template tidak masuk perhitungan pass rate.

## Micro Tools

Empat alat dapat dibuka dari sidebar atau Command Palette. Isian tetap ada saat pindah antaralat, hanya di memori tab; reload/menutup tab atau logout menghapus isian. Sesi habis sementara tetap mempertahankan isian untuk login ulang. Tidak ada analytics, CDN, atau pengiriman token ke situs decoder luar.

### HTTP Client

Collection berada di bagian atas HTTP Client. Buat collection, buka barisnya, lalu simpan request yang sedang ada di form. Daftar request hanya menampilkan nama, method, dan waktu update; detail sensitif disimpan terenkripsi di PostgreSQL. **Muat ke form** tidak otomatis mengirim request, dan izin localhost/LAN selalu kembali nonaktif.

Collection aktif dapat diekspor sebagai `.http-collection.json` dan diimpor kembali. Import menambahkan collection baru dan tidak menimpa nama yang sudah ada. File export memuat URL, body, header, variabel, serta autentikasi dalam teks biasa, sehingga harus diperlakukan sebagai file sensitif.

1. Isi method dan URL. Buka bagian **Headers & autentikasi**, **Body request**, atau **Variabel & pengaturan** bila diperlukan. Raw JSON, teks, dan form URL-encoded didukung; form diisi sebagai `name=value&other=value` yang sudah di-encode.
2. Gunakan `{{nama}}` pada URL, header, body, atau Basic/Bearer helper; nama variabel harus unik. Periksa hasil substitusi secara konseptual: substitusi adalah teks mentah, bukan JSON/URL escaping otomatis.
3. Klik **Kirim request**. Backend mengirim ke endpoint yang kamu pilih, dengan TLS verification, timeout 15 detik (1–30), tanpa mengikuti redirect atau mewarisi cookie sesi portal/proxy environment. Request yang mengubah data benar-benar berdampak pada endpoint; tidak ada auto-retry.
4. Respons menampilkan HTTP status, waktu, ukuran byte body diterima, header, dan teks UTF-8. JSON valid bisa dirapikan. Respons dipotong maksimal 2 MB; pratinjau maksimal 100.000 karakter, salin/unduh memuat seluruh bagian yang diterima. Respons biner bukan file download biner. Backend meminta `Accept-Encoding: identity`; jika endpoint tetap mengirim kompresi, body ditolak untuk membatasi risiko dekompresi berlebih.
5. Riwayat otomatis menyimpan N request terakhir (default 50; 1–200). Daftar hanya menampilkan method/waktu/status/ukuran, tanpa URL/header/body. **Muat ke form** mengganti isian, tetapi tidak langsung mengirim; nilai header/token tersembunyi sampai ditampilkan. Izin endpoint lokal harus diaktifkan lagi. **Hapus riwayat** meminta konfirmasi.

Akses localhost/LAN ditolak kecuali checkbox izin lokal diaktifkan untuk request tersebut. DNS diperiksa dan koneksi dipasangkan ke IP yang telah diperiksa; metadata/link-local, multicast, alamat reserved, dan transisi IPv6 tetap ditolak. Di Docker, localhost adalah container backend. Untuk API di Windows host, gunakan `host.docker.internal` dan izin lokal. Ini alat untuk satu pengguna di loopback, bukan proxy publik atau boundary keamanan untuk deployment multi-user.

URL, header, body, variabel, dan kredensial helper dalam riwayat dienkripsi AES-256-GCM dengan key turunan `APP_SECRET_KEY`, nonce acak per baris, serta UUID sebagai authenticated data. Metadata method/waktu/status/ukuran tidak dienkripsi. **Backup `.env`/APP_SECRET_KEY secara terpisah dari database**; mengganti atau kehilangan key membuat riwayat lama tidak terbaca. Respons tidak disimpan permanen. Riwayat terenkripsi tetap bisa dibaca pengguna yang login melalui aplikasi; enkripsi ini tidak menggantikan kontrol akses atau Vault.

### JSONizer

Pilih input JSON/YAML, tempel data, lalu pilih pretty JSON, minified JSON, atau YAML. Indentasi 2/4 spasi dan pengurutan key rekursif tersedia. Error menampilkan baris/kolom. Tree bisa dibuka/tutup dan dicari; hanya baris yang terlihat dirender. Salin output/minified atau unduh hasil.

Pemrosesan di worker setelah debounce 300 ms: input maksimal 2 MB UTF-8, 100.000 nilai, kedalaman 64; worker dihentikan setelah 30 detik. Alias berlebih/siklus YAML, duplicate YAML keys, custom tag yang tidak dikenal, dan nilai non-JSON ditolak. Komentar/anchor tidak dipertahankan. Angka memakai presisi Number JavaScript; ID panjang sebaiknya string.

### Dummy Data

Tambah field beserta tipenya, isi rentang integer/tanggal atau pilihan enum bila diperlukan, jumlah baris, dan nama tabel SQL. Klik **Buat data**; klik lagi dengan seed kosong untuk data baru, atau masukkan seed yang sama untuk hasil berulang. Seed efektif ditampilkan pada hasil. Reproduksibilitas mengasumsikan versi Faker yang sama (dikunci di lockfile).

Tersedia 13 tipe: nama lengkap/depan/belakang, email, telepon, alamat, perusahaan, UUID, integer, boolean, tanggal, lorem, dan enum. Data memakai locale en, email `.test`, dan rentang telepon fiktif; tidak dijamin unik. Batas: 1–30 field, 1–100.000 baris, 1 juta sel; lebih dari 10.000 baris meminta konfirmasi. Worker bisa dibatalkan dan memiliki timeout 30 detik; output dibatasi sekitar 20 MB.

Ekspor JSON/CSV/SQL INSERT PostgreSQL tersedia. CSV memberi apostrof pada nilai teks menyerupai formula; SQL mengutip identifier dan nilai, **tidak menjalankan SQL**. Preset menyimpan hanya schema field, maksimal 100 nama unik; duplikat ditolak tanpa overwrite. Preset dapat dimuat/dihapus dengan konfirmasi penghapusan. Jangan memasukkan secret dalam enum atau nama field; preset adalah JSON plaintext di database.

### Base64 / JWT

Encode/decode teks UTF-8 memakai alfabet standar atau URL-safe. JWT menampilkan header, payload, signature mentah, serta tanggal `exp`/`iat`/`nbf`. Status kedaluwarsa bukan bukti token valid.

Verifikasi signature hanya setelah kamu memilih algoritma yang diharapkan dan memasukkan key: HS256 shared secret atau RS256 public key PEM/SPKI (`BEGIN PUBLIC KEY`). Key privat tidak diperlukan. Verifikasi berlangsung di Web Crypto browser, tanpa pengambilan JWKS atau request ke backend; algoritma header harus cocok dengan pilihanmu. Signature cocok **tidak** memverifikasi issuer/audience/kebijakan aplikasi. Token/input maksimal 1 MB; key maksimal 16.384 karakter.

### Backup dan pengujian Micro Tools

Backup JSON di QA Reports tetap **khusus laporan**, tidak mencakup riwayat HTTP/preset. Backup seluruh database beserta salinan `.env` yang aman diperlukan untuk memulihkan riwayat dan preset. Jangan menaruh `.env` dalam file backup yang dibagikan.

Tes backend menggunakan mock transport (tidak mengirim ke API sungguhan) untuk timeout, redirect, DNS/IP, header, batas respons, riwayat, dan preset. Tes frontend mencakup konversi, seed, ekspor, JWT HS256/RS256, navigasi, masking, konfirmasi, dan tree ter-virtualisasi. Build/lint/typecheck dapat dilakukan tanpa menjalankan ulang aplikasi utama.

Breadcrumb **Laporan / judul laporan** mengembalikan pengguna ke daftar lewat **Laporan**. Navigasi kembali dan laporan tanggal lain juga tersedia sebagai tombol berbingkai; hapus memakai tombol warna bahaya yang terlihat tanpa hover.

Label **Tersimpan** berarti sudah ada di database dan masih bisa diedit. Nilai internal API/database tetap `draft` untuk kompatibilitas; bukan berarti gagal disimpan. `finalized`/`sent` tetap memiliki arti lama. Tidak perlu migrasi atau mengunci laporan yang sudah ada.

Teks diekspor berurutan: judul, `Date: September 1, 2026` (sesuai tanggal pilihan), `Testing Summary:`, `Test Coverage :`, `Current issues:`, dan `Current Status:`. Setiap aktivitas memiliki poin sendiri (`•` di Slack, `-` di Markdown/teks), dengan detail/link/baris lanjutan issue menjorok di bawah aktivitasnya. Urutan tiket mengikuti form; URL disertakan utuh. Bagian issue/coverage tanpa isi tidak ditampilkan. Isi Current issues cukup keterangannya, tanpa mengulang kode tiket. HTML juga bisa diunduh.

Simpan dan ekspor tidak mengunci laporan. Endpoint finalisasi/pengiriman lama tetap dipertahankan untuk kompatibilitas, tetapi bukan bagian dari UI harian. Laporan lama yang sudah final/terkirim tetap read-only dan dapat diekspor. Pengiriman Slack/email nyata tidak dijalankan oleh tes maupun alur baru ini.

### Format Slack dan Markdown

Slack memakai `mrkdwn`: `*tebal*`, `_miring_`, dan backtick untuk kode. Judul dan heading laporan dibuat tebal secara otomatis; catatan mempertahankan sintaks yang kamu ketik. Karakter kontrol Slack di-escape agar teks seperti `<!channel>` tidak berubah menjadi mention. Markdown umum memakai heading `#`/`##`; file Slack diberi akhiran `-slack.md` agar tidak tertukar. Format catatan tidak dikonversi oleh parser Markdown; gunakan sintaks sesuai target. HTML tidak mengeksekusi markup pengguna.

Hasil paste tidak selalu diformat otomatis oleh editor Slack. Periksa sebelum mengirim dan ikuti [panduan markup Slack](https://slack.com/help/articles/360039953113-Format-your-messages-in-Slack-with-markup).

### Backup dan pemulihan

Buka **Backup & pemulihan** di bawah daftar. **Unduh backup JSON** mencadangkan seluruh laporan (semua halaman, tanpa mengikuti filter), termasuk aktivitas, coverage, status, dan metadata. Batas versi ini 1.000 laporan / 10 MB; jika melampaui batas, ekspor ditolak secara eksplisit, bukan dipotong diam-diam.

Pilih file JSON untuk memulihkan, lalu konfirmasi nama file dan jumlah laporan. Seluruh file divalidasi terlebih dahulu. Hanya tanggal yang belum ada yang dipulihkan; tanggal yang sudah ada dilewati tanpa perubahan. Semua penambahan disimpan dalam satu transaksi. ID laporan/aktivitas baru dibuat saat pemulihan; tautan detail lama tidak dipulihkan. Status laporan final/terkirim tetap dipertahankan.

Backup ini hanya untuk data QA, bukan akun, password, sesi, `.env`, modul lain, atau salinan penuh volume PostgreSQL. File JSON tidak dienkripsi; simpan salinannya secara aman di luar volume database. Buat backup **sebelum** menghapus laporan. Belum ada backup otomatis/terjadwal atau recycle bin.

## Struktur UI

- `frontend/src/shared/components/ui/`: button, card, badge, form controls, tabs, dialog, tabel, code output, clipboard, dan feedback.
- `frontend/src/shared/components/layout/`: shell, sidebar, topbar, command palette.
- `frontend/src/shared/styles/tokens.css`: sumber token light/dark dan palette.
- `frontend/src/modules/`: halaman dan file routes masing-masing modul.
- `/components`: contoh penggunaan komponen dan state interaksinya.
- `/settings`: pilihan tema terang, gelap, atau mengikuti perangkat; preset, editor, dan impor palet pada Identitas workspace.

Komponen `UiCard` yang `interactive` memakai elemen button; jangan menaruh button/link lain di dalamnya. Dialog memakai `<dialog>` native, dengan focus trapping dan penutupan Escape dari browser. Tabel saat ini melakukan sorting dan pagination di memori; modul yang mengambil data server harus membuat kontrak pagination server yang eksplisit ketika dibangun.

`UiCopyButton` saat ini menerima teks yang sudah tersedia. Untuk Vault nanti, aksi copy wajib meminta dekripsi dari backend pada saat klik dan menghapus referensi plaintext sesudah dipakai, sesuai PRD Vault.

Tugas Kubernetes belum diimplementasikan. Docker Compose menjadi runtime lokal pada tahap awal.
