# Five-minute OmniForge local demo

This example works without a model API key, a wallet, Docker or network access
after the package has been installed.

```bash
git clone https://github.com/muhdmunir961-byte/omniforge.git
cd omniforge
python -m pip install -e .
omniforge doctor
omniforge search "debug API errors"
omniforge load log-triage
```

Use a **disposable sample project**, not the library's own repository, when
experimenting with provenance:

```bash
mkdir example-project
printf 'answer = 42\n' > example-project/main.py
ofprov init --project example-project
ofprov snapshot --project example-project --note "first snapshot"
ofprov verify --project example-project --check-files
ofprov audit --project example-project
```

Next, change `main.py` and run `ofprov verify --check-files` again. The
verification should return nonzero and identify the modified file. You can
take a new snapshot only after reviewing the change.

To see **real CLI results captured by CI**, open the Packaged CLI Preview
workflow in GitHub Actions and download its HTML/Markdown/JSON artifact.

Further reading: [architecture](../../docs/ARCHITECTURE.md),
[security](../../SECURITY.md), [provenance](../../docs/PROVENANCE_V2.ms.md).
