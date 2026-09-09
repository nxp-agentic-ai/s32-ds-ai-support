# Scripts

Utility scripts for building and the .whl files and creating the .pyz installer

---

## Build scripts

`build_modules.py` and `create_deploy_package.py` are helper scripts that produce `.whl` artifacts and `.pyz` installer package.
These scripts require the following packages in the active Python environment:

| Package | Min. version | Purpose |
|---------|-------------|---------|
| `build` | ≥ 1.0 | `build_modules.py` calls `python -m build` to produce `.whl` artifacts for all sub-packages and the root meta-package |
| `setuptools` | ≥ 61.0 | Backend declared in every `pyproject.toml` (`setuptools.backends.legacy:build`) |
| `wheel` | any recent | Required by the `setuptools` backend to emit `.whl` archives |

Dependencies are installed via
```shell
pip install build setuptools wheel
```

### Build steps

```shell
# 1. Build all sub-package wheels + the root meta-package wheel (root is built by default)
python scripts/build_modules.py

# Skip the root meta-package if needed:
# python scripts/build_modules.py --no-root

# 2. Bundle everything into a self-installing .pyz
python scripts/create_deploy_package.py

# Custom output path:
# python scripts/create_deploy_package.py --output dist/nxp-mcp.pyz

# Full help:
python scripts/build_modules.py --help
python scripts/create_deploy_package.py --help
```

> `create_deploy_package.py` depends only on the Python standard library; no extra packages beyond the three above are needed at deploy-package creation time.
---

`create_deploy_package.py` - Build self-installing deployment package

Assembles a single, self-contained **`.pyz`** (Python zip-application) that bundles all sub-package wheels, asset directories, and an installer entry point.  The resulting file can be copied to any machine and installed with a single `python` call - no build toolchain required on the target.

### Prerequisites

`build_modules.py` must be run first to produce the `.whl` files in `dist/`:

```shell
python scripts/build_modules.py
python scripts/create_deploy_package.py
```

### Usage

```shell
python scripts/create_deploy_package.py [--version X.Y.Z] [--output <path>]
```

| Argument | Default | Description |
|---|---|---|
| `--version X.Y.Z` | read from `[project].version` in `pyproject.toml` | Version string to stamp into the installer banner and output filename |
| `--output <path>` | `dist/nxp-mcp-installer-<ver>.pyz` | Full output path for the `.pyz` file |

The version is resolved in this order:
1. `--version` CLI argument (if supplied)
2. `[project].version` from the root `pyproject.toml` (default)

`scripts/installer/_manifest.py` holds a `@@VERSION@@` placeholder for `VERSION`.  The script substitutes the resolved version **in memory** when writing the manifest into the archive - the source file on disk is never modified.

### Examples

```shell
rem Standard build - version read automatically from pyproject.toml
python scripts/create_deploy_package.py

rem Override version explicitly
python scripts/create_deploy_package.py --version 1.0.0

rem Custom output path
python scripts/create_deploy_package.py --output dist/nxp-mcp.pyz
```

### What gets bundled

| Content | Archive path |
|---|---|
| Installer entry point | `__main__.py` |
| Installer manifest | `_manifest.py` |
| All `.whl` files from `dist/` | `whl/<filename>.whl` |
| Loose files declared in `_manifest.ASSET_FILES` | as declared (e.g. `README.md`, `run-mcp.bat`, `run-mcp.sh`, `LICENSE`) |
| Directories declared in `_manifest.ASSET_DIRS` | as declared (e.g. `knowledge_db/`, `models/`, `skills/`, `configs/`) |

The full asset list is defined in `scripts/installer/_manifest.py`.  Add or remove entries there - no code changes to `create_deploy_package.py` are needed.

The script validates that the root meta-package WHL (`nxp_mcp-*.whl`) is present and that all `nxp-mcp-*` sub-package dependencies it declares are bundled.  It exits with an error if anything is missing.

### Installing the `.pyz` on the target machine

```shell
rem Default install location
python s32ds-agentic-ai-installer-{version}.pyz

rem Install to a custom directory
python s32ds-agentic-ai-installer-{version}.pyz --dest C:\NXP\s32ds-agentic-ai

rem Silent install - no confirmation prompts
python s32ds-agentic-ai-installer-{version}.pyz --dest C:\NXP\s32ds-agentic-ai --yes
```

---