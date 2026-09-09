# S32CT Get Version - Worked Examples

## Example 1 - Standalone S32CT install

**Input** *(uses MCP server defaults)*:

```python
nxp_s32ct_execute_action(action_name="s32ct.env_version", params={})
```

**Output:**

```
S32 Configuration Tools 1.7.0 (framework 12.4) at C:/NXP/S32ConfigTools
```

Install is present, version is fully identified, launcher was reachable.

---

## Example 2 - S32DS-integrated S32CT install

**Input** *(explicit override - bypasses server defaults)*:

```python
nxp_s32ct_execute_action(
    action_name="s32ct.env_version",
    params={
        "installation_path": "C:/NXP/S32DS.3.5/eclipse",
        "s32ct_launcher": "C:/NXP/S32DS.3.5/eclipse/s32dsc.exe",
    },
)
```

**Output:**

```
S32 Configuration Tools (integrated in S32 Design Studio 3.5) at C:/NXP/S32DS.3.5/eclipse
```

Install is the integrated variant; version follows the parent S32DS
version.

---

## Example 3 - Version metadata missing

**Input** *(default install, but the framework metadata file is absent)*:

```python
nxp_s32ct_execute_action(action_name="s32ct.env_version", params={})
```

**Output:**

```
S32 Configuration Tools (version unknown) at C:/NXP/S32ConfigTools
```

Path resolved, launcher reachable, but no version file could be parsed.
Downstream skills are safe to run with caveats - the caller should log
`version = unknown` for reproducibility.

---

## Example 4 - Misconfigured path

**Input:**

```python
nxp_s32ct_execute_action(
    action_name="s32ct.env_version",
    params={
        "s32ct_launcher": "D:/wrong/path/toolsc.exe",
    },
)
```

**Output:**

```
S32 Configuration Tools not found at the configured path 'D:/wrong/path/toolsc.exe'
```

Escalate: do not invoke any other S32CT skill until the launcher path
is corrected.

---

## Metadata sources

S32CT does not expose a public `-version` CLI flag. The skill therefore
reads version metadata from these sources in order:

1. The Eclipse `.eclipseproduct` file in the installation root.
2. The framework version file shipped with the installation.
3. The version embedded in the launcher executable's file metadata.
4. Last resort: parse the installation directory name (e.g.
   `S32ConfigTools_1.7.0`).

If none of these is available, the skill returns `version = "unknown"`
rather than failing - the resolved path is still useful diagnostic
information.
