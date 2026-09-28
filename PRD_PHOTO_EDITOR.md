# PRD: Photo Editor

**Module ID:** `photo_editor`  
**Menu label:** `Photo Editor`  
**Owner:** Personal QA & Developer Utilities Portal  
**Status:** Draft v0.1 — ready for product review  
**Target:** Desktop-first, local/self-hosted browser workspace

## 1. Overview

Photo Editor adalah workspace pengeditan gambar berlapis di dalam portal. Modul ini ditujukan untuk pekerjaan sehari-hari seperti crop, resize, koreksi warna, menghapus bagian gambar, membuat seleksi, masking, retouch, menambahkan teks atau bentuk, dan mengekspor hasil tanpa perlu membuka layanan web pihak ketiga.

Pengeditan bersifat **local-first**: file gambar, isi layer, mask, preview, dan autosave diproses serta disimpan di browser pengguna. Backend portal tidak menerima piksel gambar pada v1. Pendekatan ini menjaga privasi, mengurangi beban server, dan sesuai dengan karakter portal yang berjalan secara lokal.

Modul ini bukan upaya menyalin seluruh Photoshop pada rilis pertama. Target v1 adalah menyediakan rangkaian alat yang lengkap untuk alur editing raster harian, dengan layer dan masking sebagai fondasi utama, melalui UI yang lebih mudah dipahami pengguna non-desainer.

## 2. Problem Statement

Saat ini pengguna harus berpindah ke aplikasi desktop atau situs pihak ketiga untuk melakukan perubahan sederhana maupun menengah pada screenshot, foto, aset QA, dan materi dokumentasi. Alur tersebut memperlambat pekerjaan, berpotensi mengirim gambar sensitif ke layanan eksternal, dan sering kali terlalu kompleks untuk tugas singkat.

Pengguna membutuhkan editor yang:

- bisa dibuka langsung dari sidebar portal;
- cukup kuat untuk editing berlapis dan masking;
- tidak merusak gambar sumber;
- menjelaskan fungsi alat dan state aktif dengan jelas;
- tetap responsif pada gambar beresolusi umum;
- tidak mengunggah gambar tanpa tindakan dan persetujuan eksplisit.

## 3. Goals

- Menyediakan workflow lengkap dari impor gambar sampai ekspor hasil dalam satu workspace.
- Menjadikan layer, selection, dan masking dapat dipakai tanpa mengharuskan pengguna memahami konsep Photoshop terlebih dahulu.
- Memastikan operasi utama non-destruktif atau dapat dibatalkan melalui history.
- Menjaga seluruh pemrosesan gambar tetap lokal di browser pada v1.
- Memberikan performa interaktif untuk dokumen umum hingga 4096 × 4096 px pada perangkat desktop modern.
- Menyediakan keyboard shortcut, tooltip, dan bantuan kontekstual untuk mempercepat pengguna mahir tanpa membingungkan pengguna baru.
- Mengikuti shell, token warna, dark/light theme, komponen bersama, dan standar aksesibilitas portal.

## 4. Success Criteria

Rilis v1 dianggap berhasil apabila:

- pengguna dapat mengimpor gambar, melakukan edit berlapis dengan minimal satu mask, menyimpan proyek, lalu mengekspor PNG/JPEG/WebP tanpa kehilangan hasil;
- semua aksi yang mengubah dokumen dapat di-undo/redo, kecuali aksi yang secara eksplisit diberi label tidak dapat dibatalkan;
- autosave dapat memulihkan sesi setelah refresh atau tab tertutup secara tidak sengaja;
- interaksi pan, zoom, brush, transform, dan slider adjustment tetap terasa langsung pada dokumen target 4096 × 4096 px dengan hingga 20 layer raster pada perangkat desktop kelas menengah;
- file asli tidak pernah ditimpa secara diam-diam;
- tidak ada data gambar yang dikirim ke backend atau pihak ketiga pada v1;
- alur utama dapat diselesaikan hanya dengan keyboard, kecuali gestur menggambar bebas yang memang membutuhkan pointer.

Karena portal tidak memakai analytics pihak ketiga, metrik penggunaan tidak dikirim keluar. Validasi keberhasilan dilakukan lewat pengujian tugas, benchmark lokal, dan laporan error lokal yang sengaja diekspor pengguna.

## 5. Non-Goals for v1

- Kompatibilitas penuh dengan Adobe Photoshop atau pengganti Photoshop untuk kebutuhan profesional tingkat lanjut.
- Impor/ekspor PSD dengan fidelity layer, smart object, effect, dan blending yang sempurna.
- Pemrosesan RAW kamera, workflow HDR, panorama stitching, atau focus stacking.
- Warna CMYK, spot color, ICC proofing profesional, separasi warna, dan kebutuhan prepress.
- Video, animasi frame, timeline, atau motion graphics.
- Kolaborasi real-time, cloud sync, komentar multi-user, atau version history server-side.
- Plugin pihak ketiga, scripting, macro, batch processing, dan action recorder.
- Fitur generative AI, background generation, face manipulation, atau panggilan model eksternal.
- Editor vektor penuh setara Illustrator; shape pada v1 hanya untuk komposisi dasar.

## 6. Primary Users and Jobs

