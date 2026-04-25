# Kuis Cerdas Cermat Multiplayer

Aplikasi kuis realtime dengan buzzer menggunakan WebSocket.

## Cara jalankan lokal

1. Instal dependencies:
   ```bash
   npm install
   ```
2. Jalankan server:
   ```bash
   npm start
   ```
3. Buka browser host:
   ```text
   http://localhost:8000/
   ```
4. Buka HP siswa pada alamat yang sama dengan IP host:
   ```text
   http://<IP_HOST>:8000/
   ```

## Hosting yang mendukung multiplayer

GitHub Pages tidak mendukung WebSocket, jadi aplikasi ini harus dideploy ke layanan yang menyediakan server Node.js.

Rekomendasi layanan:

- Railway (https://railway.app)
- Render (https://render.com)
- Fly.io (https://fly.io)
- Heroku (jika masih tersedia)

### Deploy cepat dengan Railway

1. Buat repository GitHub dan push project ini.
2. Buat akun Railway dan pilih "New Project" > "Deploy from GitHub".
3. Pilih repository project `kuis-cerdas-cermat`.
4. Pastikan `Root Directory` kosong atau `.`.
5. Set `Install Command` jadi `npm install`.
6. Set `Start Command` jadi `npm start`.
7. Deploy.
8. Setelah berhasil, aplikasi akan tersedia di URL Railway.

### URL siswa

Setelah deploy, siswa bisa membuka URL yang diberikan oleh Railway, misalnya:

```text
https://your-app-name.railway.app/
```

Host dan siswa membuka URL yang sama, kemudian siswa memasukkan kode room yang dibuat oleh host.

## Catatan

- Pastikan semua siswa membuka URL yang sama.
- Host harus membuat room terlebih dahulu.
- Koneksi multiplayer hanya bekerja jika backend WebSocket berjalan.
