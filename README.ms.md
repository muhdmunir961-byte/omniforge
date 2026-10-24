<div align="center">

# OmniForge

**Toolkit open-source untuk AI coding assistant: skill manager, workflow, MCP dan developer utilities.**

Python 3.11+ · MCP (stdio) · VS Code · MIT

**Bahasa:** [English](README.md) · [Bahasa Indonesia](README.id.md) · **Bahasa Melayu**

</div>

OmniForge ialah *companion toolkit* untuk Codex, Claude Code, Cursor, OpenCode, Gemini dan coding assistant lain. **Ia bukan model AI baharu dan bukan pengganti AI coding agent.** Fungsinya membantu agent mencari, memasang dan menggunakan skill yang sesuai, dengan kawalan kebenaran bagi tindakan berisiko.

**Kemas kini 1.3.1:** Core tests sudah lulus pada Linux, Windows dan macOS (Python 3.11/3.13), dengan CodeQL, dependency checks, Dependabot, dan verified release-candidate workflow. Coverage branch-aware yang diukur sekitar 73%—belum semua laluan kod diuji. [Seni bina](docs/ARCHITECTURE.md) · [Release](docs/RELEASE_PROCESS.md) · [CLI preview](https://github.com/muhdmunir961-byte/omniforge/actions/workflows/preview.yml).

## Quick start

Pastikan Python 3.11+ dan Git tersedia:

```bash
git clone https://github.com/muhdmunir961-byte/omniforge.git
cd omniforge
python -m pip install -e .
omniforge doctor
omniforge list
omniforge search "debug ESP32 errors"
```

Untuk test: `python -m pip install pytest && python -m pytest -q`.

## Fungsi utama

| Fungsi | Cara guna | Had |
|---|---|---|
| Skill search | `omniforge search "API errors"` | Carian hybrid tempatan; embeddings perlukan model yang sudah dipasang |
| Lazy skill loading | `omniforge load log-triage` | Baca satu `SKILL.md` apabila diperlukan |
| Pasang skill | `omniforge install log-triage --agent codex --project .` | Tidak overwrite tanpa `--force` |
| VS Code + MCP setup | `omniforge setup-vscode --project .` | Jana `.vscode/mcp.json` |
| MCP server | `omniforge mcp` | Search, load, budget dan preview tindakan berisiko |
| Audit skill | `omniforge audit skills/my-skill` | Semakan heuristik, **bukan** antivirus |
| Validate skill | `omniforge validate skills/my-skill` | Semak struktur dan metadata |
| Jana template | `omniforge forge my-tool --description "..." --command tool` | Jana dokumentasi, bukan jalankan tool asing |
| Jalankan skill | `omniforge run firmware-preflight --approve` | Docker secara default, perlukan approval |
| Workflow DAG | `omniforge orchestrate workflow.json` | Susun task mengikut dependency; bukan autonomous reasoning |
| Browser automation | `omniforge browser --url https://example.org --approve` | Perlukan Playwright dan Chromium |
| AI code editing (BYOK) | `omniforge code --task "refactor" --file app.py --endpoint URL --model MODEL` | Hantar fail terpilih, preview patch sebelum apply |
| Integriti fail | `omniforge manifest --project .` | SHA-256, **tidak ditandatangani secara digital** |
| Repo catalog | `omniforge catalog "firmware"` | 112 calon kajian, **bukan** 112 integrasi aktif |

## Skill yang disertakan (14 pakej)

**10 skrip terbina dalam:** `repo-recon`, `log-triage`, `dependency-inventory`, `sqlite-inspector`, `firmware-preflight`, `api-probe`, `python-symbols`, `git-diff-review`, `openapi-inventory` dan `secret-hygiene`.

**4 adapter pilihan:** `trivy-scan`, `kicad-drc`, `esptool-chip`, `browser-snapshot`. Untuk integrasi sebenar, tool upstream mesti dipasang secara berasingan. OmniForge tidak membundel software pihak ketiga tersebut.

## Macam mana OmniForge bekerja?

```text
Developer → Codex / Claude / AI lain
                 ↓
             OmniForge
       ├─ Cari skill
       ├─ Baca SKILL.md bila perlu
       ├─ Jalankan skill yang diluluskan
       ├─ Susun urutan task
       ├─ Browser automation
       └─ Preview AI code patch
                 ↓
               Hasil
```

**Contoh:** bila backend error, agent boleh cari `log-triage`, baca arahan skill, kemudian guna terminal dengan permission yang sesuai untuk semak log. OmniForge sendiri bukan autonomous debugger yang menyelesaikan semua masalah tanpa bantuan.

## Eksekusi terkawal dengan Docker

Preview tanpa menjalankan proses:

```bash
omniforge run firmware-preflight
```

Jalankan dalam Docker (download image sendiri dahulu):

```bash
docker pull python:3.13-alpine
omniforge run firmware-preflight --approve
```

Sandbox menggunakan read-only mounts, had resource, rangkaian dimatikan secara default dan UID/GID pengguna pada Linux. Tahap isolation tetap bergantung pada konfigurasi Docker host.

Contoh dengan argumen skrip:

```bash
omniforge run --unsafe-local --approve python-symbols -- main.py
```

**Amaran:** `--unsafe-local` menjalankan kod terus pada host tanpa sandbox. Guna hanya untuk kod yang dipercayai.

## Workflow berbilang task

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

Task `kind: "agent"` boleh memanggil agent CLI luaran menggunakan executable dan argumen yang dibenarkan melalui `--allow-command <name>`. Agent luaran tidak disediakan atau diautentikasi oleh OmniForge.

## Browser automation

```bash
python -m pip install playwright
python -m playwright install chromium
omniforge browser --url https://example.org --approve
```

Fail `--actions actions.json` boleh mengandungi tindakan `click`, `fill`, `wait`, `goto` dan `screenshot`. Private network dan cross-domain navigation disekat secara default; `--allow-local` hanya untuk laman tempatan yang dibenarkan.

## AI code editing (Bring Your Own Key)

```bash
omniforge code --task "refactor the parser" --file parser.py \
  --endpoint https://YOUR-PROVIDER.example/v1/chat/completions \
  --model YOUR-MODEL --allow-remote
```

Tetapkan `OMNIFORGE_API_KEY` dalam environment jika perlu. Secara default, OmniForge hanya memaparkan diff. Guna `--apply` selepas semakan. Sistem menyemak SHA-256 fail asal, menyimpan backup dan tidak menjalankan shell command yang dijana model. Ini *single-pass assisted editing*, bukan autonomous coding agent.

## Keselamatan MCP

MCP menyediakan `omniforge_search`, `omniforge_load`, `omniforge_budget`, `omniforge_run` dan `omniforge_browser`.

**Dua tool terakhir hanya preview.** Agent tidak boleh meluluskan pelaksanaan melalui `approve: true`. Untuk tindakan sebenar, pengguna perlu menjalankan CLI tempatan sendiri dengan `--approve`.

## Token dan carian

Lazy loading mengurangkan keperluan menghantar semua dokumentasi skill sekali gus. `omniforge budget --selected log-triage` cuma menganggarkan token berdasarkan karakter/4, **bukan** meter bil API sebenar.

Mode embeddings pilihan memerlukan `sentence-transformers` dan model tempatan yang sudah tersedia. Model tidak dimuat turun secara automatik.

## Hasil ujian v1.1.1

- **Python 3.11, 3.12, 3.13:** 64 ujian lulus bagi setiap versi di Linux.
- **Docker:** skill dan workflow dua task berjaya dijalankan dalam container sebenar.
- **Browser:** Chromium membuka localhost, mengisi borang, klik dan menyimpan screenshot.
- **AI editing:** permintaan HTTP kepada mock server tempatan, preview, apply dan backup lulus.
- **VS Code:** VSIX berjaya dibina dan arahan CLI berfungsi dalam Extension Development Host Linux.

Bukti: [Unit CI](https://github.com/muhdmunir961-byte/omniforge/actions/runs/40100657232) · [Real E2E CI](https://github.com/muhdmunir961-byte/omniforge/actions/runs/40100657217).

**Had:** Belum mengesahkan semua provider AI luaran, laman web pihak ketiga, Windows/macOS atau semua ancaman keselamatan. Extension belum diterbitkan ke VS Code Marketplace. Ini bukan jaminan keselamatan production.

Dokumentasi lanjut: [Release Audit](RELEASE_AUDIT.md) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md).

## Blockchain provenance (v1.2.0)

**Sokongan MCP:** AI assistant boleh guna `omniforge_chain_verify` dan `omniforge_chain_proof` secara read-only. Agent tidak boleh menulis ledger, sign wallet atau broadcast transaksi melalui MCP.


OmniForge sekarang ada **local hash-chain ledger** untuk merekod integriti snapshot projek/skill, serta pilihan *on-chain anchoring* pada rangkaian Ethereum-compatible. Local ledger **bukan blockchain terdesentralisasi**. Untuk rekod bukti ke EVM sebenar, pengguna perlukan wallet dan membayar gas fee sendiri. OmniForge tidak meminta private key atau menghantar transaksi secara automatik.

```bash
omniforge blockchain record --project . --note "versi baharu"
omniforge blockchain verify --project . --check-current
omniforge blockchain proof --project . --height 0

# Sediakan transaksi yang belum ditandatangani
omniforge blockchain anchor --project . --wallet 0xALAMAT_WALLET_ANDA --chain-id 1337

# Selepas pengguna approve dan broadcast melalui wallet:
omniforge blockchain verify-anchor --project . --wallet 0xALAMAT_WALLET_ANDA --chain-id 1337 --rpc-url http://127.0.0.1:8545 --tx-hash 0xHASH_TRANSAKSI_ANDA
```

Ledger disimpan dalam `.omniforge/chain.jsonl`. Ia menyimpan hash SHA-256, jumlah fail, timestamp dan nota ringkas—bukan kandungan source code. Sesiapa yang boleh mengubah semua rekod tempatan masih boleh menjana semula hash; anchor yang diperiksa secara bebas memberi bukti lebih kukuh. **Ini bukan pengesahan hak milik, lesen atau keselamatan kod.** Rujuk [Blockchain Guide](docs/BLOCKCHAIN.md).

## OF-Provenance v2 — ledger integriti yang diaudit

**API baharu tanpa memutuskan versi lama:** `ofprov` atau `omniforge provenance`. Arahan lama `omniforge blockchain` v1 kekal dan hash/anchor terdahulu tidak ditulis semula.

```bash
ofprov init --project .
ofprov snapshot --project . --note "sebelum release"
ofprov verify --project . --check-files
ofprov audit --project .
ofprov backup --project . --out ../trusted-backup-001
```

v2 menyimpan **hash SHA-256 setiap fail dan polisi scan penuh dalam setiap rekod**. Verifier ketat menolak duplicate JSON key, medan tambahan, path berbahaya dan perubahan polisi tanpa kelulusan. `--expected-head` bersama `--expected-seq` mesti dibanding dengan checkpoint yang disimpan **di luar projek** untuk mengesan penulisan semula sejarah.

Jika ada ledger v1, jalankan `ofprov migrate --project . --approve`, kemudian `ofprov snapshot --project .`. Migrasi menyalin rekod v1 byte-for-byte tanpa menukar hash lama.

EVM anchor kekal **opt-in**: OmniForge hanya menyediakan unsigned transaction selepas `--ack-public-data`. Wallet luar mesti meluluskan, menandatangani dan menghantar sendiri. Receipt RPC dalam journal tempatan tidak dianggap bukti blockchain terkini. MCP v2 hanya menawarkan verify/proof/audit **read-only**.

**Amaran:** local ledger bukan blockchain terdesentralisasi, hash bukan bukti hak milik atau keselamatan kod, dan simpan backup + trusted checkpoint secara berasingan. Panduan lanjut: [OF-Provenance v2](docs/PROVENANCE_V2.ms.md) dan [JSON schema](docs/PROVENANCE_V2_SCHEMA.json).

## Lesen

MIT untuk kod OmniForge. Software upstream kekal dengan lesen masing-masing.