### 6.1 QA tester

- Menutupi data sensitif pada screenshot menggunakan mask, blur, atau shape.
- Memberi anotasi, panah, teks, highlight, dan crop sebelum memasukkan gambar ke laporan bug.
- Mengekspor gambar terkompresi dengan ukuran yang sesuai untuk Slack atau issue tracker.

### 6.2 Developer

- Resize, crop, mengubah format, dan mengoptimalkan aset dengan cepat.
- Menghapus background sederhana atau bagian gambar menggunakan selection dan mask.
- Memeriksa dimensi, warna, dan transparansi tanpa mengunggah aset ke situs eksternal.

### 6.3 General workspace user

- Melakukan koreksi exposure, contrast, color, dan ketajaman pada foto.
- Menggabungkan beberapa gambar dengan layer, teks, dan bentuk.
- Memakai preset aman tanpa memahami semua parameter teknis.

## 7. Navigation and Information Architecture

- Tambahkan item utama **Photo Editor** di sidebar, setelah **Micro Tools** dan sebelum **Supabase Hub**.
- Route utama: `/photo-editor`.
- Command Palette mengenali kata kunci: `photo`, `image`, `gambar`, `edit`, `mask`, `crop`, `resize`, dan `compress`.
- Membuka menu tanpa proyek aktif menampilkan start screen, bukan canvas kosong yang membingungkan.
- Start screen menyediakan aksi **Buka gambar**, **Buat dokumen**, **paste screenshot (Ctrl+V)**, dan **Pulihkan autosave** bila tersedia.
- Satu tab browser hanya memiliki satu dokumen aktif pada v1. Membuka dokumen lain harus menawarkan simpan, unduh proyek, abaikan perubahan, atau batal.

## 8. Core User Flows

### 8.1 Quick edit

1. Pengguna membuka Photo Editor.
2. Pengguna memilih atau drag-and-drop gambar.
3. Editor membuat dokumen dengan satu raster layer dan mempertahankan file asli.
4. Pengguna crop/resize, melakukan adjustment, dan menambahkan anotasi bila perlu.
5. Pengguna memilih **Export**, melihat estimasi format, dimensi, dan ukuran, lalu mengunduh file baru.

### 8.2 Selection and masking

1. Pengguna memilih layer target.
2. Pengguna membuat selection dengan rectangle, ellipse, lasso, polygonal lasso, atau select-by-color.
3. Pengguna memperbaiki selection melalui add, subtract, feather, expand, contract, dan invert.
4. Pengguna memilih **Buat mask dari selection**.
5. Thumbnail mask menjadi aktif; canvas menunjukkan overlay mask opsional.
6. Pengguna mengecat mask dengan brush putih/hitam dan dapat menonaktifkan atau menghapus mask secara eksplisit.

### 8.3 Retouch

1. Pengguna menduplikasi layer atau membuat layer raster kosong.
2. Pengguna memilih healing atau clone, mengatur ukuran, hardness, opacity, dan source.
3. Preview stroke tampil selama pointer bergerak.
4. Setiap stroke menjadi satu langkah history yang dapat di-undo.

### 8.4 Save and resume

1. Perubahan memicu status **Belum disimpan** dan autosave tertunda.
2. Autosave lokal selesai tanpa mengganggu input dan status berubah menjadi **Tersimpan otomatis**.
3. Pengguna dapat mengunduh project file agar proyek dapat dipindahkan atau dibackup.
4. Saat proyek dibuka kembali, susunan layer, mask, adjustment, teks, dan ukuran canvas dipulihkan.

## 9. Functional Requirements and Acceptance Criteria

### 9.1 Document and file operations

- Membuat dokumen baru dengan width, height, background (transparent/white/custom), dan orientasi.
- Mengimpor PNG, JPEG, dan WebP. Format yang tidak didukung ditolak dengan alasan dan saran tindakan.
- Drag-and-drop atau paste screenshot ke start screen membuka gambar sebagai dokumen; pada dokumen aktif, gambar yang di-drop atau di-paste ditambahkan sebagai layer baru.
- Menampilkan nama proyek, dimensi canvas, zoom, perkiraan memori, dan status simpan.
- **Save Project** mengunduh project file versi portal yang mempertahankan struktur edit. **Export Image** menghasilkan gambar flattened; keduanya tidak boleh disamakan dalam copy UI.
- File sumber tidak pernah ditimpa. Nama ekspor default memakai suffix `-edited`.
- EXIF orientation diterapkan saat impor. Metadata pribadi seperti GPS tidak ikut pada hasil ekspor v1.
- Perubahan canvas size dan image size adalah aksi terpisah dengan preview dan penjelasan singkat.
- Image resize mendukung lock aspect ratio dan pilihan resampling yang ramah pengguna: **Cepat**, **Seimbang**, dan **Kualitas tinggi**.

### 9.2 Canvas and navigation

