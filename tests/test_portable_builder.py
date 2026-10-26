import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import build
import package

ROOT=Path(__file__).resolve().parents[1]


class PortableTests(unittest.TestCase):
    def test_official_python_sha256_pinned(self):
        self.assertEqual(build.PYTHON_VERSION, '3.14.10')
        self.assertEqual(build.PYTHON_SHA256, '90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159')
        self.assertEqual(len(build.PYTHON_SHA256),64)
        self.assertTrue(build.PYTHON_URI.startswith('https://www.python.org/'))

    def test_installer_selection(self):
        choices=[{'name':'qbittorrent_enhanced_5.2.4.10_x64_setup.exe'}, {'name':'qbittorrent_enhanced_5.2.4.10_x86_setup.exe'}]
        self.assertEqual(build.select_asset(choices)['name'],choices[0]['name'])

    def test_missing_installer_rejected(self):
        with self.assertRaises(RuntimeError):
            build.select_asset([{'name':'something-linux.tar.gz'}])

    def test_zip_slip_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.zip'
            with zipfile.ZipFile(p,'w') as z:z.writestr('../outside.txt','bad')
            with self.assertRaises(RuntimeError):build.safe_unzip(p,Path(d)/'out')

    def test_python_runtime_structural_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'python.zip'
            with zipfile.ZipFile(p,'w') as z:
                for name in ['python.exe','python314.zip','python314._pth']:
                    z.writestr(name,b'file')
            build.stage_python(p,Path(d)/'dest')
            self.assertTrue((Path(d)/'dest/python.exe').exists())

    def test_profile_and_search_python_setting_in_launcher(self):
        src=(ROOT/'launcher/qBittorrentEnhancedPortable.cs').read_text()
        self.assertIn('Path.Combine(data, "profile")',src)
        self.assertIn('Path.Combine(root, @"App\\Python")',src)
        self.assertIn('@"Search\\pythonExecutablePath"',src)
        self.assertIn('Quote("--profile=" + profile)',src)

    def test_no_global_python_environment_changes(self):
        src=(ROOT/'launcher/qBittorrentEnhancedPortable.cs').read_text()
        self.assertIn('process.EnvironmentVariables["PATH"]',src)
        self.assertIn('process.EnvironmentVariables.Remove("PYTHONPATH")',src)
        self.assertNotIn('Registry.',src)

    def test_headless_self_test_comes_first(self):
        src=(ROOT/'launcher/qBittorrentEnhancedPortable.cs').read_text()
        self.assertLess(src.index('if (selfTest) return RunSelfTest();'),src.index('if (!File.Exists(app))'))
        workflow=(ROOT/'.github/workflows/build-portable.yml').read_text()
        self.assertIn('WaitForExit(15000)',workflow)

    def test_data_and_jackett_are_preserved(self):
        src=(ROOT/'launcher/qBittorrentEnhancedPortable.cs').read_text()
        self.assertIn('File.Copy(cfgFile, backup, false)',src)
        self.assertNotIn('Directory.Delete(profile',src)
        self.assertNotIn('jackett.json',src)
        self.assertIn('if (contents != updated)',src)

    def test_manual_workflow_zip_only(self):
        w=(ROOT/'.github/workflows/build-portable.yml').read_text()
        self.assertIn('workflow_dispatch:',w)
        self.assertIn('retention-days: 1',w)
        self.assertIn('actions/upload-artifact@v6',w)
        self.assertIn('scripts/package.py',w)

    def test_package_smoke_fixture_preserves_empty_data(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'qBittorrentEnhancedPortable'
            for name in ['App/qBittorrent/qbittorrent.exe','App/Python/python.exe', 'App/Python/python314.zip', 'App/Python/python314._pth', 'App/AppInfo/appicon.ico', 'App/AppInfo/appinfo.ini', 'qBittorrentEnhancedPortable.exe', 'Other/Launcher-Source.cs','Other/build-info.json']:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
                if name.endswith('.exe'):p.write_bytes(b'MZ')
                elif name.endswith('.ico'):p.write_bytes(b'\x00\x00\x01\x00'+bytes(150))
                elif name.endswith('.cs'):p.write_text('Search\\pythonExecutablePath --portable-self-test')
                else:p.write_text('fixture')
            (root/'Data/profile').mkdir(parents=True)
            (root/'Data/Downloads').mkdir()
            out=Path(d)/'out.zip'
            package.pack(root,out)
            with zipfile.ZipFile(out) as z:
                self.assertIn('qBittorrentEnhancedPortable/Data/profile/',z.namelist())
                self.assertIn('qBittorrentEnhancedPortable/App/Python/python.exe',z.namelist())

if __name__=='__main__': unittest.main()
