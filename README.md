# Yardmaster

Yardmaster is a release management tool for Flatcar Container Linux. It automates release orchestration across multiple channels (Alpha, Beta, Stable, LTS) and provides commands to prepare, validate, and tag releases.

## Requirements

- Python 3.10+
- `uv` for environment and dependency management

## Setup

```bash
# Install dependencies
make dev-install

# Copy and edit the config file
cp .yardmaster.yaml.sample .yardmaster.yaml
# Edit .yardmaster.yaml with your values
```

### Required environment variables

The config template references these env vars:

- `JENKINS_USER` and `JENKINS_TOKEN` for Jenkins
- `GPG_KEY_ID` if GPG signing is enabled

Export them before running release commands.

## Release workflow

```bash
# 1. Initialize release state from a GitHub issue
yardmaster release init https://github.com/flatcar/Flatcar/issues/1234

# 2. Check status
yardmaster status

# 3. Run pre-release steps (tagging, branching, Jenkins builds)
yardmaster release run --pre

# 4. Run post-release steps
yardmaster release run --post

# 5. Mark release as done
yardmaster release complete
```

Use `--dry-run` on any step to preview without making changes.

Useful options:

- `--dry-run`: show actions without executing them
- `--skip-jenkins`: skip triggering Jenkins builds
- `--skip-issue-check`: skip GitHub issue title verification
- `--force`: force tag creation if it already exists
- `-v`: verbose logging

### Retag

Retag a channel mid-release:

```bash
yardmaster retag alpha
```

### Status

View configured channels, planned releases, and release state:

```bash
yardmaster status
yardmaster status --show-sdk
yardmaster status --json
```

### SDK

Determine SDK versions for upcoming releases:

```bash
yardmaster sdk determine alpha:3800.0.0
```

### Jenkins

Trigger a Jenkins PR build:

```bash
yardmaster jenkins pr-build --dry-run flatcar scripts 1234
```

## Development

```bash
make dev-install   # install dev dependencies
make test          # run tests
make lint          # lint
make format        # auto-format
make type-check    # mypy
make check         # all of the above
make fix           # auto-fix formatting + lint
make all           # fix + check + build
make clean         # remove build artifacts
make help          # list all targets
```

## Notes

- Default config path: `.yardmaster.yaml`
- Sample config: `.yardmaster.yaml.sample`
- Workspace default: `~/.yardmaster/workspace`
- Logs default: `~/.yardmaster/yardmaster.log`

## Troubleshooting

If you see `Config file not found`, copy the sample config:

```bash
cp .yardmaster.yaml.sample .yardmaster.yaml
```

Then edit it with your values.

## Configuration

Yardmaster looks for `.yardmaster.yaml` in the current directory by default. You can override this with:

- **`YARDMASTER_CONFIG`** environment variable:

  ```bash
  export YARDMASTER_CONFIG=~/my-project/.yardmaster.yaml
  yardmaster status
  ```

- **`-c` flag** (takes precedence over the env var):

  ```bash
  yardmaster -c /path/to/config.yaml status
  ```