- Canvas mendukung zoom 5%–3200%, fit to screen, actual pixels (100%), pan, rotate view sementara, dan reset view.
- Space + drag melakukan pan; mouse wheel/trackpad zoom berpusat pada posisi pointer ketika modifier shortcut aktif.
- Background di luar canvas berbeda secara visual dari area gambar dan tetap terbaca di light/dark theme.
- Checkerboard transparansi dapat diaktifkan/dinonaktifkan dan memakai kontras yang tidak mengganggu isi gambar.
- Ruler, guides, grid, snapping, dan center indicators dapat diaktifkan secara terpisah.
- Snapping menyediakan target canvas edge, center, guide, dan layer bounds, dengan indikator visual saat snap terjadi.
- Pointer cursor, outline brush, selection edge, transform handles, dan layer aktif selalu mencerminkan alat yang sedang digunakan.

### 9.3 Tool system

- Toolbar utama memiliki: Move, Marquee, Lasso, Select by Color, Crop, Brush, Eraser, Fill/Gradient, Clone, Heal, Text, Shape, Eyedropper, Hand, dan Zoom.
- Hanya satu tool utama aktif pada satu waktu; tool aktif terlihat melalui label, icon state, dan `aria-pressed`, bukan warna saja.
- Context bar menampilkan opsi yang relevan dengan tool aktif dan tidak menampilkan seluruh pengaturan sekaligus.
- Hover/focus pada tool menampilkan nama, shortcut, dan satu kalimat fungsi.
- Tool group dapat dibuka dengan klik lama atau tombol disclosure yang dapat diakses keyboard.
- Nilai tool terakhir disimpan per tool dalam sesi, dengan aksi **Reset tool**.

### 9.4 Layers

- Jenis layer v1: raster, text, shape, adjustment, dan group.
- Pengguna dapat add, duplicate, rename, reorder, group/ungroup, hide/show, lock/unlock, dan delete layer.
- Layer panel menampilkan thumbnail, nama, type, visibility, lock, mask thumbnail, opacity, dan blend mode.
- Multi-select layer didukung untuk move, group, delete, duplicate, align, dan distribute.
- Opacity 0–100% dan blend mode minimum: Normal, Multiply, Screen, Overlay, Darken, Lighten, Color Dodge, Color Burn, Hard Light, Soft Light, Difference, Hue, Saturation, Color, dan Luminosity.
- Clipping mask didukung untuk membatasi layer pada alpha layer di bawahnya.
- Merge selected, merge visible, dan flatten memerlukan konfirmasi yang menjelaskan dampak pada editability. Flatten tidak mengganti project yang tersimpan sebelum pengguna menyimpan kembali.
- Layer yang terkunci tidak dapat dimodifikasi; editor menjelaskan penyebab aksi ditolak dan menyediakan shortcut menuju kontrol unlock.

### 9.5 Selection

- Selection tools: rectangle marquee, ellipse marquee, freehand lasso, polygonal lasso, dan select by color.
- Mode selection: replace, add, subtract, dan intersect.
- Operasi selection: select all, deselect, reselect last, invert, feather, expand, contract, dan transform selection.
- Select by color memiliki tolerance, contiguous toggle, sample active layer/sample merged, dan preview overlay.
- Selection edge terlihat pada semua zoom tanpa menutupi detail gambar; animasi edge berhenti ketika `prefers-reduced-motion` aktif.
- Aksi yang membutuhkan selection memberi pesan kontekstual jika selection kosong.
- Copy/cut/paste mempertahankan transparansi dan membuat layer baru saat paste.

### 9.6 Masking

- Setiap raster, text, shape, adjustment, atau group layer dapat memiliki satu pixel mask pada v1.
- Mask dapat dibuat sebagai reveal all, hide all, atau dari selection aktif.
- Mask dapat di-enable/disable, invert, apply, atau delete. Apply dan delete memakai copy yang menjelaskan perbedaan hasil.
- Klik thumbnail layer mengedit konten; klik thumbnail mask mengedit mask. Target aktif memiliki outline dan label yang jelas.
- Saat mask aktif, brush/eraser bekerja pada grayscale mask dan tidak boleh diam-diam merusak piksel layer.
- Overlay mask dapat ditampilkan dengan warna dan opacity yang dapat disesuaikan.
- Mask properties menyediakan density dan feather non-destruktif.
- Link/unlink mask terhadap layer menentukan apakah mask ikut saat layer dipindah atau ditransform.
- Quick Mask mengubah selection menjadi overlay sementara yang dapat diedit menggunakan brush, lalu dikembalikan menjadi selection.

### 9.7 Transform, crop, and geometry

- Free Transform mendukung scale, rotate, move, flip horizontal/vertical, dan numeric input.
- Aspect ratio terkunci secara default untuk raster/image layer; pengguna dapat membuka lock secara eksplisit.
- Transform menampilkan preview dan baru dicatat ke history setelah commit. Escape membatalkan; Enter menerapkan.
- Crop menyediakan free, original ratio, square, dan custom ratio, rotate/straighten, serta opsi delete/hide cropped pixels.
- Rotate canvas 90°/180°, flip canvas, image resize, dan canvas resize tersedia dari menu Image.
- Align dan distribute bekerja terhadap selection, canvas, atau layer acuan yang dipilih.
- Image layer baru otomatis di-fit dan dipusatkan pada canvas. Kontrol Fit, Fill, alignment enam arah, dan penambahan background polos tersedia untuk koreksi cepat.
- Auto Remove BG lokal menghapus background berwarna relatif polos yang terhubung ke tepi gambar, menyediakan tolerance, dapat di-undo, dan tidak mengunggah foto.

