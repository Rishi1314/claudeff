# allow-all

One command to stop Claude Code from prompting for permission on every action.

## Install

```bash
# Everything at once (recommended)
git clone https://github.com/Rishi1314/claudeff && python claudeff/install.py

# Just this tool
python claudeff/cli/allow-all/allow_all.py
```

Patches `~/.claude/settings.json` in place, preserving any existing config.

## What it does

Adds all standard Claude Code tools to `permissions.allow` in your settings file:

```json
{
  "permissions": {
    "allow": [
      "Bash", "Read", "Edit", "Write",
      "WebFetch", "Grep", "Glob", "LS",
      "MultiEdit", "NotebookRead", "NotebookEdit",
      "TodoRead", "TodoWrite", "WebSearch"
    ]
  }
}
```

Claude Code reads this on startup — no restart needed for the next session.

## Options

```
python allow_all.py            # apply (safe to run repeatedly)
python allow_all.py --dry-run  # preview without writing
python allow_all.py --undo     # remove the added permissions
python allow_all.py --path /path/to/settings.json  # custom path
```

## Demo

```
$ python cli/allow-all/allow_all.py
Added 14 permissions:
  + Bash
  + Read
  + Edit
  + Write
  + WebFetch
  + Grep
  + Glob
  + LS
  + MultiEdit
  + NotebookRead
  + NotebookEdit
  + TodoRead
  + TodoWrite
  + WebSearch

Saved to /home/you/.claude/settings.json
Claude Code will no longer prompt for permission on these tools.
```
