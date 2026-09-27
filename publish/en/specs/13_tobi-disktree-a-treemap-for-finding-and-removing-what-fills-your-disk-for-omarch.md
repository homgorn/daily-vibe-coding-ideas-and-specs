---
title: "tobi/disktree — A treemap for finding and removing what fills your..."
description: "A treemap for finding and removing what fills your disk, for Omarchy. Rust + GPUI."
tags: []
idea_id: 13
date: 2026-09-28
viability_score: 50
viability_confidence: 50
status: draft
origin: research
canonical: https://homgorn.github.io/daily-vibe-coding-ideas-and-specs/specs/13
---

# tobi/disktree — A treemap for finding and removing what fills your...

> A treemap for finding and removing what fills your disk, for Omarchy. Rust + GPUI.

## Metadata
- **Idea ID**: 13
- **Date**: 2026-09-28
- **Viability Score**: 50/100 (confidence: 50%)
- **Status**: spec
- **Origin**: research
- **Tags**: 

## Problem

Disk space exhaustion is a common issue for developers and power users on Linux systems. Existing tools like `ncdu`, `baobab`, or `du` provide textual or basic graphical representations but lack:

1. **Intuitive spatial visualization** — Treemaps (rectangular area-proportional maps) enable instant identification of largest directories/files at a glance, unlike tree lists or bar charts.
2. **Native Omarchy integration** — Omarchy (an Arch-based opinionated desktop) users lack a first-party, performant, GPU-accelerated disk analyzer that matches the desktop's aesthetic and workflow [source:1].
3. **Safe, interactive deletion** — Most CLI tools require separate `rm` commands; GUI tools often lack direct "delete from visualization" workflow with confirmation.
4. **Performance on large filesystems** — Electron/web-based tools struggle with millions of inodes; Rust + GPUI (GPU UI) enables 60 FPS rendering and fast scanning via parallel I/O.

**Impact**: Wasted time hunting space hogs, accidental deletions, and friction in maintenance workflows.

## Solution

**tobi/disktree** — A native Rust application using GPUI (GPU-accelerated UI framework) that provides:

- **Treemap visualization**: Rectangular, area-proportional representation of disk usage, colored by type/depth, with zoom/pan/drill-down.
- **Real-time scanning**: Parallel directory traversal with progress indication; incremental updates on filesystem changes (via `notify`/`inotify`).
- **Integrated deletion**: Right-click → "Move to Trash" or "Delete Permanently" with confirmation dialog; updates treemap instantly.
- **Omarchy-first design**: Follows Omarchy theming (Catppuccin), keybindings (Vim-like), and packaging (AUR/official repo target).
- **Keyboard-centric UX**: `hjkl` navigation, `/` filter, `d` delete, `r` rescan, `?` help — no mouse required.
- **Cross-filesystem support**: Handles bind mounts, btrfs subvolumes, network shares (via FUSE) gracefully.

**Tech stack**: Rust 2024 edition, GPUI (from Zed), `ignore`/`walkdir` for scanning, `trash` crate for safe deletion, `clap` for CLI entry (`disktree [PATH]`).

**MVP scope (2-4 weeks)**: Core treemap rendering, scanning + deletion, Omarchy theme, keyboard nav, AUR package. Stretch: filter bar, export SVG/PNG, multiple root view.

## Target User

**Primary**: Omarchy users (Arch Linux power users who value minimal, keyboard-driven, GPU-accelerated tooling). They:
- Run rolling-release Arch; comfortable with AUR/makepkg.
- Prefer Rust/GPUI native apps over Electron/GTK.
- Manage large codebases, containers, VMs, media libraries — need frequent disk audits.
- Use Vim/Helix, terminal-first workflows; expect `hjkl`, command palette, no bloat.

**Secondary**: General Arch/EndeavourOS/Garuda users seeking a fast, pretty `ncdu` alternative with GUI deletion.

**Tertiary**: Linux developers on any distro who want a standalone binary (AppImage/static) for quick disk forensics.

**Non-goals**: Windows/macOS support (GPUI is Linux-first), multi-user/server dashboards, cloud storage analysis.

## Key Features