### 9.8 Drawing, fill, and retouch

- Brush dan eraser mendukung size, hardness, opacity, flow, spacing, pressure bila Pointer Events melaporkan pressure, dan stabilizer sederhana.
- Brush preset minimum: soft round, hard round, pencil, dan textured basic. Pengguna dapat menyimpan preset lokal bernama.
- Foreground/background colors dapat dipilih melalui color picker dengan input HEX, RGB, HSL, alpha, recent colors, dan palette workspace.
- Eyedropper dapat sample active layer atau merged view, dengan area 1×1, 3×3, atau 5×5.
- Fill mendukung foreground, background, transparent, dan pattern dasar. Gradient mendukung linear dan radial dengan color stops serta opacity.
- Clone Stamp memiliki pengambilan source yang eksplisit dan indikator posisi source.
- Healing Brush dan Spot Heal tersedia untuk koreksi area kecil. Hasil dipreview dan setiap stroke dapat di-undo.
- Blur, Sharpen, Smudge, Dodge, dan Burn tersedia sebagai tool brush dengan strength terbatas untuk mencegah perubahan ekstrem tidak sengaja.
- Destructive pixel tools menampilkan rekomendasi satu kali untuk bekerja pada duplikat atau layer kosong; pengguna dapat menonaktifkan tips tersebut.

### 9.9 Adjustments and filters

- Adjustment layer minimum: Brightness/Contrast, Exposure, Levels, Curves, Hue/Saturation, Vibrance, Color Balance, Black & White, Invert, dan Threshold.
- Adjustment layer bersifat non-destruktif, dapat diberi mask, diubah kembali, diatur opacity/blend mode, dan dibatasi dengan clipping mask.
- Preview adjustment diperbarui saat slider digerakkan; perubahan history dibuat saat interaksi selesai, bukan untuk setiap frame slider.
- Auto adjustment, bila tersedia, selalu menampilkan preview dan dapat dibatalkan; tidak boleh digambarkan sebagai hasil yang pasti benar.
- Filter minimum: Gaussian Blur, Motion Blur, Sharpen, Unsharp Mask, Noise, Pixelate, dan Vignette.
- Filter pada v1 diterapkan secara destruktif ke raster layer setelah dialog preview; editor menyarankan duplicate layer sebelum apply.
- Semua numeric control memiliki slider dan input angka dengan batas yang terdokumentasi.

### 9.10 Text and shapes

- Text layer mendukung font family lokal yang dibundel/tersedia di browser, size, weight, alignment, line height, letter spacing, color, opacity, dan multiline text box.
- Font fallback dijelaskan saat font project tidak tersedia; project tidak boleh gagal dibuka hanya karena font hilang.
- Shape minimum: rectangle, rounded rectangle, ellipse, line, arrow, dan polygon sederhana.
- Shape mendukung fill, stroke, stroke width, opacity, dan transform, serta tetap editable sampai dirasterisasi.
- Text dan shape dapat dirasterisasi melalui aksi eksplisit dengan konfirmasi tentang hilangnya editability.
- Anotasi cepat menyediakan preset arrow, highlight rectangle, numbered marker, dan redact block tanpa membuat toolbar baru yang terpisah.

### 9.11 History and recovery

- Undo/redo tersedia melalui tombol dan shortcut; nama aksi terakhir tampil pada tooltip/menu.
- History panel menampilkan urutan aksi sejak dokumen dibuka atau checkpoint terakhir.
- Consecutive brush movement dalam satu pointer-down dihitung sebagai satu history step.
- History disimpan dengan memory budget adaptif. Saat langkah lama harus dibuang, pengguna diberi status non-blocking.
- Autosave lokal berjalan setelah periode idle, tidak saat stroke atau transform masih aktif.
- Crash/refresh recovery menawarkan timestamp, nama, dimensi, dan preview kecil sebelum restore.
- Hanya satu recovery snapshot terakhir per project diperlukan pada v1. Recovery lama dibersihkan setelah project disimpan dan ditutup dengan benar.
- **Revert to opened** meminta konfirmasi dan tidak menghapus project file eksternal.

### 9.12 Export

- Format ekspor: PNG, JPEG, dan WebP.
- PNG menyediakan transparency toggle bila dokumen memiliki alpha.
- JPEG dan WebP menyediakan quality control dengan estimasi ukuran hasil setelah debounce.
- Pengguna dapat memilih full document atau selection, output dimensions, scale percentage, background flatten color, dan metadata policy.
- Export preview mendukung before/after dan zoom 100% untuk memeriksa artefak kompresi.
- Export tidak mengubah dokumen aktif atau menandainya tersimpan sebagai project.
- Kegagalan encode/download tidak menghilangkan dokumen atau perubahan pengguna.
- Copy flattened image to clipboard tersedia bila browser mengizinkan; kegagalan permission menampilkan langkah alternatif **Download**.

## 10. User-Friendly UX Requirements

### 10.1 Workspace layout

Desktop layout memakai empat area:

