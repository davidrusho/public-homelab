#!/usr/bin/env python3
"""
claude-hud statusline wrapper.

Post-processes the claude-hud plugin's rendered output to:
  1. Label each line with a bright, bold label (Session: / Git: / Context /
     Usage / Weekly / Tools: / Agents: / Todos: / Config:). claude-hud emits no
     labels; the activity lines (Tools/Agents/Todos) ship with none at all, so
     they're identified here by content signature.
  2. Lift the git status cluster (git:(...) / jj:(...)) onto its own "Git:" line
     and drop claude-hud's redundant "git:(" prefix (the label already says Git).
  3. Recolor every progress bar with a continuous "heat" gradient. The Context
     bar gets its OWN front-loaded ramp (hottest by ~50% fill — context filling
     toward 50% is already compaction-risk territory), distinct from the Usage /
     Weekly bars, which keep the full-width ramp (hottest at 100%).
  4. Trim the model badge: strip the "[ ]" brackets and the "(1M context)" tail
     so it reads "Opus 4.8" (the model itself stays dynamic — claude-hud emits
     whatever session model is live).
  5. Color the git diff stats: +N light green, -N light red.
  6. Compact the reset text to a muted clock glyph: "(resets at 05:50 PM)" ->
     "◷ 5:50pm". Requires claude-hud config `display.timeFormat: "absolute"`.

Palette: "Spectrum" — a full-spectrum ROYGBIV heat ramp tuned for a dark,
blue-tinted terminal. Static accents live in config.json.

claude-hud has no native option for any of these (confirmed against its source
and the author's README/GitHub docs), so this does light text surgery on the
rendered output. Requires `gitStatus.branchOverflow: "wrap"` so git is a
distinct " | "-delimited first-line segment.

If anything goes wrong, the raw claude-hud output is passed through unchanged.
Reversible: point statusLine back at claude-hud's dist/index.js.
Full write-up: https://thehomelab.lol
"""
import os
import re
import sys
import glob
import subprocess

NODE = "/opt/homebrew/bin/node"
SEP = " │ "  # the separator claude-hud joins first-line parts with

RESET = "\x1b[0m"
DIM = "\x1b[2m"
LABEL = "\x1b[1;38;2;234;240;255m"       # bold + bright #eaf0ff — the label color
GREEN = "\x1b[38;2;126;231;135m"         # #7ee787 — diff additions
RED = "\x1b[38;2;255;148;146m"           # #ff9492 — diff deletions
CLOCK = "◷"                              # reset glyph (replaces the word "resets")
CLOCK_COLOR = "\x1b[38;2;108;224;255m"   # #6ce0ff — cool clock glyph

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_OSC8 = re.compile(r"\x1b\]8;;[^\x1b\x07]*(?:\x07|\x1b\\)")

# A progress bar: an optional leading color, then a run of block/shade glyphs
# with interleaved SGR escapes (claude-hud emits <color>████<dim>░░░░<reset>).
_BAR = re.compile(r"(?:\x1b\[[0-9;]*m)*[█░](?:[█░]|\x1b\[[0-9;]*m)*")

# A colored percentage value (the "60%" after each bar). Only matches numbers
# that already carry an SGR color, i.e. the bar readouts — never bare counts.
_PCT = re.compile(r"(?:\x1b\[[0-9;]*m)+(\d+)%")

# Spectrum heat gradient: (position 0..1, (r, g, b)). indigo-blue -> red.
_HEAT = [
    (0.00, (77, 124, 255)),   # indigo-blue
    (0.22, (41, 211, 255)),   # cyan
    (0.44, (53, 224, 122)),   # green
    (0.64, (255, 210, 58)),   # yellow
    (0.82, (255, 138, 42)),   # orange
    (1.00, (255, 59, 92)),    # red
]

# claude-hud's environment line: "N CLAUDE.md | N rules | N MCPs | N hooks".
_ENV_LINE = re.compile(r"^\d+\s+(?:CLAUDE\.md|rules|MCPs?|hooks?)\b")
# git-files line at the bottom: "path(+33 -1)".
_GITFILES = re.compile(r"\([+-]\d+")

_MONTHS = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
_RESET_ABS = re.compile(r"\(resets at ([^)]*)\)")
_RESET_DATE = re.compile(rf"^((?:{_MONTHS}) \d{{1,2}}) (\d{{1,2}}):(\d{{2}}) (AM|PM)$")
_RESET_TIME = re.compile(r"^(\d{1,2}):(\d{2}) (AM|PM)$")

_BAR_LABELS = re.compile(r"(Context|Usage|Weekly)")
# elapsed times an agent line ends with: (12s) (<1s) (3m 5s) (1h 2m)
_ELAPSED = re.compile(r"\((?:<1s|\d+h \d+m|\d+m \d+s|\d+[smh])\)")


def strip_escapes(s: str) -> str:
    return _OSC8.sub("", _ANSI.sub("", s))


