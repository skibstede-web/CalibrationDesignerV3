# START_HERE.md — How to use these files

## 1. Place files

Copy all files from this package into:

```text
C:\Users\Erik\Documents\Projects\CalibrationDesignerV3
```

The final project root should contain:

```text
AGENTS.md
SPEC.md
BUILD_PLAN.md
TEST_PLAN.md
README.md
CODEX_START_PROMPT.md
START_HERE.md
.gitignore
.codex\config.toml
```

## 2. Open the project

Open this folder in either:

- the Windows Codex app, or
- VS Code with Codex.

Project folder:

```text
C:\Users\Erik\Documents\Projects\CalibrationDesignerV3
```

## 3. Check Codex permissions

This package includes:

```text
.codex\config.toml
```

It is configured for an unattended workspace-limited run:

```text
sandbox_mode = "workspace-write"
approval_policy = "never"
```

This is intended to let Codex work inside the project folder without repeated approvals.

It is deliberately **not** configured as `danger-full-access`.

## 4. Start Codex

In Codex, paste the full content of:

```text
CODEX_START_PROMPT.md
```

Then let Codex run.

## 5. Expected result

Codex should build the full app, run tests, and create:

```text
dist\CalibrationDesignerV3_beta_YYYYMMDD_HHMMSS.zip
```

## 6. If Codex gets blocked

If Codex cannot install dependencies because network access is blocked, either approve dependency installation once or temporarily set this in `.codex\config.toml`:

```toml
[sandbox_workspace_write]
network_access = true
```

It is already set to `true` in this starter package because you asked for an unattended end-to-end build.

## 7. If the unattended run fails

Do not restart with a vague prompt.

Use a targeted prompt such as:

```text
Read the latest failing test output. Fix only the failing tests and related implementation. Do not change the app scope. Run pytest again.
```

or:

```text
Continue from the current project state. Complete the next incomplete milestone in BUILD_PLAN.md. Run tests before moving on.
```