```text
┌──────────────────────────────────────────────────────────────────┐
│ Menu + document status + undo/redo + save project + export       │
├──────┬───────────────────────────────────────────────┬───────────┤
│ Tool │                                               │ Layers /  │
│ bar  │                  Canvas                       │ Properties│
│      │                                               │ / History │
├──────┴───────────────────────────────────────────────┴───────────┤
│ Tool hint · dimensions · zoom · memory/performance status        │
└──────────────────────────────────────────────────────────────────┘
```

- Canvas adalah primary surface dan memakai ruang terbesar.
- Panel kanan memiliki tabs **Layers**, **Properties**, dan **History**; panel dapat dilipat.
- Context bar tepat di atas canvas berubah mengikuti tool aktif.
- Advanced options memakai disclosure dan tidak memenuhi layar secara default.
- Label teks dipertahankan untuk aksi penting seperti Save Project dan Export; icon-only hanya untuk aksi yang sudah universal dan tetap membutuhkan tooltip/accessible name.
- Empty, loading, decoding, saving, exporting, recovery, error, unsupported, permission denied, disabled, dan out-of-memory states harus dirancang sebelum implementasi dianggap selesai.

### 10.2 Progressive disclosure and onboarding

- First-run tour maksimum lima langkah: open image, choose tool, layers, mask, export. Tour dapat dilewati dan dibuka kembali dari Help.
- Masking memiliki bantuan kontekstual singkat: **putih menampilkan, hitam menyembunyikan**.
- Setiap tool menyediakan contoh shortcut dan penjelasan satu kalimat; dokumentasi panjang berada di Help drawer.
- Preset memakai nama berbasis hasil, misalnya **Soft portrait**, **Crisp screenshot**, atau **Small web image**, bukan istilah teknis saja.
- Ketika aksi tidak tersedia, tooltip menjelaskan prasyaratnya, misalnya **Pilih raster layer untuk memakai Healing Brush**.
- Dialog destruktif menyebut layer/project terdampak dan menawarkan opsi yang lebih aman bila ada.

### 10.3 Responsive behavior

- Fitur penuh ditargetkan untuk viewport desktop ≥1024 px.
- Pada 768–1023 px, toolbar tetap terlihat dan panel kanan menjadi drawer; canvas tidak menyebabkan horizontal page scroll.
- Di bawah 768 px, pengguna masih dapat membuka, crop, rotate, memakai basic adjustment, undo/redo, dan export. Layer/mask lanjutan tetap dapat diakses melalui full-screen drawer tetapi diberi label **Lebih nyaman di desktop**.
- Touch target minimum 44 px. Canvas memakai Pointer Events agar mouse, pen, dan touch berbagi jalur input yang konsisten.
- Browser/device yang tidak memenuhi kemampuan render minimum menampilkan compatibility state sebelum dokumen besar diproses.

## 11. Keyboard Shortcuts

Shortcut minimum:

| Action | Shortcut |
|---|---|
| Open image | `Ctrl/Cmd + O` |
| Save/download project | `Ctrl/Cmd + S` |
| Export | `Ctrl/Cmd + Shift + E` |
| Undo / Redo | `Ctrl/Cmd + Z` / `Ctrl/Cmd + Shift + Z` |
| Move / Marquee / Lasso | `V` / `M` / `L` |
| Brush / Eraser / Crop | `B` / `E` / `C` |
| Text / Shape / Eyedropper | `T` / `U` / `I` |
| Hand / Zoom | `H` / `Z` |
| Decrease/increase brush | `[` / `]` |
| Deselect / Invert selection | `Ctrl/Cmd + D` / `Ctrl/Cmd + Shift + I` |
| Free Transform | `Ctrl/Cmd + T` |
| Fit canvas | `Ctrl/Cmd + 0` |
| Actual pixels | `Ctrl/Cmd + 1` |

- Shortcut tidak dijalankan saat fokus berada pada text input kecuali shortcut dokumen yang aman dan diharapkan.
- Browser-reserved shortcut yang tidak dapat dicegah dengan konsisten harus memiliki alternatif tombol/menu.
- Shortcut map ditampilkan di Help dan dapat dicari. Custom shortcut berada di luar scope v1.

## 12. Accessibility

- Semua toolbar, menu, dialog, tab, layer rows, dan numeric controls dapat digunakan dengan keyboard dan memiliki focus order yang logis.
- Canvas memiliki accessible summary yang menyebut ukuran dokumen, layer aktif, selection bounds, dan tool aktif. Editor tidak mengklaim bahwa manipulasi piksel bebas sepenuhnya dapat dioperasikan tanpa penglihatan.
- Layer reorder memiliki alternatif tombol **Move up/down** selain drag-and-drop.
- Warna bukan satu-satunya pembeda layer aktif, mask aktif, lock, selection mode, atau status error.
- Numeric values dapat diubah melalui input keyboard, bukan slider saja.
- Tooltips dapat dipicu lewat hover dan focus, serta tidak menutupi target aktif.
- Semua dialog mengelola focus, mendukung Escape ketika aman, dan mengembalikan focus ke pemicu.
- Motion mengikuti `prefers-reduced-motion`; marching ants selection diganti outline statis yang tetap jelas.
- Kontrol UI memenuhi WCAG 2.2 AA sejauh berlaku. Isi foto pengguna sendiri tidak termasuk dalam penilaian kontras UI.

