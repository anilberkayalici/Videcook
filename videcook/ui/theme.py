"""Dark wine QSS theme for Videcook."""

DARK_STYLESHEET = """
/* ================================================================
   Global
   ================================================================ */
QMainWindow {
    background-color: #050506;
    color: #F7EEF1;
    font-family: "Segoe UI", "Inter", "Microsoft YaHei", sans-serif;
    font-size: 14px;
}

QWidget {
    background-color: transparent;
}

QLabel {
    color: #F7EEF1;
    background-color: transparent;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    background: #080708;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #3A2028;
    border-radius: 5px;
    min-height: 32px;
}

QScrollBar::handle:vertical:hover {
    background: #6E2636;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}

/* ================================================================
   App shell
   ================================================================ */
#sidebar {
    background-color: #080708;
    border-right: 1px solid #24141A;
}

#sidebarBrand {
    background-color: #110B0D;
    border: 1px solid #2A171E;
    border-radius: 8px;
}

#sidebarTitle {
    color: #FFF7F8;
    font-size: 20px;
    font-weight: 700;
}

#sidebarHint {
    color: #A9959A;
    font-size: 12px;
    font-weight: 400;
}

#sidebarButton {
    background-color: transparent;
    color: #BBAAB0;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 12px 14px;
    text-align: left;
    font-size: 14px;
    font-weight: 600;
}

#sidebarButton:hover {
    background-color: #130D10;
    border-color: #332029;
    color: #FFF7F8;
}

#sidebarButton:checked {
    background-color: #2A1018;
    border-color: #8A2F43;
    color: #FFF7F8;
    font-weight: 700;
}

#sidebarFooter {
    color: #735F66;
    font-size: 11px;
}

#header {
    background-color: #070607;
    border-bottom: 1px solid #211217;
}

#contentRoot {
    background-color: #0B090B;
}

/* ================================================================
   Surfaces
   ================================================================ */
#primaryCard,
#statusCard,
#settingsCard,
#setupCard,
#helpCard {
    background-color: #111013;
    border: 1px solid #2A1A21;
    border-radius: 8px;
}

#primaryCard {
    background-color: #121013;
}

#statusCard {
    background-color: #0E0D10;
}

#inlinePanel,
#fieldPanel,
#embedPanel,
#binaryRow,
#stepRow {
    background-color: #171217;
    border: 1px solid #2B1B22;
    border-radius: 8px;
}

#heroStrip {
    background-color: #120D10;
    border: 1px solid #301A22;
    border-radius: 8px;
}

/* ================================================================
   Typography
   ================================================================ */
#appTitle {
    color: #FFF8F9;
    font-size: 23px;
    font-weight: 700;
}

#pageTitle {
    color: #FFF8F9;
    font-size: 21px;
    font-weight: 700;
}

#appTagline,
#mutedText {
    color: #A9959A;
    font-size: 13px;
    font-weight: 400;
}

#sectionLabel {
    color: #E8C9D0;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
}

#fieldLabel {
    color: #DCCBD0;
    font-size: 13px;
    font-weight: 600;
}

#stepBadge {
    background-color: #7F1D2D;
    color: #FFF8F9;
    font-weight: 700;
    font-size: 13px;
    border-radius: 8px;
}

#stepText {
    color: #D7C4CA;
    font-size: 13px;
}

/* ================================================================
   Inputs / Combo
   ================================================================ */
QLineEdit,
QComboBox {
    background-color: #09080A;
    color: #FFF7F8;
    border: 1px solid #35212A;
    border-radius: 8px;
    padding: 9px 13px;
    font-size: 13px;
    selection-background-color: #8A2F43;
    selection-color: #FFF7F8;
}

QLineEdit:hover,
QComboBox:hover {
    border-color: #59303D;
}

QLineEdit:focus,
QComboBox:focus {
    border-color: #B83A52;
    background-color: #0D0A0D;
}

QLineEdit:disabled,
QComboBox:disabled {
    background-color: #121013;
    color: #6F5B62;
    border-color: #261820;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox QAbstractItemView {
    background-color: #100D11;
    color: #EADCE0;
    border: 1px solid #3B222C;
    border-radius: 8px;
    padding: 6px;
    selection-background-color: #7F1D2D;
    selection-color: #FFF7F8;
    outline: none;
}

QComboBox QAbstractItemView::item {
    min-height: 30px;
    padding: 7px 10px;
    border-radius: 6px;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #24151C;
}

/* ================================================================
   Buttons
   ================================================================ */
QPushButton {
    background-color: #1B1419;
    color: #EADCE0;
    border: 1px solid #34212A;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 700;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #261821;
    border-color: #6E2636;
    color: #FFF7F8;
}

QPushButton:pressed {
    background-color: #120C10;
    border-color: #8A2F43;
}

QPushButton:focus {
    border-color: #D0475D;
}

QPushButton:disabled {
    background-color: #121013;
    color: #66545B;
    border-color: #24171E;
}

#cookie_browse_button,
#output_browse_button {
    background-color: #21151B;
    color: #FFF3F5;
    border: 1px solid #5B2635;
    font-weight: 700;
}

#cookie_browse_button:hover,
#output_browse_button:hover {
    background-color: #321A24;
    border-color: #B83A52;
}

#download_button {
    background-color: #A92C42;
    color: #FFF8F9;
    border: 1px solid #C9455C;
    font-weight: 700;
    font-size: 15px;
    border-radius: 8px;
    min-height: 46px;
}

#download_button:hover {
    background-color: #BE3A52;
    border-color: #E05267;
}

#download_button:pressed {
    background-color: #842136;
    border-color: #A92C42;
}

#download_button:disabled {
    background-color: #1A1217;
    color: #715A62;
    border-color: #2A1A21;
}

#cancel_button {
    background-color: transparent;
    color: #D8B3BD;
    border: 1px solid #4D2633;
    font-weight: 700;
    border-radius: 8px;
}

#cancel_button:hover {
    background-color: #211119;
    border-color: #B83A52;
    color: #FFF2F5;
}

#cancel_button:disabled {
    background-color: transparent;
    color: #625158;
    border-color: #261820;
}

#langToggle {
    background-color: #141014;
    color: #E7D4DA;
    border: 1px solid #3A222B;
    border-radius: 8px;
    font-weight: 700;
    font-size: 12px;
}

#langToggle:hover {
    background-color: #23151C;
    color: #FFF7F8;
    border-color: #8A2F43;
}

/* ================================================================
   Segmented button
   ================================================================ */
#segButton {
    background-color: #0C0A0C;
    color: #BBAAB0;
    border: 1px solid #35212A;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 700;
    padding: 8px 14px;
}

#segButton:hover {
    border-color: #8A2F43;
    color: #FFF3F5;
}

#segButton:checked {
    background-color: #7F1D2D;
    color: #FFF8F9;
    border-color: #B83A52;
}

/* ================================================================
   Checks and toggles
   ================================================================ */
QCheckBox {
    color: #D7C4CA;
    font-size: 13px;
    font-weight: 600;
    spacing: 10px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    background-color: #0B090B;
    border: 1px solid #46303A;
}

QCheckBox::indicator:hover {
    border-color: #A92C42;
}

QCheckBox:focus {
    color: #FFF7F8;
}

QCheckBox::indicator:checked {
    background-color: #A92C42;
    border-color: #D0475D;
}

#embedPanel QCheckBox {
    color: #EADCE0;
    font-size: 13px;
    font-weight: 600;
}

#embedPanel QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 6px;
}

#membersToggle {
    background-color: #0D0A0D;
    color: #EADCE0;
    border: 1px solid #422632;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 700;
}

#membersToggle:hover {
    background-color: #181016;
    border-color: #8A2F43;
    color: #FFF7F8;
}

#membersToggle:checked {
    background-color: #2A1018;
    border-color: #C9455C;
    color: #FFF7F8;
}

#membersToggle:checked:hover {
    background-color: #37131F;
}

/* ================================================================
   Progress and status
   ================================================================ */
QProgressBar {
    background-color: #070607;
    border: 1px solid #2A1A21;
    border-radius: 8px;
    text-align: center;
    color: #FFF7F8;
    font-size: 12px;
    font-weight: 700;
}

QProgressBar::chunk {
    background-color: #A92C42;
    border-radius: 7px;
}

#status_label {
    color: #F1DCE2;
    font-size: 15px;
    font-weight: 700;
}

#statusHint {
    color: #8C7880;
    font-size: 12px;
}

/* ================================================================
   Log panel
   ================================================================ */
#logPanel {
    background-color: #080708;
    border: 1px solid #24141A;
    border-radius: 8px;
}

#logTitle {
    color: #DAB8C1;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
}

QPlainTextEdit {
    background-color: #050506;
    color: #BDAAB1;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 12px;
    border: 1px solid #24141A;
    border-radius: 8px;
    padding: 10px;
    selection-background-color: #8A2F43;
    selection-color: #FFF7F8;
}

QPlainTextEdit:focus {
    border-color: #5B2635;
}

/* ================================================================
   Warning and badges
   ================================================================ */
#warningBox {
    background-color: #1A1110;
    border: 1px solid #5B3327;
    border-radius: 8px;
}

#warningLabel {
    color: #E7C2A3;
    font-size: 12px;
    font-weight: 500;
}
"""


def apply_theme(app_or_widget) -> None:
    """Apply the dark stylesheet to a QApplication or QWidget."""
    app_or_widget.setStyleSheet(DARK_STYLESHEET)

