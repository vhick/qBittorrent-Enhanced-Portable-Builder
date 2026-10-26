// qBittorrent Enhanced Edition Portable Builder v1.2
// Uses an isolated profile and the bundled Python runtime for search plugins.
// No global PATH/registry changes. Original icon supplied at build time.
using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Windows.Forms;

internal static class PortableLauncher
{
    [STAThread]
    private static int Main(string[] args)
    {
        // FIRST: headless CI test. Nothing else, including file checks, can open a dialog.
        bool selfTest = args.Length == 1 &&
            String.Equals(args[0], "--portable-self-test", StringComparison.OrdinalIgnoreCase);
        if (selfTest) return RunSelfTest();

        try
        {
            string root = Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory)
                .TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            string appDir = Path.Combine(root, @"App\qBittorrent");
            string app = Path.Combine(appDir, "qbittorrent.exe");
            string pythonDir = Path.Combine(root, @"App\Python");
            string python = Path.Combine(pythonDir, "python.exe");
            string data = Path.Combine(root, "Data");
            string profile = Path.Combine(data, "profile");
            string downloads = Path.Combine(data, "Downloads");
            if (!File.Exists(app)) throw new FileNotFoundException("Missing App\\qBittorrent\\qbittorrent.exe", app);
            if (!File.Exists(python)) throw new FileNotFoundException("Missing App\\Python\\python.exe. Please extract the complete v1.2 ZIP.", python);
            foreach (string arg in args)
            {
                if (arg.Equals("--profile", StringComparison.OrdinalIgnoreCase) ||
                    arg.StartsWith("--profile=", StringComparison.OrdinalIgnoreCase) ||
                    arg.Equals("--configuration", StringComparison.OrdinalIgnoreCase) ||
                    arg.StartsWith("--configuration=", StringComparison.OrdinalIgnoreCase))
                    throw new ArgumentException("Please do not override the portable profile with --profile or --configuration.");
            }
            Directory.CreateDirectory(profile);
            Directory.CreateDirectory(downloads);
            Configure(data, profile, downloads, python, root);

            StringBuilder arguments = new StringBuilder(Quote("--profile=" + profile));
            foreach (string arg in args) arguments.Append(' ').Append(Quote(arg));
            ProcessStartInfo process = new ProcessStartInfo();
            process.FileName = app;
            process.WorkingDirectory = appDir;
            process.Arguments = arguments.ToString();
            process.UseShellExecute = false;
            // The environment changes apply ONLY to the qBittorrent process and its children.
            // The explicit INI preference avoids depending on the system Python installation.
            string currentPath = process.EnvironmentVariables["PATH"] ?? "";
            process.EnvironmentVariables["PATH"] = pythonDir + ";" + currentPath;
            process.EnvironmentVariables.Remove("PYTHONHOME");
            process.EnvironmentVariables.Remove("PYTHONPATH");
            Process launched = Process.Start(process);
            if (launched == null) throw new InvalidOperationException("Unable to launch qBittorrent Enhanced Edition.");
            return 0;
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "qBittorrent Enhanced Portable", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }

    private static void Configure(string data, string profile, string downloads, string python, string root)
    {
        string cfgDir = Path.Combine(profile, @"config\qBittorrent");
        string cfgFile = Path.Combine(cfgDir, "qBittorrent.ini");
        string marker = Path.Combine(data, "portable-root.txt");
        Directory.CreateDirectory(cfgDir);
        string pythonPortablePath = python.Replace('\\', '/');
        string downloadPortablePath = downloads.Replace('\\', '/');
        if (!File.Exists(cfgFile))
        {
            // Qt/QSettings keys are backslash-separated inside their section.
            File.WriteAllText(cfgFile,
                "[BitTorrent]\r\nSession\\DefaultSavePath=" + downloadPortablePath +
                "\r\n\r\n[Preferences]\r\nSearch\\pythonExecutablePath=" + pythonPortablePath + "\r\n",
                new UTF8Encoding(false));
        }
        else
        {
            // Do not discard old torrent sessions, plugins, Jackett JSON, or preferences.
            string contents = File.ReadAllText(cfgFile, Encoding.UTF8);
            string updated = PutIniKey(contents, "Preferences", @"Search\pythonExecutablePath", pythonPortablePath);

            // Only correct the default download directory when it is the OLD
            // portable Data/Downloads path. Never rewrite per-torrent save paths.
            if (File.Exists(marker))
            {
                string oldRoot = File.ReadAllText(marker, Encoding.UTF8).Trim();
                if (!String.IsNullOrEmpty(oldRoot) &&
                    !String.Equals(oldRoot, root, StringComparison.OrdinalIgnoreCase))
                {
                    string oldDownloads = Path.Combine(oldRoot, @"Data\Downloads").Replace('\\', '/');
                    updated = ReplaceIniKeyIfValue(updated, "BitTorrent", @"Session\DefaultSavePath", oldDownloads, downloadPortablePath);
                }
            }
            if (contents != updated)
            {
                // Back up the config if we have not already done so on this portable copy.
                string backup = Path.Combine(cfgDir, "qBittorrent.ini.portable-pre-python.bak");
                if (!File.Exists(backup)) File.Copy(cfgFile, backup, false);
                // Write to a separate file, then atomically replace existing config.
                string pending = cfgFile + ".portable.tmp";
                File.WriteAllText(pending, updated, new UTF8Encoding(false));
                try { File.Replace(pending, cfgFile, null); }
                catch (PlatformNotSupportedException) { File.Copy(pending, cfgFile, true); File.Delete(pending); }
            }
        }
        File.WriteAllText(marker, root, new UTF8Encoding(false));
    }

