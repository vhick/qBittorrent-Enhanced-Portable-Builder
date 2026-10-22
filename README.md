# qBittorrent Enhanced Edition — True Portable Builder v1.0

Build a Windows x64 PortableApps-style ZIP from the **official c0re100 release**, with **no installer execution** on Windows. The application uses the officially supported `--profile` command-line option to keep its settings and torrent session history in `Data`.

**Upstream:** https://github.com/c0re100/qBittorrent-Enhanced-Edition  
**Official releases:** https://github.com/c0re100/qBittorrent-Enhanced-Edition/releases  
**Native portable mode:** https://github.com/qbittorrent/qBittorrent/wiki/How-to-use-portable-mode

## 1. Use the builder (no coding required)

1. Create a new **public or private** GitHub repository, e.g. `qBittorrent-Enhanced-Portable-Builder`.
2. Extract the builder kit ZIP on your PC, then upload **all its contents** into the **root of the repository**. Preserve the hidden `.github/workflows/` folder.
3. Commit the files. GitHub can take a moment to show the new workflow under **Actions**.
4. Go to **Actions > Build qBittorrent Enhanced Portable (Manual) > Run workflow**.
5. Leave `upstream_tag` as `latest`, or specify a release tag like `release-5.2.4.10`. Press **Run workflow**.
6. When the job succeeds, download the artifact named `qBittorrent-Enhanced-Portable-Windows-x64`.
7. Unzip the artifact, then unzip the **application ZIP inside it**. You will get a single `qBittorrentEnhancedPortable` folder.
8. Run **`qBittorrentEnhancedPortable.exe`** in that folder. You do not need to install qBittorrent or Python.

**Note:** The builder ZIP only contains GitHub source/workflow files. GitHub Actions creates the finished Windows application ZIP; it is not bundled into this kit. The artifact is retained for **1 day**, so download it after a successful run.

## 2. The final app structure

```
qBittorrentEnhancedPortable/
├── qBittorrentEnhancedPortable.exe    <- LAUNCH THIS
├── App/
│   ├── qBittorrent/
│   │   ├── qbittorrent.exe
│   │   └── [upstream DLLs, Qt plugins, translations...]
│   └── AppInfo/
│       ├── appinfo.ini
│       ├── appicon.ico                 <- ORIGINAL multi-size upstream icon
│       ├── appicon_16.png
│       ├── appicon_32.png
│       └── ...
├── Data/
│   ├── profile/                       <- ALL qBittorrent preferences and resume data
│   ├── Downloads/                     <- default on first launch
│   └── portable-root.txt              <- created on first launch
└── Other/
    ├── PORTABLE-README.txt
    └── Source/
```

The package's `Data` folder is EMPTY at build time. The launcher creates preferences on first start. This avoids an upgrade accidentally overwriting older settings.

## 3. How it stays portable

- Official `--profile=<folder>` directs config, logs, saved .torrent files and resume state into `Data/profile`.
- The launcher creates `Data/Downloads` and sets it as the **initial default downloads directory** if no previous preferences exist.
- The launcher uses the original Windows icon embedded in official `qbittorrent.exe`; no generic icons.
- No installer is executed, and the builder does not register file extensions, startup entries, desktop shortcuts, magnet handlers or Explorer context-menu commands.
- Does NOT require administrator rights or an NTFS junction. No need to copy/delete host AppData before/after launching.
- External programs (file manager, WebUI browser, antivirus, Windows firewall, network stacks) can create host traces. This is profile portability, not a virtual machine or full OS sandbox.

**Do not launch `App/qBittorrent/qbittorrent.exe` directly**: it would bypass the root launcher, potentially use a different profile, and might write to host AppData.

## 4. Updates WITHOUT losing data

1. Exit qBittorrent fully, including the tray icon, and wait for all torrents to stop.
2. Back up the whole `Data` directory.
3. Run the builder again using `latest`. Download the new app ZIP.
4. From the new ZIP, replace the existing root `qBittorrentEnhancedPortable.exe`, `App` folder and `Other` folder.
5. **Keep the original `Data` directory**. Never overwrite or delete it.
6. Launch again. Your saved torrents and settings should return.

**Moving PC or drive letters:** The launcher adjusts its *own default* `Data/Downloads` value when a previously recorded root path changes. It does NOT rewrite saved torrent file locations or move download files. If drive letters change, existing torrents may show missing files until you correct the save paths (e.g. choose the new location and force-recheck). Back up Data before migration.

If you had installed qBittorrent previously and want to migrate the prior settings, first back up both `%APPDATA%\qBittorrent` and `%LOCALAPPDATA%\qBittorrent`. Their layout may differ by version, so migrate carefully and verify your torrents before deleting anything. The builder never touches installed settings.

## 5. Good practice / optional integrations

For maximum portability, leave **start with Windows**, **magnet or .torrent association**, and other system integration options OFF. You can drag `.torrent` files onto the portable launcher or use **File > Add Torrent Link**.

Built-in WebUI exposes a network interface: use a strong password, restrict remote access and keep the app up to date. Do not assume portability makes torrenting private or anonymous.

Use torrents only for content you are allowed to download or distribute.

## 6. Build failures

- **Cannot find Windows x64 installer**: Upstream changed its asset naming. See `scripts/resolve_release.py`; the workflow fails instead of silently choosing a 32-bit/Linux asset.
- **Installer SHA256 mismatch**: workflow stops; do not bypass the check.
- **7-Zip extraction failed**: find this step in Actions logs; attach the log ZIP if asking for help.
- **Original icon extraction failed**: attach the log. We do not substitute a generic icon.
- **Launcher C# path compilation error**: workflow passes ABSOLUTE paths for `.cs` and `.ico`; this addresses the earlier AyuGram path issue.
- **App won't open**: verify that the ZIP was completely extracted; keep the Qt plugin folders under `App/qBittorrent`.

## Technical notes

- Python 3.12 on Windows GitHub runner; `pefile` extracts original full-resolution PE icon group, Pillow makes menu PNGs.
- Windows .NET Framework C# compiler builds root launcher as small GUI `exe` (no separate .NET runtime required beyond Windows Framework availability).
- Uses GitHub release API (public upstream) and verifies release asset `sha256:` digest if GitHub publishes one.
- Only one ZIP artifact, manual Actions trigger, 1-day retention.
- No continuous synchronization, automatic release monitoring or scheduled builds.

## Testing status

The kit includes offline tests and ZIP inspection. The actual Windows workflow needs a GitHub Actions run; the Linux authoring environment cannot execute the compiled Windows app.
