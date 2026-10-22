// qBittorrent Enhanced Edition Portable launcher.
// Uses the upstream-supported --profile switch: the host user's AppData profile is not used.
// Build as a Windows GUI executable with the application's original icon.
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
        string root = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        string appDir = Path.Combine(root, @"App\qBittorrent");
        string app = Path.Combine(appDir, "qbittorrent.exe");
        string data = Path.Combine(root, "Data");
        string profile = Path.Combine(data, "profile");
        string downloads = Path.Combine(data, "Downloads");

        try
        {
            if (!File.Exists(app))
                throw new FileNotFoundException("The qBittorrent application file is missing. Re-extract the portable ZIP without removing App.", app);

            // A workflow smoke test can verify the compiled launcher without opening the GUI.
            if (args.Length == 1 && args[0] == "--portable-self-test")
                return 0;

            foreach (string arg in args)
            {
                // Protect the Data-only configuration guarantee from overrides.
                if (arg.Equals("--profile", StringComparison.OrdinalIgnoreCase) ||
                    arg.StartsWith("--profile=", StringComparison.OrdinalIgnoreCase) ||
                    arg.Equals("--configuration", StringComparison.OrdinalIgnoreCase) ||
                    arg.StartsWith("--configuration=", StringComparison.OrdinalIgnoreCase))
                    throw new ArgumentException("This launcher manages the portable profile automatically. Remove the --profile or --configuration argument.");
            }

            Directory.CreateDirectory(data);
            Directory.CreateDirectory(profile);
            Directory.CreateDirectory(downloads);
            SetupFirstRunAndRelocation(root, data, profile, downloads);

            StringBuilder arguments = new StringBuilder();
            arguments.Append(QuoteArgument("--profile=" + profile));
            foreach (string arg in args)
                arguments.Append(' ').Append(QuoteArgument(arg));

            ProcessStartInfo info = new ProcessStartInfo();
            info.FileName = app;
            info.Arguments = arguments.ToString();
            info.WorkingDirectory = appDir;
            info.UseShellExecute = false;
            Process process = Process.Start(info);
            if (process == null)
                throw new InvalidOperationException("Windows could not start qBittorrent Enhanced Edition.");
            return 0;
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "qBittorrent Enhanced Portable", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }

    // First run only: use a portable download folder instead of the host Downloads folder.
    // Relocation only adjusts the default if it is still our managed Data/Downloads path.
    // Existing torrents' saved file paths are NOT rewritten or moved.
    private static void SetupFirstRunAndRelocation(string root, string data, string profile, string downloads)
    {
        string configDir = Path.Combine(Path.Combine(profile, "config"), "qBittorrent");
        string configFile = Path.Combine(configDir, "qBittorrent.ini");
        string marker = Path.Combine(data, "portable-root.txt");
        string newPath = downloads.Replace('\\', '/');
        if (!File.Exists(configFile))
        {
            Directory.CreateDirectory(configDir);
            File.WriteAllText(configFile,
                "[BitTorrent]\r\nSession\\DefaultSavePath=" + newPath + "\r\n",
                new UTF8Encoding(false));
        }
        else if (File.Exists(marker))
        {
            string oldRoot = File.ReadAllText(marker).Trim();
            if (!String.IsNullOrWhiteSpace(oldRoot) &&
                !String.Equals(oldRoot, root, StringComparison.OrdinalIgnoreCase))
            {
                string oldPath = Path.Combine(Path.Combine(oldRoot, "Data"), "Downloads").Replace('\\', '/');
                string oldText = File.ReadAllText(configFile);
                string pattern = @"(?m)^(Session\\DefaultSavePath=)" + Regex.Escape(oldPath) + @"\r?$";
                string newText = Regex.Replace(oldText, pattern,
                    m => m.Groups[1].Value + newPath, RegexOptions.IgnoreCase);
                if (!String.Equals(oldText, newText, StringComparison.Ordinal))
                    File.WriteAllText(configFile, newText, new UTF8Encoding(false));
            }
        }
        File.WriteAllText(marker, root, new UTF8Encoding(false));
    }

    // Windows CommandLineToArgvW-compatible quoting for dragged .torrent files and magnet links.
    private static string QuoteArgument(string argument)
    {
        if (argument.Length > 0 && argument.IndexOfAny(new char[] { ' ', '\t', '\n', '\v', '"' }) < 0)
            return argument;
        StringBuilder result = new StringBuilder("\"");
        int slashes = 0;
        foreach (char c in argument)
        {
            if (c == '\\') { slashes++; continue; }
            if (c == '"')
            {
                result.Append('\\', slashes * 2 + 1);
                result.Append('"');
                slashes = 0;
                continue;
            }
            result.Append('\\', slashes);
            slashes = 0;
            result.Append(c);
        }
        result.Append('\\', slashes * 2);
        result.Append('"');
        return result.ToString();
    }
}