### MVP (Must Have)
1. **Treemap rendering** — Squarified algorithm (Bruls et al.), GPU-instanced rectangles via GPUI; tooltip on hover shows path/size/percentage.
2. **Parallel scanner** — `rayon`-powered walk with `ignore` crate (respects `.gitignore`, `.dockerignore`); emits progress events to UI.
3. **Interactive deletion** — Context menu / `d` key → confirm → `trash::delete` (respects `XDG_TRASH_HOME`); immediate UI removal + size recalculation.
4. **Keyboard navigation** — `hjkl`/`arrows` move focus; `Enter`/`l` drill down; `Backspace`/`h` up; `/` fuzzy filter (path/name); `r` rescan; `q`/`Esc` quit.
5. **Omarchy theming** — Catppuccin Mocha/Latte via GPUI theme system; respects `GTK_THEME` fallback.
6. **CLI entry** — `disktree [PATH]` (default `$PWD`); `--help`/`--version`; `--no-delete` flag for read-only mode.
7. **Packaging** — `PKGBUILD` for AUR; static `musl` binary for universal Linux.

### Post-MVP (Should Have)
8. **Filter bar** — Persistent regex/glob filter with syntax highlighting; saves last 10 patterns.
9. **Export** — `Ctrl+E` → Save treemap as SVG (vector) or PNG (raster) for reports.
10. **Multiple roots** — Tabbed view for `/`, `/home`, `/mnt/data` simultaneously.
11. **Btrfs/ZFS awareness** — Show subvolume/snapshot boundaries; exclude snapshots by default.
12. **Docker/container volumes** — Detect `/var/lib/docker/overlay2` and label layers.

### Non-Functional
- **Startup < 200ms** (cold, SSD) for 100k inodes.
- **60 FPS** pan/zoom at 4K on integrated GPU (Intel UHD / AMD iGPU).
- **Memory < 150 MB** for 1M inodes.
- **Zero telemetry**; no network calls.
- **Accessibility**: High-contrast mode; screen-reader labels via GPUI's accessibility tree.

## Tech Stack & Architecture

**Language**: Rust (confirmed by repository language) [source:1]

**UI Framework**: GPUI (explicitly stated in project description) [source:1]

**Target Platform**: Omarchy (Arch-based Linux distribution) [source:1]

**Application Type**: Desktop GUI application for disk usage visualization and management

**Architecture Pattern**: Likely client-side only (no backend) — treemap rendering and filesystem scanning run locally

**Key Dependencies (inferred from domain)**:
- GPUI for GPU-accelerated UI rendering
- Rust standard library + filesystem APIs (std::fs, walkdir or similar)
- Possible: `ignore` crate for .gitignore-aware scanning
- Possible: `serde` for configuration persistence

**Build System**: Cargo (standard for Rust projects)

**Distribution**: Likely binary release via GitHub Releases; possibly AUR package for Omarchy/Arch users

**Unknown**: Exact GPUI version, minimum Rust version, additional crates, CI/CD configuration, testing framework

## Data Model

**Core Entities**:

1. **FileSystemNode** — Represents a file or directory in the scanned tree
   - `path: PathBuf` — Absolute path
   - `name: String` — Basename
   - `size: u64` — Size in bytes (file size or recursive directory size)
   - `node_type: NodeType` — File | Directory | Symlink | Other
   - `children: Option<Vec<FileSystemNode>>` — Populated for directories after scan
   - `modified: SystemTime` — Last modification time
   - `permissions: Metadata` — Unix permissions (for deletion authorization)

2. **ScanRoot** — User-selected root path for analysis
   - `path: PathBuf`
   - `label: String` — User-friendly name (e.g., "Home", "Root")
   - `total_size: u64` — Cached total for progress display

3. **TreemapRect** — Computed layout for GPU rendering
   - `x, y, width, height: f32` — Normalized or pixel coordinates
   - `node_id: usize` — Reference to FileSystemNode
   - `depth: usize` — Nesting level for color/label logic

4. **SelectionState** — UI interaction state
   - `selected_nodes: HashSet<usize>` — Node IDs marked for deletion
   - `hovered_node: Option<usize>` — For tooltip/detail panel
   - `focused_path: Option<PathBuf>` — Current drill-down path

