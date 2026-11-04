# HERESY — The Gremlin Files

A read-only, interactive **evidence corkboard** for all twelve HERESY investigations. Ten are in the default harness, one has confirmed out-of-harness Louvain observations, and one CUDA assertion case is blocked after executed preflight.

- **HTML:** accessible semantic layout, keyboard-focusable evidence cards, native modal dossiers.
- **CSS:** textured cork, scattered note paper, pushpins, labels, industrial lettering and responsive layouts.
- **JavaScript:** case search, evidence-status filters, keyboard-accessible dossier details and GitHub/SOFA source links.
- **Canvas 2D:** connecting red strings behind the relevant case files, redrawn only on layout changes.
- **Data:** `cases.json` is a deliberately reviewed static snapshot grounded in experiment manifests and the SOFA publication registry. It contains no receipt fabrications or live execution claims.
- **Privacy:** zero cookies, analytics, external scripts, package managers, API fetches or autonomous publishing. The only load-time fetch is the same-origin `cases.json`.

## Run locally

From the **repository root**, use Python's standard-library HTTP server:

```sh
python3 -m http.server 8000 -d site
```

Then open `http://localhost:8000`. Opening `index.html` with a `file://` URL may block its same-origin JSON fetch by browser security policy. This is expected; use a local HTTP server.

## Static checks

```sh
python3 -m unittest discover -s tests -p 'test_corkboard.py' -v
```

The tests check all twelve case IDs, each status and formal title against its original `experiment.json`, the documented case-file paths, six case-linked SOFA publications against `sofa/manifest.json`, the source-locked 005/006 report outcomes, red-thread graph references, local asset dependencies, and native Canvas/modal features. They **do not** constitute browser rendering, accessibility certification or additional experiment execution.

## GitHub Pages deployment

1. Merge the reviewed corkboard PR to `main`.
2. Visit [Repository Settings → Pages](https://github.com/QSOLKCB/HERESY-SOFA/settings/pages).
3. Under **Build and deployment**, select **Source: GitHub Actions**. The GitHub plugin can commit the workflow but cannot change this repository administrative setting.
4. **Explicitly approve publication:** use Actions → **HERESY Corkboard — static Pages** → **Run workflow**, select `main`, and start the manual `workflow_dispatch`. Pushes and pull requests validate the site but **never deploy it automatically**.
5. The expected Pages URL, **only after GitHub reports successful deployment**, is `https://qsolkcb.github.io/HERESY-SOFA/`.

The workflow uploads `site/` as the artifact and uses GitHub's official Pages deployment actions. It does not modify branch settings, credentials, repository secrets or any archival data.

## Evidence boundaries

- **CAUGHT / REPRODUCER** means an implemented bounded experiment exists. `HERESY-004` verifies byte normalization on Linux, **not Windows cmd.exe**.
- **WANTED** is reserved for the unconfirmed CUDA assertion hypothesis: `HERESY-005` compiled and executed device preflight, but no assertion trial ran (`NOT_RUN`, no 710). The published SOFA TIL documents only this narrower observation.
- **OBSERVED** means a successful, source-locked standalone experiment without default-harness promotion. `HERESY-006` observed 42 legitimate Louvain cycle partitions in 240 configurations under NetworkX 3.5. It does **not** establish a NetworkX contract violation, and its manifest remains a `placeholder` with `entrypoint: null`.
- **Both placeholder manifests are excluded from `run-all`**. The display status is a second, explicitly named evidence axis, not a mutation of harness eligibility.
- **ON SOFA** means the manifest records a separately published and verified-to-exist contribution, not that this website submits anything. The 005 contribution reports preflight only; 006 is a reproducibility/verification Blueprint.
- `HERESY-011` records separate Python x86-64/ARM64 reproduction and upstream TOMBSTONE Rust evidence; these are not conflated.
- `HERESY-012` reproduces only the JUnit parameter-identity bookkeeping flaw on synthetic Python XML; QEC #623 live-socket/Ed25519 CI is separately reported upstream, never attributed to this site.
- Red strings are thematic links between cases, not cryptographic or scientific causality.

All controls are client-side. To add a case, update its source experiment first, then curate `site/cases.json`, preserving the exact manifest identity and status. The `evidenceState` field is independent of the harness manifest's `status` and must not imply an unexecuted hardware test. The static tests will fail if an invalid publication or missing source path is introduced.

> The compiler is innocent. The corkboard is not.
