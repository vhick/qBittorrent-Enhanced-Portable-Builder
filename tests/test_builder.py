import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import resolve_release
import extract_icon
import package_app


class BuilderTests(unittest.TestCase):
    def test_official_asset_selection(self):
        assets = [
            {"name": "qbittorrent-enhanced-nox_x86_64-linux-musl_static.zip"},
            {"name": "qbittorrent_enhanced_5.2.4.10_x64_setup.exe"},
            {"name": "qBittorrent-Enhanced-Edition-x86_64.AppImage"},
        ]
        self.assertEqual(resolve_release.find_installer(assets)["name"], "qbittorrent_enhanced_5.2.4.10_x64_setup.exe")

    def test_missing_windows_asset_fails_closed(self):
        with self.assertRaises(RuntimeError):
            resolve_release.find_installer([{"name": "x86_64.AppImage"}])

    def test_payload_selection_and_nested_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prog = root / "installer" / "files"
            prog.mkdir(parents=True)
            (prog / "qbittorrent.exe").write_bytes(b"MZ" + bytes(600_000))
            (prog / "qt.conf").write_text("[Paths]\n")
            (prog / "platforms").mkdir()
            (prog / "platforms" / "qwindows.dll").write_bytes(b"dll")
            (prog / "uninst.exe").write_bytes(b"MZ")
            self.assertEqual(package_app.find_payload(root), prog)
            destination = root / "copy"
            package_app.copy_program(prog, destination)
            self.assertTrue((destination / "platforms" / "qwindows.dll").exists())
            self.assertFalse((destination / "uninst.exe").exists())

    def test_original_ico_packaging(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Image.new("RGBA", (64, 64), (15, 80, 160, 255))
            content = io.BytesIO()
            image.save(content, format="PNG")
            output = Path(tmp) / "icon.ico"
            extract_icon.save_ico([(64, 64, 0, 0, 1, 32, content.getvalue())], output)
            contents = output.read_bytes()
            self.assertEqual(struct.unpack_from("<HHH", contents), (0, 1, 1))
            with Image.open(output) as icon:
                self.assertEqual(icon.size, (64, 64))

    def test_safe_asset_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "Unexpected installer"):
                resolve_release.download("https://example.org/malware.exe", Path(tmp) / "x.exe")

    def test_launcher_absolute_profile_arg_is_present(self):
        code = Path("launcher/qBittorrentEnhancedPortable.cs").read_text(encoding="utf-8")
        self.assertIn('QuoteArgument("--profile=" + profile)', code)
        self.assertIn('Path.Combine(data, "profile")', code)
        self.assertIn('Path.Combine(data, "Downloads")', code)
        self.assertIn('Session\\\\DefaultSavePath=', code)
        self.assertIn('AppDomain.CurrentDomain.BaseDirectory', code)
        self.assertNotIn("CreateSymbolicLink", code)


    def test_end_to_end_package_with_fixture_installer(self):
        from verify_package import verify
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "extracted"
            src.mkdir()
            (src / "qbittorrent.exe").write_bytes(b"MZ" + bytes(650_000))
            (src / "qt.conf").write_text("[Paths]\n")
            (src / "platforms").mkdir()
            (src / "platforms" / "qwindows.dll").write_bytes(b"qwindows")
            work = root / "work"
            work.mkdir()
            (work / "qBittorrentEnhancedPortable.exe").write_bytes(b"MZ" + bytes(2048))
            Image.new("RGBA", (128, 128), (50, 90, 120, 255)).save(work / "appicon.ico", format="ICO")
            dist = root / "dist"
            metadata = {"tag": "release-5.2.4.10", "sha256": "TEST_ONLY", "asset": "qbittorrent_enhanced_5.2.4.10_x64_setup.exe"}
            package = package_app.build(metadata, src, work, dist)
            verify(package)
            import zipfile
            with zipfile.ZipFile(package) as zipfile_obj:
                self.assertIn("qBittorrentEnhancedPortable/Data/profile/", zipfile_obj.namelist())
                self.assertIn("qBittorrentEnhancedPortable/App/qBittorrent/platforms/qwindows.dll", zipfile_obj.namelist())
                self.assertNotIn("qBittorrentEnhancedPortable/Data/profile/config/qBittorrent/qBittorrent.ini", zipfile_obj.namelist())

    def test_self_test_runs_before_application_file_check(self):
        """Regression: a blocking WinForms message box caused the 35-minute CI timeout."""
        code = Path('launcher/qBittorrentEnhancedPortable.cs').read_text(encoding='utf-8')
        self.assertIn('if (selfTest)', code)
        self.assertIn('String.Equals(args[0], "--portable-self-test"', code)
        self.assertLess(code.index('if (selfTest)'), code.index('if (!File.Exists(app))'))
        self.assertIn('if (!selfTest)\n                MessageBox.Show(', code)
        self.assertIn('Assembly.GetExecutingAssembly().Location', code)

    def test_headless_self_test_has_a_hard_timeout(self):
        workflow = Path('.github/workflows/build-portable.yml').read_text(encoding='utf-8')
        self.assertIn('$test.WaitForExit(15000)', workflow)
        self.assertIn('$test.Kill()', workflow)
        self.assertNotIn("-ArgumentList '--portable-self-test' -Wait", workflow)
        self.assertIn('timeout-minutes: 3', workflow)
        self.assertIn('timeout-minutes: 20', workflow)
        self.assertIn('actions/checkout@v5', workflow)
        self.assertIn('actions/setup-python@v6', workflow)
        self.assertIn('actions/upload-artifact@v6', workflow)

    def test_compiler_uses_full_source_paths(self):
        workflow = Path(".github/workflows/build-portable.yml").read_text(encoding="utf-8")
        self.assertIn("Resolve-Path -LiteralPath 'launcher/qBittorrentEnhancedPortable.cs'", workflow)
        self.assertIn('"/win32icon:$icon"', workflow)
        self.assertIn("workflow_dispatch", workflow)
        self.assertIn("retention-days: 1", workflow)


if __name__ == "__main__":
    unittest.main()
