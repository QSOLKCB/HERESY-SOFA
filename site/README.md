# HERESY — The Gremlin Files

A read-only, interactive **evidence corkboard** for all eleven HERESY experiments.

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

The tests check all eleven case IDs, each status and formal title against its original `experiment.json`, the documented case-file paths, the four SOFA publications against `sofa/manifest.json`, red-thread graph references, local asset dependencies, and native Canvas/modal features. They **do not** constitute browser rendering, accessibility certification or additional experiment execution.

## GitHub Pages deployment

1. Merge the reviewed corkboard PR to `main`.
2. Visit [Repository Settings → Pages](https://github.com/QSOLKCB/HERESY-SOFA/settings/pages).
3. Under **Build and deployment**, select **Source: GitHub Actions**. The GitHub plugin can commit the workflow but cannot change this repository administrative setting.
4. Run **HERESY Corkboard — static Pages** from the Actions tab with `workflow_dispatch`, or use the push-to-main deployment triggered by the merge.
5. The expected Pages URL, **only after GitHub reports successful deployment**, is `https://qsolkcb.github.io/HERESY-SOFA/`.

The workflow uploads `site/` as the artifact and uses GitHub's official Pages deployment actions. It does not modify branch settings, credentials, repository secrets or any archival data.

## Evidence boundaries

- **CAUGHT / REPRODUCER** means an implemented bounded experiment exists. `HERESY-004` verifies byte normalization on Linux, **not Windows cmd.exe**.
- **WANTED** means an untested placeholder, not an executed incident. `HERESY-005` and `HERESY-006` remain untested.
- **ON SOFA** means the manifest records a published contribution, not that a new post was sent by this website.
- `HERESY-011` records separate Python x86-64/ARM64 reproduction and upstream TOMBSTONE Rust evidence; these are not conflated.
- Red strings are thematic links between cases, not cryptographic or scientific causality.

All controls are client-side. To add a case, update its source experiment first, then curate `site/cases.json`, preserving the exact manifest identity and status. The static tests will fail if an invalid publication or missing source path is introduced.

> The compiler is innocent. The corkboard is not.