## 13. Performance, Limits, and Compatibility

### 13.1 Supported target

- Target nyaman: canvas sampai 4096 × 4096 px, hingga 20 raster-equivalent layers, dan history aktif pada desktop modern.
- Hard limit awal: 8192 px per sisi, 64 megapixel canvas, 100 total layers, dan 256 megapixel total decoded raster surfaces. Limit aktual boleh diturunkan berdasarkan kemampuan GPU/browser sebelum alokasi dilakukan.
- Editor memperingatkan sebelum operasi yang diperkirakan melampaui memory budget dan tidak mencoba alokasi berulang setelah gagal.
- File input default maksimum 200 MB. Batas ini bukan jaminan file dapat dibuka karena gambar terkompresi dapat membutuhkan memori jauh lebih besar setelah decode.
- Preview interaktif boleh menggunakan resolusi sementara, tetapi export harus memakai resolusi dokumen penuh atau menjelaskan bila perangkat tidak mampu.

### 13.2 Responsiveness requirements

- Pan/zoom/transform menargetkan 60 fps dan tidak boleh turun terus-menerus di bawah 30 fps pada supported target.
- Tool stroke menampilkan feedback visual pada frame berikutnya; pekerjaan berat tidak memblokir main thread lebih dari 100 ms tanpa progress state.
- Decode, encode, thumbnail generation, histogram, filter, dan operasi piksel besar dipindahkan ke worker bila API browser mendukung.
- Operasi lebih dari 500 ms menampilkan progress atau busy state yang stabil; operasi cancellable menyediakan Cancel.
- Resize/filter/export besar tidak dapat dimulai dua kali melalui double click.

### 13.3 Browser baseline

- Dukungan resmi mengikuti browser Chromium yang dibundel/direkomendasikan untuk lingkungan lokal portal.
- Rendering memakai capability detection, bukan user-agent detection.
- Fallback Canvas 2D dapat menyediakan basic edit/export ketika akselerasi GPU tidak tersedia; fitur yang tidak aman dijalankan pada fallback harus dinonaktifkan dengan alasan yang jelas.
- Kehilangan WebGL context harus mencoba satu kali pemulihan tanpa menghapus project state. Jika gagal, tawarkan simpan project/reload.

## 14. Persistence and Project Format

- Autosave dan recovery menggunakan IndexedDB, bukan `localStorage`, karena ukuran data gambar.
- Project file menggunakan container versi milik portal dengan extension yang ditetapkan saat technical design. Container minimum menyimpan manifest versioned, canvas settings, ordered layer tree, pixel assets, masks, adjustment parameters, text/shape definitions, dan composite preview.
- Project format wajib memiliki `formatVersion` dan migrator agar versi baru tidak diam-diam merusak file lama.
- Import memvalidasi ukuran, jumlah entry, path, dan manifest sebelum melakukan decode untuk mencegah file rusak atau archive bomb.
- Project file dan autosave tidak dimasukkan ke backup QA Reports atau database PostgreSQL.
- Pengguna diberi peringatan bahwa menghapus site data/browser storage akan menghapus autosave lokal; **Save Project** adalah backup portabel.
- Bila File System Access API tersedia, direct save dapat ditawarkan setelah pengguna memilih file. Fallback selalu berupa download project baru.

## 15. Privacy and Security

- Tidak ada piksel, metadata, nama file, thumbnail, atau project data yang dikirim ke backend maupun pihak ketiga pada v1.
- Tidak ada CDN runtime, remote font, remote image processor, telemetry, atau crash uploader.
- Nama file dan metadata gambar tidak boleh muncul di log aplikasi kecuali pengguna secara eksplisit mengekspor diagnostic report.
- SVG tidak termasuk format impor v1 untuk menghindari active content dan perbedaan rasterization. Dukungan masa depan harus melakukan sanitization dan rasterization terisolasi.
- Clipboard read hanya dilakukan sebagai respons terhadap aksi paste pengguna; clipboard write hanya dilakukan saat pengguna memilih copy.
- Image decoder errors ditampilkan sebagai pesan aman tanpa menyisipkan metadata atau byte file ke DOM.
- Object URLs dibebaskan saat layer/project ditutup agar data dan memori tidak bertahan tanpa perlu.
- Diagnostic report berisi kemampuan browser, ukuran dokumen, jumlah/jenis layer, timing, dan kode error; tidak berisi piksel, isi teks layer, path, atau nama file secara default.

## 16. Technical Direction

Bagian ini menetapkan boundary, bukan memaksakan library tertentu sebelum spike teknis.