def mklabel(name: str) -> str:
    """A bright, bold label padded so its value lands in a common column."""
    pad = " " * max(1, 9 - len(name))
    return f"{RESET}{LABEL}{name}{RESET}{pad}"


def heat(frac: float, ramp: str = "full") -> tuple[int, int, int]:
    if ramp == "context":
        frac = frac * 2  # front-load: reach the hot end by ~50% fill
    frac = 0.0 if frac < 0 else 1.0 if frac > 1 else frac
    for i in range(len(_HEAT) - 1):
        f0, c0 = _HEAT[i]
        f1, c1 = _HEAT[i + 1]
        if frac <= f1:
            t = 0.0 if f1 == f0 else (frac - f0) / (f1 - f0)
            return (
                round(c0[0] + (c1[0] - c0[0]) * t),
                round(c0[1] + (c1[1] - c0[1]) * t),
                round(c0[2] + (c1[2] - c0[2]) * t),
            )
    return _HEAT[-1][1]


def _recolor_bars_seg(seg: str, ramp: str) -> str:
    def repl(m: re.Match) -> str:
        glyphs = [c for c in m.group(0) if c in "█░"]
        width = len(glyphs)
        if width == 0:
            return m.group(0)
        out = []
        for i, g in enumerate(glyphs):
            if g == "█":
                r, gr, b = heat(i / (width - 1) if width > 1 else 0.0, ramp)
                out.append(f"\x1b[38;2;{r};{gr};{b}m█")
            else:
                out.append(f"{DIM}░")
        out.append(RESET)
        return "".join(out)

    return _BAR.sub(repl, seg)


def _recolor_percents_seg(seg: str, ramp: str) -> str:
    def repl(m: re.Match) -> str:
        n = int(m.group(1))
        r, g, b = heat(min(100, n) / 100, ramp)
        return f"\x1b[38;2;{r};{g};{b}m{n}%"

    return _PCT.sub(repl, seg)


def _recolor_seg(seg: str, ramp: str) -> str:
    return _recolor_percents_seg(_recolor_bars_seg(seg, ramp), ramp)


def _recolor_line_bars(line: str) -> str:
    """Recolor bars on one line, choosing the ramp by the nearest preceding
    label: Context -> front-loaded ramp; Usage / Weekly -> full-width ramp."""
    parts = _BAR_LABELS.split(line)
    out = [_recolor_seg(parts[0], "full")]
    for k in range(1, len(parts), 2):
        lbl = parts[k]
        ramp = "context" if lbl == "Context" else "full"
        out.append(lbl)
        if k + 1 < len(parts):
            out.append(_recolor_seg(parts[k + 1], ramp))
    return "".join(out)


def recolor_bars(text: str) -> str:
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if "█" in line or "░" in line:
            lines[i] = _recolor_line_bars(line)
    return "\n".join(lines)


def _compact(hh: str, mm: str, ap: str) -> str:
    return f"{int(hh)}:{mm}{ap.lower()}"


def _reset_render(when: str) -> str:
    return f"{RESET}{CLOCK_COLOR}{CLOCK}{RESET}{DIM} {when}{RESET}"


def reformat_resets(text: str) -> str:
    def repl(m: re.Match) -> str:
        inside = m.group(1).strip()
        dm = _RESET_DATE.match(inside)
        if dm:
            date, hh, mm, ap = dm.groups()
            return _reset_render(f"{date}, {_compact(hh, mm, ap)}")
        tm = _RESET_TIME.match(inside)
        if tm:
            hh, mm, ap = tm.groups()
            return _reset_render(_compact(hh, mm, ap))
        return m.group(0)  # unexpected shape (e.g. 24h locale) — leave as-is

    return _RESET_ABS.sub(repl, text)


def clean_model(seg: str) -> str:
    """Strip the model badge's '[ ]' brackets and any '(… context)' tail, while
    leaving ANSI escapes (whose own '[' must not be touched) intact."""
    seg = re.sub(r"\s*\((?:[^()]*context[^()]*)\)", "", seg, flags=re.I)
    seg = re.sub(r"(?<!\x1b)\[(?=[A-Za-z])", "", seg, count=1)
    seg = re.sub(r"(?<!\x1b)\](?![0-9])", "", seg, count=1)
    return seg


def dedup_git(seg: str) -> str:
    """Drop claude-hud's 'git:(' / 'jj:(' prefix and the matching ')' — the
    'Git:' label already names it."""
    seg = re.sub(r"((?:\x1b\[[0-9;]*m)*)(?:git|jj):\(", r"\1", seg, count=1)
    seg = re.sub(r"((?:\x1b\[[0-9;]*m)*)\)((?:\x1b\[[0-9;]*m)*\s*)$", r"\1\2", seg, count=1)
    return seg


def _recolor_pm(line: str) -> str:
    line = re.sub(r"\+(\d+)", GREEN + r"+\1" + RESET, line)
    line = re.sub(r"-(\d+)", RED + r"-\1" + RESET, line)
    return line


