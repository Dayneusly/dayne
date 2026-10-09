# Panduan deploy ke Streamlit Community Cloud

## File yang dipakai

- streamlit_app.py: aplikasi Streamlit.
- requirements.txt: daftar paket Python.
- .streamlit/config.toml: tema gelap.
- latihan1_data.js: data latihan JavaScript yang dikompresi.
- convert_csv_to_js.py: konverter CSV ke file data JS.

File latihan1.csv dikecualikan oleh .gitignore; aplikasi membaca latihan1_data.js.

## Memperbarui data

Letakkan CSV baru bernama latihan1.csv di folder proyek, lalu jalankan:

    cd D:\WebsiteDedel
    .\.venv\Scripts\python.exe convert_csv_to_js.py latihan1.csv latihan1_data.js

File JS yang dihasilkan berisi CSV yang dikompresi gzip dan dikodekan Base64. Ini mengecilkan file, tetapi bukan enkripsi: orang yang memiliki file dapat membukanya kembali.

## Mengunggah kode ke GitHub

1. Buat repository baru di GitHub. Buat repository kosong tanpa README agar perintah push pertama sederhana.
2. Ganti USERNAME dan NAMA-REPO di alamat repository pada perintah git remote add origin dengan milik Anda.
3. Jalankan perintah berikut dari PowerShell:

    cd D:\WebsiteDedel
    git init
    git add .gitignore streamlit_app.py requirements.txt convert_csv_to_js.py latihan1_data.js .streamlit/config.toml
    git commit -m "Siapkan dashboard Streamlit"
    git branch -M main
    git remote add origin https://github.com/USERNAME/NAMA-REPO.git
    git push -u origin main

Perintah git add memilih file untuk aplikasi Streamlit; folder .venv, CSV mentah, dan versi Flask tidak ikut diunggah.

Jika Git meminta identitas commit, atur nama dan email Git terlebih dahulu:

    git config --global user.name "Nama Anda"
    git config --global user.email "email-anda@example.com"

## Deploy di Streamlit Community Cloud

1. Buka https://share.streamlit.io dan masuk dengan akun GitHub.
2. Hubungkan akses repository bila diminta, lalu pilih Create app.
3. Pilih repository, branch main, dan entrypoint streamlit_app.py.
4. Di Advanced settings, pilih Python 3.14 bila tersedia (lingkungan lokal proyek ini menggunakan Python 3.14).
5. Tekan Deploy. Setelah build selesai, Streamlit memberikan URL untuk app.

## Menerbitkan pembaruan

Setelah mengedit kode atau membuat ulang latihan1_data.js, jalankan:

    cd D:\WebsiteDedel
    git add streamlit_app.py latihan1_data.js requirements.txt .streamlit/config.toml
    git commit -m "Perbarui dashboard"
    git push

Streamlit Community Cloud mendeteksi push baru dan membangun ulang app.
