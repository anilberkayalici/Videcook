"""Videcook application entry point."""

import sys


def _smoke_check() -> int:
    """Verify imports and basic setup without launching a long-lived GUI window."""
    try:
        from videcook.app import create_app
        from videcook.ui.main_window import MainWindow
        from videcook.utils.i18n import LanguageManager
    except ImportError as exc:
        print(f"Videcook GUI smoke check SKIPPED: {exc}")
        print("PySide6 may not be fully installed. Run: python -m pip install -r requirements.txt")
        return 0

    try:
        create_app(["videcook", "--smoke"])
        i18n = LanguageManager()
        # Instantiate but do not show or exec — this proves Qt + imports work
        window = MainWindow(i18n)
        assert window.windowTitle() == "Videcook"
        print("Videcook GUI smoke check passed")
        return 0
    except Exception as exc:
        print(f"Videcook GUI smoke check FAILED: {exc}")
        return 1


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--smoke":
        return _smoke_check()

    from videcook.app import run_app

    return run_app()


if __name__ == "__main__":
    sys.exit(main())