def color_git_stats(text: str) -> str:
    """Color diff counts on git lines: +N green, -N red."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        s = strip_escapes(line)
        if s.lstrip().startswith("Git:") or _GITFILES.search(s):
            lines[i] = _recolor_pm(line)
    return "\n".join(lines)


def brighten_bar_labels(text: str) -> str:
    return _BAR_LABELS.sub(lambda m: f"{RESET}{LABEL}{m.group(1)}{RESET}", text)


def classify_activity(s: str) -> str | None:
    """Identify an unlabeled activity line by its content signature."""
    if s.startswith("▸"):
        return "Todos:"
    if _ELAPSED.search(s):
        return "Agents:"
    if re.search(r"×\d", s):
        return "Tools:"
    if re.search(r"\(\d+/\d+\)", s):
        return "Todos:"
    if s[:1] in ("✓", "◐"):
        return "Tools:"
    return None


def label_activity_lines(text: str) -> str:
    lines = text.split("\n")
    for i, line in enumerate(lines):
        s = strip_escapes(line).strip()
        if not s or s.startswith(("Session:", "Git:", "Config:", "Context", "Usage", "Weekly")):
            continue
        kind = classify_activity(s)
        if kind:
            lines[i] = mklabel(kind) + line
    return "\n".join(lines)


def term_columns() -> int:
    try:
        fd = os.open("/dev/tty", os.O_RDONLY)
        try:
            return os.get_terminal_size(fd).columns
        finally:
            os.close(fd)
    except Exception:
        return 120


def find_hud() -> str | None:
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude"))
    matches = glob.glob(
        os.path.join(config_dir, "plugins/cache/*/claude-hud/*/dist/index.js")
    )

    def ver_key(path: str):
        m = re.search(r"/claude-hud/(\d+)\.(\d+)\.(\d+)/", path)
        return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)

    return max(matches, key=ver_key) if matches else None


def node_bin() -> str:
    if os.path.exists(NODE):
        return NODE
    from shutil import which
    return which("node") or NODE


def is_git_segment(seg: str) -> bool:
    return re.match(r"(git|jj):\(", strip_escapes(seg).strip()) is not None


def split_session_git(output: str) -> str:
    lines = output.rstrip("\n").split("\n")
    if not lines or not lines[0].strip():
        return output

    segments = lines[0].split(SEP)
    git_seg = None
    kept = []
    for seg in segments:
        if git_seg is None and is_git_segment(seg):
            git_seg = seg
        else:
            kept.append(seg)

    if kept:
        kept[0] = clean_model(kept[0])

    out = [mklabel("Session:") + SEP.join(kept)]
    if git_seg is not None:
        out.append(mklabel("Git:") + dedup_git(git_seg))
    out.extend(lines[1:])
    return "\n".join(out)


def label_git_files_line(text: str) -> str:
    """Label the git-files line 'Files:' and rewrite claude-hud's cryptic
    untracked marker '?N' into readable '(N untracked)'. The line lists changed
    files (~modified / +added / -deleted with line diffs); it's the only line
    that starts with one of those markers, so that's how it's found."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        s = strip_escapes(line).strip()
        if not s or s[0] not in "~+-?":
            continue
        # "?1" (or "\x1b[2m?1\x1b[0m") -> readable, un-dimmed "(1 untracked)"
        new = re.sub(
            r"(?:\x1b\[2m)?\?(\d+)",
            lambda m: f"{RESET}({m.group(1)} untracked)",
            line,
        )
        lines[i] = mklabel("Files:") + new
        break
    return "\n".join(lines)


def label_config_line(text: str) -> str:
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if _ENV_LINE.match(strip_escapes(line).strip()):
            # claude-hud renders the config counts in ANSI dim; un-dim so they
            # read at the same normal-foreground brightness as the Tools names.
            content = line.replace(DIM, "")
            lines[i] = mklabel("Config:") + content
            break
    return "\n".join(lines)


def transform(output: str) -> str:
    reshaped = split_session_git(output)
    colored = reformat_resets(recolor_bars(reshaped))
    labeled = label_config_line(label_activity_lines(colored))
    labeled = label_git_files_line(labeled)
    return color_git_stats(brighten_bar_labels(labeled))


def main() -> int:
    data = sys.stdin.buffer.read()
    hud = find_hud()
    if not hud:
        sys.stdout.buffer.write(data)
        return 0

    env = dict(os.environ)
    env["COLUMNS"] = str(max(1, term_columns() - 4))

    try:
        proc = subprocess.run([node_bin(), hud], input=data, capture_output=True, env=env)
    except Exception:
        return 0
    raw = proc.stdout.decode("utf-8", errors="replace")
    if proc.returncode != 0 or not raw.strip():
        sys.stdout.write(raw)
        return 0

    try:
        result = transform(raw)
    except Exception:
        result = raw  # never let surgery break the statusline
    sys.stdout.write(result if result.endswith("\n") else result + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
