"""UI geometry validation for Videcook Download page.

Usage:
    python scripts/check_ui_geometry.py

Performs deterministic geometry checks at 1250x780 and 1000x700.
Exits with 1 if any check fails, 0 if all pass.
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))  # noqa: E402

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from videcook.ui.main_window import MainWindow  # noqa: E402
from videcook.ui.theme import apply_theme  # noqa: E402
from videcook.utils.i18n import LanguageManager  # noqa: E402

# Widgets to locate by objectName
EXPECTED_NAMES = [
    "video_url_input",
    "cookie_path_input",
    "cookie_browse_button",
    "output_path_input",
    "output_browse_button",
    "quality_combo",
    "download_button",
    "cancel_button",
    "progress_bar",
    "status_label",
    "operation_log",
]

FAILED: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "[PASS]" if condition else "[FAIL]"
    line = f"  {status} {label}"
    if detail:
        line += f"  ({detail})"
    print(line)
    if not condition:
        FAILED.append(label)


def run_at_size(width: int, height: int) -> None:
    print(f"\n{'='*60}")
    print(f"Size: {width}x{height}")
    print("=" * 60)

    app = QApplication.instance() or QApplication(sys.argv)
    apply_theme(app)

    i18n = LanguageManager()
    window = MainWindow(i18n)
    window.resize(width, height)
    window.show()
    window._show_page(0)
    app.processEvents()

    page = window._download_page

    # Collect widgets
    widgets: dict[str, QWidget | None] = {}
    for name in EXPECTED_NAMES:
        w = page.findChild(QWidget, name)
        widgets[name] = w
        if w is None:
            FAILED.append(f"widget not found: {name}")

    print("\n[geometry]")
    for name, w in widgets.items():
        if w is not None:
            g = w.geometry()
            print(f"  {name}: x={g.x()} y={g.y()} w={g.width()} h={g.height()}")

    # --- Sizing checks ---
    print("\n[check] Sizing")

    # Inputs and combo: h in [34, 60]
    for name in ["video_url_input", "cookie_path_input", "output_path_input", "quality_combo"]:
        w = widgets.get(name)
        if w:
            h = w.height()
            ok = 34 <= h <= 60
            check(f"{name} height 34-60", ok, f"h={h}")

    # Browse buttons: h in [38, 56]
    for name in ["cookie_browse_button", "output_browse_button"]:
        w = widgets.get(name)
        if w:
            h = w.height()
            ok = 38 <= h <= 56
            check(f"{name} height 38-56", ok, f"h={h}")

    # All widgets: width > 50
    for name, w in widgets.items():
        if w:
            ok = w.width() > 50
            check(f"{name} width > 50", ok, f"w={w.width()}")

    # --- Non-overlap checks ---
    print("\n[check] Non-overlap")

    def bottom(w):
        g = w.geometry()
        return g.y() + g.height()

    def top(w):
        return w.geometry().y()

    # Overlap: check consecutive rows (widget_a.row vs widget_b.row)
    # Row 1 → Row 2, Row 2 → Row 3, Row 3 → Row 4
    row_order = [
        ("video_url_input", "cookie_path_input"),       # row 1 → row 2
        ("cookie_path_input", "output_path_input"),     # row 2 → row 3
        ("output_path_input", "quality_combo"),         # row 3 → row 4
    ]
    for a_name, b_name in row_order:
        a = widgets.get(a_name)
        b = widgets.get(b_name)
        if a and b:
            a_bottom = bottom(a)
            b_top = top(b)
            ok = a_bottom <= b_top + 6
            check(f"{a_name} -> {b_name} (no overlap)", ok,
                  f"{a_name}.bottom={a_bottom} {b_name}.top={b_top}")

    # Special: cookie_browse_button aligned within 8px of cookie_path_input
    cb = widgets.get("cookie_browse_button")
    ci = widgets.get("cookie_path_input")
    if cb and ci:
        diff = abs(cb.geometry().y() - ci.geometry().y())
        check("cookie_browse aligns with cookie_path_input (dy <= 8)",
              diff <= 8, f"dy={diff}")

    ob = widgets.get("output_browse_button")
    oi = widgets.get("output_path_input")
    if ob and oi:
        diff = abs(ob.geometry().y() - oi.geometry().y())
        check("output_browse aligns with output_path_input (dy <= 8)",
              diff <= 8, f"dy={diff}")

    # --- Card bounds ---
    print("\n[check] Card bounds")
    qual = widgets.get("quality_combo")
    form_card = page.findChild(QWidget, "card")
    if qual and form_card:
        card_bottom = form_card.geometry().y() + form_card.geometry().height()
        qual_bottom = bottom(qual)
        check("form_card contains quality_combo",
              qual_bottom <= card_bottom + 4,
              f"card_bottom={card_bottom} qual_bottom={qual_bottom}")

    window.close()


def main() -> int:
    run_at_size(1250, 780)
    run_at_size(1000, 700)

    print(f"\n{'='*60}")
    if FAILED:
        print(f"[FAIL] {len(FAILED)} check(s) failed:")
        for f in FAILED:
            print(f"  - {f}")
        return 1
    else:
        print("[PASS] All geometry checks passed.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
