# qBittorrent Enhanced Edition Portable Builder v1.2

A manually triggered, ZIP-only Windows x64 GitHub Actions builder for [c0re100/qBittorrent-Enhanced-Edition](https://github.com/c0re100/qBittorrent-Enhanced-Edition), with an isolated built-in Python runtime for **qBittorrent Search and Jackett plugins**.

## What v1.2 fixes

Previous portable builds isolated the qBittorrent profile, but depended on the Windows computer to have an appropriate Python executable for search plugins. If there wasn't one, or qBittorrent failed to locate it, **all search plugins, including Jackett, could fail together**.

This version downloads a verified, official **CPython 3.14.10 Windows x64 embeddable package** from python.org and packages it under `App/Python`. The launcher writes the correct absolute Python path into qBittorrent's own `Data/profile/config/qBittorrent/qBittorrent.ini` `[Preferences]` section (`Search\pythonExecutablePath`), making the path automatically update if the portable drive letter changes. No Python installation, system PATH modification, registry setting, or admin access is required.

Python 3.14.10 was published October 25, 2026 with important security fixes. Because third-party plugin scripts vary, **we cannot guarantee every plugin supports Python 3.14 yet**. The build checks the bundled interpreter and key standard-library modules; running a real search still requires an interactive Windows test.

The original application icon is extracted from the publisher's executable. The original installer is **extracted, never executed**. No plugins are downloaded or installed without user action.

## How to build (browser only)

1. Download and extract this builder ZIP.
2. Open your existing `qBittorrent-Enhanced-Portable-Builder` GitHub repository.
3. Upload all the extracted files to the repository root, preserving `.github/workflows/build-portable.yml`, and **replace the previous versions**. Commit to `main`.
4. Click **Actions → Build qBittorrent Enhanced Portable (Manual) → Run workflow**. Leave `upstream_tag` set to `latest`, or choose a published tag such as `release-5.2.4.10`.
5. When it succeeds, download the `qBittorrent-Enhanced-Portable-Windows-x64` artifact. Inside it is the final portable application ZIP.
6. **Completely exit** your old portable qBittorrent, including its tray icon. Make a copy of your entire **old `Data` folder**.
7. Extract the new application ZIP into a temporary location. **Replace your old `App`, `Other`, and root `qBittorrentEnhancedPortable.exe`** with the new files; **keep your existing `Data` folder unchanged**.
8. Launch using the root **`qBittorrentEnhancedPortable.exe`**. Open **Tools → Options → Advanced → Python executable path**. It should point inside your portable folder at `App\Python\python.exe` (without surrounding quotation marks). Check **View → Search Engine** and try a trusted plugin.

**Do not use “Re-run jobs” on the old run.** Trigger a new run after committing v1.2. The artifact is kept for one day.

## The final portable ZIP

```text
qBittorrentEnhancedPortable/
├── qBittorrentEnhancedPortable.exe        ← launch this
├── App/
│   ├── qBittorrent/                       ← original untouched program and Qt libraries
│   │   └── qbittorrent.exe
│   ├── Python/                            ← official portable Python 3.14.10
│   │   ├── python.exe
│   │   ├── python314.zip
│   │   ├── python314._pth
│   │   └── ...
│   └── AppInfo/                           ← PortableApps Menu metadata and original icon
│       ├── appinfo.ini
│       ├── appicon.ico
│       └── appicon_*.png
├── Data/
│   ├── profile/                           ← settings, search plugins, cached .torrent files
│   └── Downloads/                         ← default download folder
└── Other/
    ├── PORTABLE-GUIDE.md
    ├── Launcher-Source.cs
    ├── build-info.json
    └── SOURCE-LICENSES.txt
```

`Data` is shipped empty (directories only), so the new ZIP cannot overwrite any personal settings or plugin files when you update correctly.

## Jackett and other search plugins

The **Jackett Python plugin** and the **Jackett server/application** are different programs. Bundling Python makes qBittorrent able to run Python plugins, but **does not install or run the Jackett service**. Keep your existing Jackett server running before you search, and confirm its API key and address are correct.

1. Open qBittorrent Search → **Search plugins…** and confirm the plugin you want is listed and enabled. If needed, install trusted plugins from the [official search-plugins repository](https://github.com/qbittorrent/search-plugins/wiki/Install-search-plugins).
2. Jackett's official plugin is at `https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/jackett.py`. Its `jackett.json` configuration must live **beside the installed `jackett.py` inside the portable profile's search engines folder**, normally `Data\profile\data\qBittorrent\nova3\engines\` (check your actual folder). Do not place API keys in the builder repository.
3. Open the Jackett application and copy its API Key into your existing private `jackett.json`. The default URL is `http://127.0.0.1:9117` when both apps are on the same PC. Restart qBittorrent after editing the config.
4. If the plugin still fails, first check Python in **Tools → Options → Advanced**, then check Jackett's actual server status, URL and API key. An outdated third-party plugin, firewall or proxy can also prevent searches.

**Never share a populated `Data` folder** or `jackett.json`: it can contain passwords, WebUI credentials, torrent history and API keys.

## Portability and upgrade notes

- All normal qBittorrent preferences, search plugins and Jackett plugin configuration are preserved under `Data/profile` using the official `--profile` feature. The launcher patches only the search Python preference and (only if moving drives) a matching old `Data/Downloads` default value. Existing per-torrent save locations are **never** blindly changed.
- A one-time backup of your original preferences is saved as `qBittorrent.ini.portable-pre-python.bak` in the same portable config folder before the first v1.2 edit.
- Settings such as **torrent associations**, **start with Windows**, default-client status and Windows firewall integrations may still write to the host OS if you enable them in the program; this is portable **profile isolation**, not a virtual machine and not a guarantee of zero OS traces.
- Python may be updated in a future builder version because security fixes matter. Using an embedded runtime means you should rebuild periodically when a new supported Python version is available.
- The GitHub workflow checks official Python SHA-256 against the published Python Software Foundation hash and checks the GitHub qBittorrent release digest when available.
- **Compatibility limit:** a plugin may rely on removed Python modules or break with a newer interpreter. If only one plugin fails and others work, the plugin is likely the problem; do not wipe your entire `Data` folder.

## Testing / troubleshooting

The workflow tests the actual bundled Python executable, several standard modules used by plugins, original icon and compiled launcher's headless configuration self-test. The portable ZIP structure is also verified. It does not simulate a real Windows desktop qBittorrent search or a live Jackett server connection.

If a GitHub build fails, download the failed run's logs ZIP and share that ZIP. If a plugin fails after the app starts, a screenshot of the exact Search error and Python executable field is more useful than deleting existing profiles.
