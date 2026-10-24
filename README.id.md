<div align="center">

# OmniForge

**Toolkit open-source untuk AI coding assistant: skill manager, workflow, MCP, dan developer utilities.**

Python 3.11+ · MCP (stdio) · VS Code · MIT

**Bahasa:** [English](README.md) · **Bahasa Indonesia** · [Bahasa Melayu](README.ms.md)

</div>

OmniForge adalah *companion toolkit* untuk Codex, Claude Code, Cursor, OpenCode, Gemini, dan coding assistant lainnya. **Ini bukan model AI baru dan bukan pengganti coding agent.** Fokusnya adalah mencari, memasang, dan menggunakan skill yang relevan, dengan kontrol izin untuk aktivitas yang berisiko.

**Update 1.3.1:** Core tests sudah lulus di Linux, Windows dan macOS (Python 3.11/3.13), tersedia CodeQL, dependency checks, Dependabot, dan verified release-candidate workflow. Coverage branch-aware yang terukur sekitar 73%—belum semua code path teruji. [Arsitektur](docs/ARCHITECTURE.md) · [Release](docs/RELEASE_PROCESS.md) · [CLI preview](https://github.com/muhdmunir961-byte/omniforge/actions/workflows/preview.yml).

## Quick start

Pastikan Python 3.11+ dan Git sudah terpasang:

```bash
git clone https://github.com/muhdmunir961-byte/omniforge.git
cd omniforge
python -m pip install -e .
omniforge doctor
omniforge list
omniforge search "debug ESP32 errors"
```

Untuk menjalankan test: `python -m pip install pytest && python -m pytest -q`.

## Fitur utama

| Fitur | Cara pakai | Catatan |
|---|---|---|
| Skill search | `omniforge search "API errors"` | Pencarian hybrid lokal; embeddings opsional butuh model yang sudah terpasang |
| Lazy skill loading | `omniforge load log-triage` | Load satu `SKILL.md` saat dibutuhkan |
| Skill install | `omniforge install log-triage --agent codex --project .` | Tidak menimpa file tanpa `--force` |
| VS Code + MCP setup | `omniforge setup-vscode --project .` | Membuat konfigurasi `.vscode/mcp.json` |
| MCP server | `omniforge mcp` | Search, load, budget, dan preview aksi berisiko |
| Audit skill | `omniforge audit skills/my-skill` | Pemeriksaan heuristik, **bukan** antivirus |
| Validasi skill | `omniforge validate skills/my-skill` | Memeriksa struktur dan metadata |
| Buat template skill | `omniforge forge my-tool --description "..." --command tool` | Generate dokumen, bukan menjalankan tool asing |
| Eksekusi skill | `omniforge run firmware-preflight --approve` | Docker default; izin eksplisit wajib |
| Workflow DAG | `omniforge orchestrate workflow.json` | Mengatur dependency task; bukan autonomous reasoning |
| Browser automation | `omniforge browser --url https://example.org --approve` | Butuh Playwright dan Chromium |
| AI code editing (BYOK) | `omniforge code --task "refactor" --file app.py --endpoint URL --model MODEL` | Kirim file terpilih saja; preview patch sebelum apply |
| File integrity | `omniforge manifest --project .` | SHA-256, **tanpa tanda tangan digital** |
| Repository catalog | `omniforge catalog "firmware"` | 112 kandidat riset, **bukan** 112 integrasi aktif |

## Skill yang tersedia (14 paket)

**10 script bawaan:** `repo-recon`, `log-triage`, `dependency-inventory`, `sqlite-inspector`, `firmware-preflight`, `api-probe`, `python-symbols`, `git-diff-review`, `openapi-inventory`, dan `secret-hygiene`.

**4 adapter opsional:** `trivy-scan`, `kicad-drc`, `esptool-chip`, `browser-snapshot`. Integrasi aktual memerlukan tool upstream terinstal sendiri. OmniForge tidak membundel software pihak ketiga tersebut.

## Cara kerja

```text
Developer → Codex / Claude / AI lain
                 ↓
             OmniForge
       ├─ Cari skill
       ├─ Baca SKILL.md seperlunya
       ├─ Jalankan skill yang disetujui
       ├─ Atur urutan task
       ├─ Browser automation
       └─ Preview AI code patch
                 ↓
              Hasil
```

**Contoh:** ketika backend error, agent dapat mencari `log-triage`, membaca instruksi skill, lalu menggunakan terminal yang memiliki izin untuk menjalankan pemeriksaan log. OmniForge sendiri tidak melakukan autonomous debugging secara menyeluruh.

## Eksekusi aman dengan Docker

Preview tanpa menjalankan proses:

```bash
omniforge run firmware-preflight
```

Menjalankan di Docker (image harus kamu download dulu):

```bash
docker pull python:3.13-alpine
omniforge run firmware-preflight --approve
```

Sandbox menggunakan mount read-only, membatasi resource, menonaktifkan jaringan secara default, dan menjalankan proses memakai UID/GID pengguna pada Linux. Kualitas isolasi tetap bergantung pada konfigurasi Docker host.

Untuk script dengan argumen:

```bash
omniforge run --unsafe-local --approve python-symbols -- main.py
```

**Peringatan:** `--unsafe-local` menjalankan kode di host tanpa sandbox. Gunakan hanya untuk kode tepercaya.

## Workflow multi-task

Buat `workflow.json`:

```json
{
  "tasks": [
    {"id": "hardware", "kind": "skill", "skill": "firmware-preflight"},
    {"id": "repository", "kind": "skill", "skill": "repo-recon", "depends_on": ["hardware"]}
  ]
}
```

```bash
omniforge orchestrate workflow.json
omniforge orchestrate workflow.json --approve
```

Task `kind: "agent"` bisa memanggil CLI agent eksternal dengan executable dan argumen yang diizinkan melalui `--allow-command <name>`. Agent eksternal tidak disediakan atau diautentikasi oleh OmniForge.

## Browser automation

```bash
python -m pip install playwright
python -m playwright install chromium
omniforge browser --url https://example.org --approve
```

File aksi `--actions actions.json` dapat memuat `click`, `fill`, `wait`, `goto`, dan `screenshot`. Akses private network dan navigasi lintas domain dibatasi secara default; `--allow-local` khusus situs lokal yang memang kamu izinkan.

## AI code editing (Bring Your Own Key)

```bash
omniforge code --task "refactor the parser" --file parser.py \
  --endpoint https://YOUR-PROVIDER.example/v1/chat/completions \
  --model YOUR-MODEL --allow-remote
```

Set `OMNIFORGE_API_KEY` di environment jika provider memerlukannya. Default-nya hanya menampilkan diff. Gunakan `--apply` setelah review. OmniForge memeriksa SHA-256 file asal, membuat backup, dan tidak mengeksekusi shell command yang dihasilkan model. Ini *single-pass assisted editing*, bukan autonomous coding agent.

## Keamanan MCP

MCP menyediakan `omniforge_search`, `omniforge_load`, `omniforge_budget`, `omniforge_run`, dan `omniforge_browser`.

**Dua tool terakhir hanya preview.** Agent tidak bisa memberikan persetujuan eksekusi lewat parameter `approve: true`. Untuk menjalankan aksi nyata, pengguna harus memanggil CLI lokal sendiri dengan `--approve`.

## Token & pencarian

OmniForge menggunakan lazy loading supaya dokumentasi semua skill tidak perlu dikirim sekaligus. `omniforge budget --selected log-triage` hanya memperkirakan token dengan rasio karakter/4, **bukan** pengukuran biaya API yang akurat.

Mode embeddings opsional memerlukan `sentence-transformers` dan model lokal yang sudah tersedia; model tidak di-download otomatis.

## Hasil pengujian v1.1.1

- **Python 3.11, 3.12, 3.13:** masing-masing 64 test lulus pada Linux.
- **Docker:** eksekusi skill dan workflow dua task berhasil di container sungguhan.
- **Browser:** Chromium membuka situs localhost, mengisi form, klik, dan menyimpan screenshot.
- **AI editing:** request HTTP ke mock server lokal, preview, apply, dan backup berhasil.
- **VS Code:** VSIX berhasil dibuat dan command CLI berjalan di Extension Development Host Linux.

Bukti: [Unit CI](https://github.com/muhdmunir961-byte/omniforge/actions/runs/40100657232) · [Real E2E CI](https://github.com/muhdmunir961-byte/omniforge/actions/runs/40100657217).

**Batasan:** Belum memverifikasi seluruh provider AI eksternal, semua website, Windows/macOS, atau semua skenario keamanan. Extension belum dipublikasikan ke VS Code Marketplace. Ini bukan jaminan *production security*.

Dokumentasi lanjutan: [Release Audit](RELEASE_AUDIT.md) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md).

## Blockchain provenance (v1.2.0)

**Support MCP:** AI assistant bisa pakai `omniforge_chain_verify` dan `omniforge_chain_proof` secara read-only. Agent nggak bisa menulis ledger, sign wallet, atau broadcast transaksi melalui MCP.


OmniForge sekarang punya **local hash-chain ledger** buat mencatat integritas snapshot project/skill, plus opsi *on-chain anchoring* di jaringan Ethereum-compatible. Local ledger **bukan blockchain terdesentralisasi**. Kalau mau catat bukti ke EVM sungguhan, kamu perlu wallet sendiri dan gas fee. OmniForge nggak meminta private key atau otomatis mengirim transaksi.

```bash
omniforge blockchain record --project . --note "rilis baru"
omniforge blockchain verify --project . --check-current
omniforge blockchain proof --project . --height 0

# Siapkan unsigned transaction (belum dikirim ke blockchain)
omniforge blockchain anchor --project . --wallet 0xALAMAT_WALLET_KAMU --chain-id 1337

# Setelah kamu approve + broadcast melalui wallet:
omniforge blockchain verify-anchor --project . --wallet 0xALAMAT_WALLET_KAMU --chain-id 1337 --rpc-url http://127.0.0.1:8545 --tx-hash 0xHASH_TRANSAKSI_KAMU
```

File ledger disimpan di `.omniforge/chain.jsonl`. Yang dicatat hanya hash SHA-256, jumlah file, timestamp, dan catatan singkat—bukan konten source code. Kalau seseorang bisa mengubah semua isi ledger lokal, ia juga bisa menghitung ulang seluruh chain. Anchor yang diverifikasi secara independen memberikan bukti lebih kuat; **bukan jaminan siapa pembuat kode atau bahwa kode itu aman**. Dokumentasi lengkap: [Blockchain Guide](docs/BLOCKCHAIN.md).

## OF-Provenance v2 — integrity ledger yang diaudit

**API baru tanpa merusak versi lama:** `ofprov` atau `omniforge provenance`. Command lama `omniforge blockchain` v1 tetap tersedia dan hash/anchor lamanya tidak diubah.

```bash
ofprov init --project .
ofprov snapshot --project . --note "before release"
ofprov verify --project . --check-files
ofprov audit --project .
ofprov backup --project . --out ../trusted-backup-001
```

v2 menyimpan **hash SHA-256 tiap file dan full scan policy di setiap record**. Strict verifier menolak duplicate JSON key, field tambahan, path tak aman dan perubahan policy tanpa izin. `--expected-head` dan `--expected-seq` harus dibandingkan dengan checkpoint yang disimpan **di luar project** supaya full ledger rewrite bisa terdeteksi.

Kalau sudah pakai ledger v1, gunakan `ofprov migrate --project . --approve`, lalu `ofprov snapshot --project .`. Migrasi menyalin data v1 byte-for-byte, bukan menghitung ulang hash lama.

EVM anchor tetap **opt-in**: aplikasi cuma menyiapkan unsigned transaction setelah `--ack-public-data`. Wallet eksternal harus approve dan sign sendiri. RPC receipt yang disimpan lokal bukan bukti finalitas blockchain terkini. MCP v2 hanya menyediakan verify/proof/audit **read-only**.

**Penting:** local ledger bukan blockchain decentralized, hash bukan bukti ownership/safety kode, dan user harus menyimpan backup plus trusted checkpoint secara terpisah. Detail: [panduan BM](docs/PROVENANCE_V2.ms.md) dan [JSON schema](docs/PROVENANCE_V2_SCHEMA.json).

## Lisensi

MIT untuk kode OmniForge. Software upstream tetap menggunakan lisensinya masing-masing.