    private static int RunSelfTest()
    {
        // No actual app or user data accessed, no dialog boxes, and no Windows integrations.
        string original = "[BitTorrent]\r\nSession\\DefaultSavePath=C:/Downloads\r\n[Preferences]\r\nGeneral\\Locale=en\r\n";
        string result = PutIniKey(original, "Preferences", @"Search\pythonExecutablePath", "D:/Portable/App/Python/python.exe");
        if (!result.Contains(@"Search\pythonExecutablePath=D:/Portable/App/Python/python.exe")) return 5;
        if (!result.Contains(@"Session\DefaultSavePath=C:/Downloads")) return 6;
        if (!result.Contains(@"General\Locale=en")) return 7;
        string second = PutIniKey(result, "Preferences", @"Search\pythonExecutablePath", "E:/Portable/App/Python/python.exe");
        if (second.Contains("D:/Portable/App/Python/python.exe")) return 8;
        if (!second.Contains("E:/Portable/App/Python/python.exe")) return 9;
        if (PutIniKey(second, "Preferences", @"Search\pythonExecutablePath", "E:/Portable/App/Python/python.exe") != second) return 10;
        return 0;
    }

    // Edits a single Qt INI key inside its section, without replacing other settings.
    private static string PutIniKey(string ini, string section, string key, string value)
    {
        string eol = ini.Contains("\r\n") ? "\r\n" : "\n";
        string[] lines = Regex.Split(ini, "\r\n|\n");
        int header = -1, boundary = lines.Length, found = -1;
        for (int i = 0; i < lines.Length; i++)
        {
            string trimmed = lines[i].Trim();
            if (trimmed.Equals("[" + section + "]", StringComparison.OrdinalIgnoreCase))
            { header = i; continue; }
            if (header >= 0 && trimmed.StartsWith("[") && trimmed.EndsWith("]")) { boundary = i; break; }
            if (header >= 0)
            {
                int eq = lines[i].IndexOf('=');
                if (eq > 0 && lines[i].Substring(0, eq).Trim().Equals(key, StringComparison.OrdinalIgnoreCase))
                { found = i; break; }
            }
        }
        if (found >= 0)
        {
            int eq = lines[found].IndexOf('=');
            string desired = lines[found].Substring(0, eq + 1) + value;
            if (desired == lines[found]) return ini;
            lines[found] = desired;
            return String.Join(eol, lines);
        }
        System.Collections.Generic.List<string> list = new System.Collections.Generic.List<string>(lines);
        if (header < 0)
        {
            if (list.Count == 0 || list[list.Count - 1].Length != 0) list.Add("");
            list.Add("[" + section + "]");
            list.Add(key + "=" + value);
        }
        else
        {
            // Insert just after section header; never alter unrelated sections.
            list.Insert(header + 1, key + "=" + value);
        }
        return String.Join(eol, list);
    }

    private static string ReplaceIniKeyIfValue(string ini, string section, string key, string oldValue, string newValue)
    {
        string[] lines = Regex.Split(ini, "\r\n|\n");
        bool inside = false;
        for (int i = 0; i < lines.Length; ++i)
        {
            string line = lines[i].Trim();
            if (line.StartsWith("[") && line.EndsWith("]"))
            { inside = line.Equals("[" + section + "]", StringComparison.OrdinalIgnoreCase); continue; }
            if (!inside) continue;
            int eq = lines[i].IndexOf('=');
            if (eq >= 0 && lines[i].Substring(0, eq).Trim().Equals(key, StringComparison.OrdinalIgnoreCase) &&
                lines[i].Substring(eq + 1).Trim().Equals(oldValue, StringComparison.OrdinalIgnoreCase))
                return PutIniKey(ini, section, key, newValue);
        }
        return ini;
    }

    private static string Quote(string arg)
    {
        StringBuilder output = new StringBuilder("\"");
        int backslashes = 0;
        foreach (char ch in arg)
        {
            if (ch == '\\') { backslashes++; continue; }
            if (ch == '"')
            { output.Append('\\', backslashes * 2 + 1); output.Append('"'); backslashes = 0; continue; }
            output.Append('\\', backslashes); backslashes = 0; output.Append(ch);
        }
        output.Append('\\', backslashes * 2);
        output.Append('"');
        return output.ToString();
    }
}