- Modul frontend berada di `frontend/src/modules/photo-editor/` dan memiliki `routes.ts`, views, components, store, engine adapters, workers, serialization, serta tests sendiri.
- Vue menangani shell dan state UI. State render berfrekuensi tinggi tidak boleh membuat seluruh component tree reactive pada setiap pointer move.
- Rendering engine memiliki API internal yang typed dan terpisah dari komponen Vue agar dapat diuji, dipindahkan ke worker, atau diganti tanpa mengubah UI.
- GPU acceleration direkomendasikan untuk compositing, blend mode, adjustment preview, mask, dan filter. Canvas 2D dipertahankan sebagai basic fallback dan untuk operasi yang lebih sederhana.
- Heavy work memakai Web Worker dan, ketika tersedia, OffscreenCanvas. UI harus tetap berfungsi dengan capability-based degradation ketika OffscreenCanvas tidak tersedia.
- Pixel buffers besar tidak disalin berulang antara main thread dan worker; gunakan transferable objects atau strategi tile/cache yang terukur.
- History memakai command/delta/checkpoint strategy, bukan menyimpan full-canvas snapshot untuk setiap input.
- Tidak ada backend router, tabel, atau migration pada v1 kecuali technical spike membuktikan kebutuhan yang tidak dapat dipenuhi secara lokal dan perubahan tersebut disetujui terpisah.
- Library rendering atau image codec baru harus dievaluasi untuk bundle size, lisensi, WebGL context recovery, color correctness, memory behavior, testability, dan maintenance. Keputusan dicatat melalui technical design/ADR sebelum implementasi.
- Shared portal primitives dipakai untuk button, modal, tabs, input, select, toast, error, dan confirmation. Canvas-specific controls boleh berada di modul; primitive umum yang terbukti reusable dapat dipromosikan kemudian.

## 17. Error and Edge Cases

- File rusak, format palsu, atau decode gagal: tampilkan nama format yang terdeteksi bila aman, alasan singkat, dan opsi memilih file lain.
- Gambar terlalu besar: hitung kebutuhan sebelum full decode bila metadata memungkinkan, lalu tawarkan buka versi diperkecil atau batal.
- Browser kehabisan memori: hentikan operasi, pertahankan last stable document state, kurangi cache/history, dan tawarkan export/save project.
- Storage quota habis: editing tetap berjalan jika memungkinkan, status autosave berubah menjadi gagal, dan pengguna diarahkan mengunduh project.
- Tab/browser ditutup saat ada perubahan: gunakan browser leave warning bila tersedia dan selalu mengandalkan autosave sebagai recovery, bukan jaminan dialog muncul.
- Export transparency ke JPEG: wajib meminta background flatten color; default mengikuti warna putih tetapi terlihat dan dapat diubah.
- Layer/mask target berubah saat operasi berlangsung: commit atau batalkan operasi aktif sebelum selection berubah.
- Font hilang: gunakan fallback yang terlihat, tandai text layer, dan pertahankan nama font asli dalam project.
- Clipboard permission ditolak: sediakan download dan instruksi singkat, tanpa loop permintaan izin.
- GPU context hilang: freeze input, tampilkan recovery state, dan jangan membuat project dianggap tersimpan sebelum state stabil.
- Undo melewati perubahan ukuran besar: tampilkan progress dan cegah input lain sampai state konsisten.
- Nilai numeric kosong/NaN/out of range: jangan commit; tampilkan batas valid inline dan pertahankan nilai terakhir yang valid.
- Shortcut berbenturan dengan browser/OS: aksi UI tetap tersedia dan Help menandai shortcut yang tidak didukung.

## 18. Testing Requirements

### 18.1 Unit tests

- Layer tree operations, selection algebra, mask compositing, transform matrices, blend calculations, color conversion, adjustment parameters, serialization/migration, history coalescing, limits, dan export option validation.
- Worker protocol, cancellation, stale response rejection, transferable ownership, dan error recovery.
- Project parser menolak manifest rusak, unsupported version, traversal path, oversized entry, dan decompression bomb pattern.

### 18.2 Component and integration tests

- Start screen, open/replace confirmation, tool activation, context bar, layer reorder/lock/visibility, active layer-versus-mask target, adjustment edit, autosave status, recovery, dan export flow.
- Keyboard navigation, focus restore, shortcut suppression pada text input, tooltip on focus, dan reduced-motion behavior.
- Permission denied, decode error, quota exceeded, worker crash, export error, GPU fallback, serta input state yang tetap terjaga.

### 18.3 Visual and render verification

- Golden-image tests dengan tolerance terdokumentasi untuk blend modes, masks, transforms, adjustments, filters, text, dan export alpha.
- Render comparison dijalankan pada browser target yang konsisten; perbedaan GPU kecil tidak boleh menghasilkan test yang flaky.
- Manual QA pada light/dark themes, 768/1024/1440 px viewport, mouse, keyboard, touch, serta pen bila tersedia.
- Uji round-trip project: create → edit → save → close → reopen → export, lalu bandingkan layer tree dan composite output.

### 18.4 Performance tests

- Benchmark dokumen 4096 × 4096 dengan 20 layer untuk pan/zoom, brush stroke, mask preview, adjustment slider, undo, autosave, dan export.
- Stress test sampai hard limit harus gagal secara terkontrol tanpa merusak autosave atau browser session.
- Memory tidak terus meningkat setelah project ditutup, history dipangkas, atau layer besar dihapus.

## 19. Delivery Plan

### Phase 0 — Technical spike

- Buktikan render/compositing, mask brush, worker/offscreen path, color correctness, project serialization, memory budget, dan export pada browser target.
- Pilih rendering/codec dependencies melalui ADR.
- Tetapkan extension project dan compatibility matrix.
- Exit criteria: prototype dapat membuka gambar 4096 × 4096, membuat dua layer dan satu mask, melakukan adjustment, undo, save/reopen, dan export tanpa kehilangan state.

