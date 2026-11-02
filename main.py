"""
main.py - Entry point for Saiful Download Manager.

Run:    python main.py
Build:  build_exe.bat   (produces dist\SaifulDownloadManager.exe)
"""
import sys
import os


def main():
    if getattr(sys, "frozen", False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

    from gui import MainWindow
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
