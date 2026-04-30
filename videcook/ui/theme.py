"""Dark QSS theme for Videcook — single modern dark style."""

DARK_STYLESHEET = """
/* ================================================================
   Global
   ================================================================ */
QMainWindow {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 14px;
}
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}

/* ================================================================
   Sidebar
   ================================================================ */
#sidebar {
    background-color: #11111b;
    border-right: 1px solid #1e1e2e;
}

#sidebarButton {
    background-color: transparent;
    color: #a6adc8;
    border: none;
    border-radius: 6px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}
#sidebarButton:hover {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
#sidebarButton:checked, #sidebarButton:pressed {
    background-color: #1e1e2e;
    color: #89b4fa;
    border-left: 3px solid #89b4fa;
    border-radius: 6px;
    padding-left: 11px;
}

/* ================================================================
   Header
   ================================================================ */
#header {
    background-color: #181825;
    border-bottom: 1px solid #262636;
}
#appTitle {
    color: #cdd6f4;
    font-size: 18px;
    font-weight: 700;
}
#appTagline {
    color: #6c7086;
    font-size: 12px;
    font-weight: 400;
}

/* ================================================================
   Inputs
   ================================================================ */
QLineEdit, QComboBox {
    background-color: #11111b;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #89b4fa;
}
QLineEdit:disabled, QComboBox:disabled {
    background-color: #181825;
    color: #6c7086;
    border-color: #262636;
}
QComboBox::drop-down {
    border: none;
    width: 28px;
}
QComboBox QAbstractItemView {
    background-color: #11111b;
    color: #cdd6f4;
    selection-background-color: #313244;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 4px;
}

/* ================================================================
   Buttons — default / secondary
   ================================================================ */
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 500;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #45475a;
}
QPushButton:pressed {
    background-color: #585b70;
}
QPushButton:disabled {
    background-color: #262636;
    color: #6c7086;
}

/* ================================================================
   Primary action button
   ================================================================ */
#primaryButton {
    background-color: #89b4fa;
    color: #11111b;
    font-weight: 600;
    min-height: 40px;
}
#primaryButton:hover {
    background-color: #b4befe;
}
#primaryButton:pressed {
    background-color: #74c7ec;
}
#primaryButton:disabled {
    background-color: #313244;
    color: #6c7086;
}

/* ================================================================
   Danger / secondary action button
   ================================================================ */
#dangerButton {
    background-color: transparent;
    color: #f38ba8;
    border: 1px solid #f38ba8;
    font-weight: 500;
    min-height: 36px;
}
#dangerButton:hover {
    background-color: rgba(243, 139, 168, 0.12);
}
#dangerButton:pressed {
    background-color: rgba(243, 139, 168, 0.22);
}
#dangerButton:disabled {
    background-color: transparent;
    color: #6c7086;
    border-color: #45475a;
}

/* ================================================================
   Download page — named buttons
   ================================================================ */
#cookie_browse_button, #output_browse_button {
    background-color: #89b4fa;
    color: #11111b;
    font-weight: 600;
    min-width: 104px;
}
#cookie_browse_button:hover, #output_browse_button:hover {
    background-color: #b4befe;
}
#cookie_browse_button:pressed, #output_browse_button:pressed {
    background-color: #74c7ec;
}

#download_button {
    background-color: #89b4fa;
    color: #11111b;
    font-weight: 600;
    min-height: 42px;
}
#download_button:hover {
    background-color: #b4befe;
}
#download_button:pressed {
    background-color: #74c7ec;
}
#download_button:disabled {
    background-color: #313244;
    color: #6c7086;
}

#cancel_button {
    background-color: transparent;
    color: #f38ba8;
    border: 1px solid #f38ba8;
    font-weight: 500;
    min-height: 42px;
}
#cancel_button:hover {
    background-color: rgba(243, 139, 168, 0.12);
}
#cancel_button:pressed {
    background-color: rgba(243, 139, 168, 0.22);
}
#cancel_button:disabled {
    background-color: transparent;
    color: #6c7086;
    border-color: #45475a;
}

/* ================================================================
   Language toggle
   ================================================================ */
#langToggle {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 14px;
    padding: 5px 14px;
    font-weight: 700;
    font-size: 12px;
}
#langToggle:hover {
    background-color: #45475a;
    border-color: #585b70;
}

/* ================================================================
   Progress bar
   ================================================================ */
QProgressBar {
    background-color: #11111b;
    border: none;
    border-radius: 6px;
    text-align: center;
    color: #cdd6f4;
    font-size: 12px;
    font-weight: 600;
    min-height: 22px;
}
QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 6px;
}

/* ================================================================
   Text area / log
   ================================================================ */
QTextEdit, QPlainTextEdit {
    background-color: #11111b;
    color: #a6adc8;
    border: 1px solid #262636;
    border-radius: 8px;
    padding: 10px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
}

/* ================================================================
   Scroll area
   ================================================================ */
QScrollArea {
    border: none;
}

/* ================================================================
   Labels
   ================================================================ */
QLabel {
    color: #cdd6f4;
    background-color: transparent;
}
#sectionLabel {
    color: #6c7086;
    font-size: 11px;
    font-weight: 600;
}
#fieldLabel {
    color: #a6adc8;
    font-size: 12px;
    font-weight: 500;
}
#warningLabel {
    color: #f9e2af;
    font-size: 13px;
}
#statusLabel {
    color: #a6e3a1;
    font-weight: 600;
    font-size: 13px;
}
#okLabel {
    color: #a6e3a1;
    font-weight: 600;
}
#missingLabel {
    color: #f38ba8;
    font-weight: 600;
}

/* ================================================================
   Group boxes
   ================================================================ */
QGroupBox {
    color: #a6adc8;
    border: 1px solid #262636;
    border-radius: 10px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: 600;
    font-size: 13px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
}

/* ================================================================
   Cards / containers
   ================================================================ */
#card {
    background-color: #181825;
    border: 1px solid #262636;
    border-radius: 12px;
}

/* ================================================================
   Log panel
   ================================================================ */
#logPanel {
    background-color: #11111b;
    border: 1px solid #262636;
    border-radius: 10px;
}
#logHeader {
    background-color: #181825;
    border-bottom: 1px solid #262636;
    border-radius: 8px;
}
#logTitle {
    color: #6c7086;
    font-size: 11px;
    font-weight: 600;
}

/* ================================================================
   Warning callout box
   ================================================================ */
#warningBox {
    background-color: rgba(249, 226, 175, 0.08);
    border: 1px solid rgba(249, 226, 175, 0.25);
    border-radius: 10px;
    padding: 14px;
}

/* ================================================================
   Step items in help
   ================================================================ */
#stepBadge {
    background-color: #313244;
    color: #89b4fa;
    border-radius: 13px;
    font-weight: 700;
    font-size: 12px;
}
#stepText {
    color: #cdd6f4;
    font-size: 13px;
}
"""


def apply_theme(app_or_widget) -> None:
    """Apply the dark stylesheet to a QApplication or QWidget."""
    app_or_widget.setStyleSheet(DARK_STYLESHEET)