5. **AppConfig** — Persisted user preferences
   - `recent_roots: Vec<PathBuf>`
   - `show_hidden: bool`
   - `color_scheme: ColorScheme`
   - `confirm_deletion: bool`

**Data Flow**:
- User selects ScanRoot → Background scan builds FileSystemNode tree → TreemapRect layout computed → GPUI renders rectangles → User selects nodes → Deletion confirmation → `std::fs::remove_file` / `remove_dir_all` → Tree updates incrementally

**Unknown**: Exact struct definitions, serialization format for config, error handling model, async scan implementation details

## API / Interfaces

No public API documented. The application is a standalone GUI tool built with Rust and GPUI for Omarchy. Internal interfaces likely include: filesystem scanning module (traversing directories, computing sizes), treemap layout engine (squarified algorithm), GPUI view components (rendering, interaction), and deletion confirmation dialogs. All communication is in-process. External interfaces: none. [source:1]

## UI/UX Requirements

Treemap visualization: rectangles proportional to file/directory size, color-coded by type or depth. Interactions: click to drill down, right-click context menu for delete, keyboard navigation (arrows, Enter, Backspace). Toolbar: path breadcrumb, refresh, settings (color scheme, filter). Deletion: confirmation modal with size impact, undo toast. Responsive layout adapts to window size. Dark/light theme following Omarchy conventions. Accessibility: high contrast, focus indicators, screen reader labels. Performance: incremental scanning, virtualized rendering for large trees. [source:1]

## Monetization

Unknown. The project is an open-source Rust/GPUI treemap disk analyzer for Omarchy hosted on GitHub with 1,161 stars [source:1]. No licensing, pricing, or commercial model information is available in the source materials.

## Risks & Mitigation

**Technical Risks**
- GPUI framework maturity: GPUI is a relatively new Rust UI framework; API instability or missing widgets could delay MVP features.
- Disk scanning performance: Recursive filesystem traversal on large volumes may block the UI thread; requires async/background scanning with progress reporting.
- Platform specificity: Targeting Omarchy (Arch-based) limits testing surface; filesystem edge cases (btrfs subvolumes, bind mounts, FUSE) may behave differently.

**Maintenance Risks**
- Single-maintainer bus factor: Repository shows single author (tobi); no CONTRIBUTING.md or governance documented in sources.
- Dependency churn: Rust ecosystem moves fast; GPUI and disk I/O crates may introduce breaking changes.

**Mitigations**
- Implement scanning in a separate thread with channel-based UI updates.
- Abstract filesystem access behind a trait to enable mocking and cross-platform tests.
- Publish clear contribution guidelines and issue templates to distribute maintenance.

## Launch Checklist

**Pre-MVP (Weeks 1-2)**
- [ ] Scaffold Rust + GPUI project with Cargo workspace
- [ ] Implement background directory scanner (walkdir/ignore) emitting sized entries
- [ ] Build treemap layout algorithm (squarified) rendering to GPUI canvas
- [ ] Add keyboard navigation (arrows, enter, backspace) and tooltip with path/size

**MVP (Weeks 3-4)**
- [ ] Integrate delete confirmation dialog (move to trash via `trash` crate)
- [ ] Package for Omarchy: create PKGBUILD for AUR and/or binary release via GitHub Actions
- [ ] Add README with install instructions, keybindings, and screenshots
- [ ] Tag v0.1.0 and publish release notes

**Post-Launch**
- [ ] Monitor issue tracker for crash reports on btrfs/ZFS/FUSE
- [ ] Add `--exclude` CLI flag for common noise (node_modules, .git, caches)
- [ ] Investigate GPUI accessibility support for screen readers

## Cited Sources

[1] https://github.com/tobi/disktree

> *Partial spec: Interfaces and UX: unparseable response (attempt 1). Sections that failed are marked above.*

## Launch Commands (Copy to IDE)

### Claude Code
```bash
claude -p "$(cat SPEC.md)"
```

### OpenCode
```bash
opencode run "$(cat SPEC.md)"
```

### Codex CLI
```bash
codex exec "$(cat SPEC.md)"
```

### Cursor
```bash
cursor agent -p "$(cat SPEC.md)"
```

### Antigravity
```bash
antigravity run "$(cat SPEC.md)"
```

---
*Generated by Daily Vibe Coding Engine — 2026-09-28*
