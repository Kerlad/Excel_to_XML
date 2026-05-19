// C# Launcher for ExcelXML-Mintrud
// Compile: csc.exe /target:winexe /win32icon:resources\ico.ico /out:ExcelXML-Mintrud.exe Launcher.cs
using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

class Program
{
    static void Main()
    {
        string appDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
        string mainPy = Path.Combine(appDir, "main.py");

        if (!File.Exists(mainPy))
        {
            MessageBox.Show(
                "Ne naiden fayl main.py.\nUbedites, chto programma raspakovana polnostyu.",
                "ExcelXML-Mintrud",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error
            );
            return;
        }

        string pythonExe = FindPython();
        if (pythonExe == null)
        {
            MessageBox.Show(
                "Python ne naiden.\nUstanovite Python 3.12+ s python.org",
                "ExcelXML-Mintrud",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error
            );
            return;
        }

        try
        {
            Process proc = new Process();
            proc.StartInfo.FileName = pythonExe;
            proc.StartInfo.Arguments = "\"" + mainPy + "\"";
            proc.StartInfo.WorkingDirectory = appDir;
            proc.StartInfo.UseShellExecute = false;
            proc.Start();
            proc.WaitForExit();
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                "Oshibka zapuska:\n" + ex.Message,
                "ExcelXML-Mintrud",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error
            );
        }
    }

    static string FindPython()
    {
        string[] candidates = {
            "py.exe", "python3.exe", "python.exe",
            "python3.13.exe", "python3.12.exe", "python3.11.exe"
        };
        foreach (string name in candidates)
        {
            string path = FindOnPath(name);
            if (path != null) return path;
        }

        string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);

        string[] paths = {
            localAppData + "\\Programs\\Python\\",
            programFiles + "\\Python\\",
            programFiles + "\\Python312\\",
            "C:\\Python312\\",
            "C:\\Python313\\"
        };
        foreach (string dir in paths)
        {
            foreach (string name in candidates)
            {
                string full = Path.Combine(dir, name);
                if (File.Exists(full)) return full;
            }
        }
        return null;
    }

    static string FindOnPath(string filename)
    {
        try
        {
            string pathEnv = Environment.GetEnvironmentVariable("PATH");
            if (string.IsNullOrEmpty(pathEnv)) return null;
            string[] paths = pathEnv.Split(';');
            foreach (string p in paths)
            {
                string trimmed = p.Trim();
                if (trimmed.Length == 0) continue;
                string full = Path.Combine(trimmed, filename);
                if (File.Exists(full)) return full;
            }
        }
        catch { }
        return null;
    }
}
