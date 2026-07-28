# claude-hud statusline wrapper

A Python wrapper that post-processes the [claude-hud](https://github.com/jarrodwatts/claude-hud)
statusline plugin for Claude Code, adding line labels, a continuous color gradient on the
progress bars, and a few readability edits that the plugin does not expose as config.

claude-hud does the hard part: reading Claude Code's statusline JSON and rendering context
usage, rate-limit windows, tool activity, running agents, todos, and git state. This wrapper
only rewrites the text it prints.

## What it changes

| Change | Detail |
|---|---|
| Line labels | `Session:` `Git:` `Tools:` `Agents:` `Todos:` `Config:` `Files:`. claude-hud emits no line labels, and the activity lines ship with none at all, so they are identified by content signature. |
| Git on its own line | Lifts the `git:(...)` cluster off line 1 and drops the now-redundant `git:(` prefix. |
| Gradient bars | Repaints each bar cell by cell across a six-stop ROYGBIV ramp, so a 60% bar no longer looks like a 0% bar. Natively the color only changes at the 75% and 90% thresholds. |
| Front-loaded context ramp | The Context bar reaches the hot end of the ramp by roughly 50% fill. Usage and Weekly bars keep the full-width ramp. |
| Trimmed model badge | `[Opus 4.8 (1M context)]` renders as `Opus 4.8`. The model name itself stays dynamic. |
| Colored diff stats | `+N` green, `-N` red. `?N` becomes `(N untracked)`. |
| Compact reset text | `(resets at 05:50 PM)` becomes `◷ 5:50pm`. |

## Requirements

- macOS or Linux, Python 3.10+ (the type hints use `str | None`)
- Node.js, since claude-hud itself is a Node program
- claude-hud installed as a Claude Code plugin

The Node path is hard-coded to `/opt/homebrew/bin/node` with a `which node` fallback. Edit the
`NODE` constant at the top if yours lives elsewhere.

## Install

1. Install claude-hud first and confirm it renders on its own:

   ```
   /plugin marketplace add jarrodwatts/claude-hud
   /plugin install claude-hud
   /reload-plugins
   /claude-hud:setup
   ```

2. Copy `claude-hud-session-wrapper.py` to `~/.claude/` and make it executable:

   ```bash
   cp claude-hud-session-wrapper.py ~/.claude/
   chmod +x ~/.claude/claude-hud-session-wrapper.py
   ```

3. Merge `config.json` into `~/.claude/plugins/claude-hud/config.json`. Four keys are
   load-bearing for the wrapper:

   - `gitStatus.branchOverflow: "wrap"` so git becomes its own ` │ `-delimited segment
   - `display.timeFormat: "absolute"` so reset text is parseable as `(resets at <time>)`
   - `display.sevenDayThreshold: 0` so the weekly usage bar is always visible
   - `elementOrder` with `environment` last

4. Point `statusLine.command` in `~/.claude/settings.json` at the wrapper:

   ```json
   {
     "statusLine": {
       "type": "command",
       "command": "bash -c 'exec python3 \"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/claude-hud-session-wrapper.py\"'"
     }
   }
   ```

5. Restart Claude Code.

## Revert

Point `statusLine.command` back at claude-hud's own `dist/index.js`. Nothing else needs undoing.

## Caveats

This is text surgery on another program's rendered output, so it carries the obvious risks:

- It assumes line 1 is `[model] │ project │ git:(…)` split on ` │ `. A claude-hud release that
  changes that format breaks the reshaping. Failures fall through to raw output rather than a
  blank statusline.
- The Context ramp is selected by matching the literal word `Context`. If that word is ever
  renamed or localized, the bar silently falls back to the full-width ramp.
- Activity line labels are inferred from content signatures, so a future format collision could
  produce a wrong label.
- Re-running `/claude-hud:configure` can rewrite `config.json` and reset the four keys above.
  Re-check them after any configure run.
- The bar gradient overrides claude-hud's semantic bar colors, where hue means healthy, warning,
  or critical. Severity now reads from fill length plus the warm end of the ramp.