### Phase 1 — Editing foundation

- Navigation, start screen, document lifecycle, canvas navigation, import/export, raster layers, move/transform/crop, brush/eraser, color picker, undo/redo, autosave, dan recovery.
- Exit criteria: quick edit flow dapat dipakai end-to-end dan aman terhadap refresh.

### Phase 2 — Selection and masking

- Marquee/lasso/select by color, selection operations, pixel masks, quick mask, overlay, feather/density, dan clipping mask.
- Exit criteria: pengguna dapat menghapus background sederhana secara non-destruktif dan memperbaiki edge dengan brush.

### Phase 3 — Creative and correction tools

- Adjustment layers, blend modes, filter, gradient/fill, retouch tools, text, shape, guide/grid/snap, multi-layer align/distribute.
- Exit criteria: seluruh functional requirements v1 tersedia dan render tests lulus.

### Phase 4 — Hardening and release

- Accessibility pass, compatibility fallback, large-file guards, project migrations, performance tuning, onboarding/help, documentation, dan full regression.
- Exit criteria: seluruh Definition of Done terpenuhi.

## 20. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Browser memory habis pada layer besar | Crash atau kehilangan edit | Preflight pixel budget, tile/cache strategy, adaptive history, autosave, hard limits |
| Scope berubah menjadi “semua fitur Photoshop” | Rilis tidak pernah selesai | V1 capability list dan phase exit criteria diperlakukan sebagai kontrak |
| Render berbeda antar GPU/browser | Hasil tidak konsisten | Browser baseline, golden tests, capability detection, CPU/basic fallback |
| Main thread macet | UX terasa rusak | Worker, OffscreenCanvas, batched state updates, cancellable operations |
| Project format sulit dimigrasi | File lama tidak bisa dibuka | Versioned manifest, migrations, round-trip fixtures sejak Phase 0 |
| UI terlalu padat bagi pemula | Fitur tidak ditemukan atau salah pakai | Context bar, progressive disclosure, first-run tour, meaningful disabled states |
| Destructive edit merusak hasil | Kehilangan kerja | Non-destructive defaults, history, duplicate recommendation, explicit confirmations |
| IndexedDB dibersihkan browser | Autosave hilang | Jelaskan batas recovery dan dorong Save Project sebagai backup portabel |

## 21. Open Product Decisions Before Implementation

Keputusan berikut harus ditutup pada Phase 0 dan dicatat di technical design:

- Nama final format project dan extension file.
- Rendering engine/library dibanding implementasi internal minimum.
- Codec tambahan yang layak dibundel tanpa memperbesar aplikasi secara berlebihan.
- Color space internal v1: sRGB-only atau dukungan Display-P3 dengan conversion yang konsisten.
- Apakah background removal berbasis lokal layak masuk versi setelah v1 tanpa mengirim data keluar.
- Default memory budget berdasarkan benchmark perangkat target pengguna.

Rekomendasi awal: gunakan sRGB-only untuk v1, jangan menjanjikan PSD/RAW, dan prioritaskan project round-trip serta masking yang stabil sebelum menambah filter baru.

## 22. Definition of Done

- [ ] Route dan menu Photo Editor tersedia di sidebar, dashboard quick action, dan Command Palette.
- [ ] Semua requirement Phase 1–4 yang ditandai v1 selesai atau secara eksplisit dipindahkan melalui revisi PRD.
- [ ] Tidak ada upload gambar atau request eksternal dari modul.
- [ ] Import, edit, mask, autosave, save project, reopen, dan export lulus end-to-end test.
- [ ] Setiap perubahan dokumen dapat di-undo/redo dan tidak ada silent overwrite file sumber.
- [ ] Error, empty, loading, disabled, permission, recovery, quota, dan out-of-memory states tersedia.
- [ ] Keyboard, focus, reduced motion, screen-reader labels, layer reorder alternative, dan contrast UI telah diperiksa.
- [ ] Benchmark supported target memenuhi budget yang disepakati dari Phase 0.
- [ ] Project format versioning, parser hardening, migration fixtures, dan corrupt-file recovery diuji.
- [ ] Light/dark theme dan responsive layouts telah diverifikasi.
- [ ] `DESIGN.md`, `SYSTEM_ARCHITECTURE.md`, `README.md`, dan dependency/license notes diperbarui saat implementasi dimulai.
- [ ] Frontend typecheck, lint, unit/integration tests, render tests, dan production build lulus.

## 23. Future Considerations

- Subject selection semantik untuk rambut, objek kompleks, dan background ramai menggunakan model lokal opsional.
- RAW decode dan non-destructive development workflow.
- PSD import/export terbatas dengan compatibility report.
- Smart objects, layer effects, vector masks, channels, dan advanced paths.
- Perspective warp, liquify, content-aware fill, panorama, dan batch actions.
- Project library server-side yang opsional dan tetap lokal, dengan explicit storage quota.
- Tablet-first workspace dan customizable keyboard shortcuts.
- Reusable QA annotation templates dan integrasi eksplisit ke QA Reports tanpa membuat modul saling mengakses data internal.
