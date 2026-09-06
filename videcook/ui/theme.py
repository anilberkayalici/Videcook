"""Multi-theme QSS system for Videcook.

Each theme is a colour palette. The ``_QSS_TEMPLATE`` uses placeholder
tokens like ``{{bg}}`` that are replaced at load time via
:func:`build_stylesheet`. Theme names map to palettes; the active
theme is persisted in user preferences.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Colour palettes (key -> hex)
# ---------------------------------------------------------------------------

THEMES: dict[str, dict[str, str]] = {   'dracula': {   'accent': '#512985',
                   'accent_bright': '#7642B5',
                   'accent_bright_hover': '#8347CF',
                   'accent_hover': '#8E4FE0',
                   'accent_soft': '#4B2373',
                   'accent_text': '#FFFFFF',
                   'bg': '#07040C',
                   'bg_brand': '#090511',
                   'bg_button': '#1A112B',
                   'bg_button_hover': '#271A40',
                   'bg_card': '#0E0917',
                   'bg_dropdown': '#120B1C',
                   'bg_elevated': '#160E24',
                   'bg_field': '#120B1C',
                   'bg_hero': '#07040C',
                   'bg_input': '#090511',
                   'bg_sidebar': '#090511',
                   'bg_surface': '#0E0917',
                   'border': '#271A40',
                   'border_focus': '#8E4FE0',
                   'border_hover': '#3C285E',
                   'brand_border': '#271A40',
                   'check_checked': '#8E4FE0',
                   'check_indicator': '#090511',
                   'content_bg': '#07040C',
                   'cookie_browse_bg': '#120B1C',
                   'cookie_browse_border': '#3C285E',
                   'cookie_browse_hover': '#1A112B',
                   'header_bg': '#090511',
                   'header_border': '#1D122E',
                   'lang_toggle_bg': '#120B1C',
                   'lang_toggle_border': '#30204F',
                   'lang_toggle_hover': '#1D122E',
                   'log_bg': '#07040C',
                   'name': 'Dusk',
                   'progress': '#7642B5',
                   'scroll_bg': '#07040C',
                   'scroll_handle': '#30204F',
                   'scroll_handle_hover': '#4B3278',
                   'seg_button_bg': '#160E24',
                   'seg_button_checked': '#63359E',
                   'sidebar_active': '#1D122E',
                   'sidebar_active_border': '#8E4FE0',
                   'sidebar_footer': '#745299',
                   'sidebar_hover': '#160E24',
                   'step_badge': '#63359E',
                   'swatch_blend': '#542A7C',
                   'swatch_end': '#07040C',
                   'swatch_ring': '#7642B5',
                   'swatch_start': '#C373F2',
                   'table_stripe': '#0E0917',
                   'table_stripe_border': '#271A40',
                   'text_accent': '#C373F2',
                   'text_body': '#D8BEEB',
                   'text_dim': '#745299',
                   'text_primary': '#F2E6FC',
                   'text_secondary': '#A37DCC',
                   'warning_bg': '#261A00',
                   'warning_text': '#F0B832'},
    'gruvbox': {   'accent': '#235E39',
                   'accent_bright': '#388A58',
                   'accent_bright_hover': '#40A166',
                   'accent_hover': '#46AB6E',
                   'accent_soft': '#02422C',
                   'accent_text': '#FFFFFF',
                   'bg': '#040906',
                   'bg_brand': '#060C08',
                   'bg_button': '#122919',
                   'bg_button_hover': '#1B3D25',
                   'bg_card': '#08140C',
                   'bg_dropdown': '#0B1A10',
                   'bg_elevated': '#0E1F13',
                   'bg_field': '#0B1A10',
                   'bg_hero': '#040906',
                   'bg_input': '#060C08',
                   'bg_sidebar': '#060C08',
                   'bg_surface': '#08140C',
                   'border': '#1B3D25',
                   'border_focus': '#46AB6E',
                   'border_hover': '#2A5C38',
                   'brand_border': '#1B3D25',
                   'check_checked': '#46AB6E',
                   'check_indicator': '#060C08',
                   'content_bg': '#040906',
                   'cookie_browse_bg': '#0B1A10',
                   'cookie_browse_border': '#2A5C38',
                   'cookie_browse_hover': '#122919',
                   'header_bg': '#060C08',
                   'header_border': '#122919',
                   'lang_toggle_bg': '#0B1A10',
                   'lang_toggle_border': '#224A2E',
                   'lang_toggle_hover': '#122919',
                   'log_bg': '#040906',
                   'name': 'Sage',
                   'progress': '#388A58',
                   'scroll_bg': '#040906',
                   'scroll_handle': '#224A2E',
                   'scroll_handle_hover': '#357347',
                   'seg_button_bg': '#0E1F13',
                   'seg_button_checked': '#2C7348',
                   'sidebar_active': '#122919',
                   'sidebar_active_border': '#46AB6E',
                   'sidebar_footer': '#538A6E',
                   'sidebar_hover': '#0E1F13',
                   'step_badge': '#2C7348',
                   'swatch_blend': '#024A32',
                   'swatch_end': '#040906',
                   'swatch_ring': '#388A58',
                   'swatch_start': '#10B981',
                   'table_stripe': '#08140C',
                   'table_stripe_border': '#1B3D25',
                   'text_accent': '#10B981',
                   'text_body': '#BBEBD1',
                   'text_dim': '#538A6E',
                   'text_primary': '#E6FCEF',
                   'text_secondary': '#7EBA9C',
                   'warning_bg': '#241C00',
                   'warning_text': '#E6BA22'},
    'nord': {   'accent': '#115663',
                'accent_bright': '#1D8296',
                'accent_bright_hover': '#2299B0',
                'accent_hover': '#25A4BD',
                'accent_soft': '#00485C',
                'accent_text': '#FFFFFF',
                'bg': '#03070C',
                'bg_brand': '#050A11',
                'bg_button': '#111D2B',
                'bg_button_hover': '#1A2C40',
                'bg_card': '#09111A',
                'bg_dropdown': '#0C1521',
                'bg_elevated': '#0E1A26',
                'bg_field': '#0C1521',
                'bg_hero': '#03070C',
                'bg_input': '#050A11',
                'bg_sidebar': '#050A11',
                'bg_surface': '#09111A',
                'border': '#1A2C40',
                'border_focus': '#25A4BD',
                'border_hover': '#27425E',
                'brand_border': '#1A2C40',
                'check_checked': '#25A4BD',
                'check_indicator': '#050A11',
                'content_bg': '#03070C',
                'cookie_browse_bg': '#0C1521',
                'cookie_browse_border': '#27425E',
                'cookie_browse_hover': '#111D2B',
                'header_bg': '#050A11',
                'header_border': '#132233',
                'lang_toggle_bg': '#0C1521',
                'lang_toggle_border': '#20364F',
                'lang_toggle_hover': '#132233',
                'log_bg': '#03070C',
                'name': 'Harbor',
                'progress': '#1D8296',
                'scroll_bg': '#03070C',
                'scroll_handle': '#20364F',
                'scroll_handle_hover': '#335378',
                'seg_button_bg': '#0E1A26',
                'seg_button_checked': '#166C7D',
                'sidebar_active': '#132233',
                'sidebar_active_border': '#25A4BD',
                'sidebar_footer': '#5B7894',
                'sidebar_hover': '#0E1A26',
                'step_badge': '#166C7D',
                'swatch_blend': '#005A6B',
                'swatch_end': '#03070C',
                'swatch_ring': '#1D8296',
                'swatch_start': '#00E5FF',
                'table_stripe': '#09111A',
                'table_stripe_border': '#1A2C40',
                'text_accent': '#00E5FF',
                'text_body': '#C2D6EB',
                'text_dim': '#5B7894',
                'text_primary': '#E6F1FC',
                'text_secondary': '#85A3C2',
                'warning_bg': '#292100',
                'warning_text': '#FAD02C'},
    'solarized': {   'accent': '#CCCCCC',
                     'accent_bright': '#D4D4D4',
                     'accent_bright_hover': '#FFFFFF',
                     'accent_hover': '#FFFFFF',
                     'accent_soft': '#525252',
                     'accent_text': '#050505',
                     'bg': '#000000',
                     'bg_brand': '#050505',
                     'bg_button': '#1A1A1A',
                     'bg_button_hover': '#262626',
                     'bg_card': '#0A0A0A',
                     'bg_dropdown': '#111111',
                     'bg_elevated': '#141414',
                     'bg_field': '#121212',
                     'bg_hero': '#000000',
                     'bg_input': '#050505',
                     'bg_sidebar': '#050505',
                     'bg_surface': '#0A0A0A',
                     'border': '#262626',
                     'border_focus': '#FFFFFF',
                     'border_hover': '#404040',
                     'brand_border': '#262626',
                     'check_checked': '#FFFFFF',
                     'check_indicator': '#050505',
                     'content_bg': '#000000',
                     'cookie_browse_bg': '#121212',
                     'cookie_browse_border': '#404040',
                     'cookie_browse_hover': '#1A1A1A',
                     'header_bg': '#050505',
                     'header_border': '#1A1A1A',
                     'lang_toggle_bg': '#121212',
                     'lang_toggle_border': '#333333',
                     'lang_toggle_hover': '#1A1A1A',
                     'log_bg': '#000000',
                     'name': 'Obsidian',
                     'progress': '#D4D4D4',
                     'scroll_bg': '#000000',
                     'scroll_handle': '#333333',
                     'scroll_handle_hover': '#525252',
                     'seg_button_bg': '#141414',
                     'seg_button_checked': '#E0E0E0',
                     'sidebar_active': '#1A1A1A',
                     'sidebar_active_border': '#FFFFFF',
                     'sidebar_footer': '#737373',
                     'sidebar_hover': '#141414',
                     'step_badge': '#E0E0E0',
                     'swatch_blend': '#888888',
                     'swatch_end': '#000000',
                     'swatch_ring': '#FFFFFF',
                     'swatch_start': '#FFFFFF',
                     'table_stripe': '#0A0A0A',
                     'table_stripe_border': '#262626',
                     'text_accent': '#FFFFFF',
                     'text_body': '#E0E0E0',
                     'text_dim': '#737373',
                     'text_primary': '#FFFFFF',
                     'text_secondary': '#A3A3A3',
                     'warning_bg': '#261A00',
                     'warning_text': '#FACC15'},
    'wine': {   'accent': '#8A1222',
                'accent_bright': '#B01E31',
                'accent_bright_hover': '#CC2137',
                'accent_hover': '#D42239',
                'accent_soft': '#5C1A24',
                'accent_text': '#FFFFFF',
                'bg': '#070404',
                'bg_brand': '#090506',
                'bg_button': '#1A1112',
                'bg_button_hover': '#2B1A1E',
                'bg_card': '#0F0A0B',
                'bg_dropdown': '#140C0D',
                'bg_elevated': '#170F11',
                'bg_field': '#140C0D',
                'bg_hero': '#070404',
                'bg_input': '#090506',
                'bg_sidebar': '#090506',
                'bg_surface': '#0F0A0B',
                'border': '#2B1A1E',
                'border_focus': '#D42239',
                'border_hover': '#4A2C33',
                'brand_border': '#2B1A1E',
                'check_checked': '#D42239',
                'check_indicator': '#090506',
                'content_bg': '#070404',
                'cookie_browse_bg': '#140C0D',
                'cookie_browse_border': '#4A2C33',
                'cookie_browse_hover': '#1A1112',
                'header_bg': '#090506',
                'header_border': '#1F1416',
                'lang_toggle_bg': '#140C0D',
                'lang_toggle_border': '#362125',
                'lang_toggle_hover': '#1F1416',
                'log_bg': '#070404',
                'name': 'Garnet',
                'progress': '#B01E31',
                'scroll_bg': '#070404',
                'scroll_handle': '#362125',
                'scroll_handle_hover': '#54333A',
                'seg_button_bg': '#170F11',
                'seg_button_checked': '#9C1728',
                'sidebar_active': '#1F1416',
                'sidebar_active_border': '#D42239',
                'sidebar_footer': '#7A5C61',
                'sidebar_hover': '#170F11',
                'step_badge': '#9C1728',
                'swatch_blend': '#730C1E',
                'swatch_end': '#070404',
                'swatch_ring': '#B01E31',
                'swatch_start': '#E6193C',
                'table_stripe': '#0F0A0B',
                'table_stripe_border': '#2B1A1E',
                'text_accent': '#FF2A4D',
                'text_body': '#E2CED1',
                'text_dim': '#7A5C61',
                'text_primary': '#FFF0F2',
                'text_secondary': '#A8898E',
                'warning_bg': '#2B1A00',
                'warning_text': '#F5B942'}}

# Hidden compatibility alias for users who had the old sixth theme saved.
THEMES["monokai"] = THEMES["dracula"]
_LEGACY_THEME_KEYS = {"monokai": "dracula"}

# List of theme keys in display order.
THEME_KEYS = ["solarized", "wine", "nord", "dracula", "gruvbox"]


def normalize_theme_key(theme_key: str) -> str:
    """Return a visible theme key, preserving old saved preferences."""
    if theme_key in THEME_KEYS:
        return theme_key
    return _LEGACY_THEME_KEYS.get(theme_key, THEME_KEYS[0])


def build_theme_swatch_stylesheet(p: dict[str, str]) -> str:
    """Return the per-button QSS used by the theme picker preview."""
    return (
        "#themeSwatch {"
        "  background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
        f"    stop:0 {p['swatch_start']},"
        f"    stop:0.46 {p['swatch_start']},"
        f"    stop:0.52 {p['swatch_blend']},"
        f"    stop:1 {p['swatch_end']});"
        "  border-radius: 22px; min-width: 44px; max-width: 44px;"
        "  min-height: 44px; max-height: 44px;"
        "  border: 2px solid transparent; padding: 0; margin: 0;"
        "}"
        f"#themeSwatch:hover {{ border-color: {p['swatch_ring']}; }}"
        f"#themeSwatch:checked {{ border-color: {p['swatch_ring']}; border-width: 3px; }}"
    )


def _build_qss(p: dict[str, str]) -> str:
    """Build the full QSS for a single palette."""
    return f"""
/* ================================================================
   Global
   ================================================================ */
QMainWindow {{
    background-color: {p['bg']};
    color: {p['text_body']};
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 14px;
}}
QWidget {{ background-color: transparent; }}
QLabel {{ color: {p['text_body']}; background-color: transparent; }}
QScrollArea {{ border: none; background-color: transparent; }}
QScrollBar:vertical {{
    background: {p['scroll_bg']}; width: 10px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {p['scroll_handle']}; border-radius: 5px; min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{ background: {p['scroll_handle_hover']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* ================================================================
   App shell
   ================================================================ */
#sidebar {{
    background-color: {p['bg_sidebar']};
    border-right: 1px solid {p['border']};
}}
#sidebarBrand {{
    background-color: {p['bg_brand']};
    border: 1px solid {p['brand_border']};
    border-radius: 8px;
}}
#sidebarTitle {{ color: {p['text_primary']}; font-size: 20px; font-weight: 700; }}
#sidebarHint {{ color: {p['text_secondary']}; font-size: 12px; font-weight: 400; }}
#sidebarButton {{
    background-color: transparent; color: {p['text_dim']};
    border: 1px solid transparent; border-radius: 8px;
    padding: 12px 14px; text-align: left; font-size: 14px; font-weight: 600;
}}
#sidebarButton:hover {{
    background-color: {p['sidebar_hover']};
    border-color: {p['border_hover']}; color: {p['text_primary']};
}}
#sidebarButton:checked {{
    background-color: {p['sidebar_active']};
    border-color: {p['sidebar_active_border']};
    color: {p['text_primary']}; font-weight: 700;
}}
#sidebarFooter {{ color: {p['sidebar_footer']}; font-size: 11px; }}
#header {{
    background-color: {p['header_bg']};
    border-bottom: 1px solid {p['header_border']};
}}
#contentRoot {{ background-color: {p['content_bg']}; }}

/* ================================================================
   Surfaces
   ================================================================ */
#modernCard {{
    background-color: {p['bg_card']};
    border: 1px solid {p['border']}; 
    border-radius: 12px;
}}
#primaryCard, #statusCard, #settingsCard, #setupCard, #helpCard {{
    background-color: {p['bg_surface']};
    border: 1px solid {p['border']}; border-radius: 8px;
}}
#primaryCard {{ background-color: {p['bg_card']}; }}
#statusCard {{ background-color: {p['bg_surface']}; }}
#inlinePanel, #fieldPanel, #embedPanel, #binaryRow, #stepRow {{
    background-color: {p['table_stripe']};
    border: 1px solid {p['table_stripe_border']}; border-radius: 8px;
}}
#heroStrip {{
    background-color: {p['bg_hero']};
    border: 1px solid {p['border']}; border-radius: 8px;
}}

/* ================================================================
   Typography
   ================================================================ */
#appTitle {{ color: {p['text_primary']}; font-size: 23px; font-weight: 700; }}
#pageTitle {{ color: {p['text_primary']}; font-size: 21px; font-weight: 700; }}
#appTagline, #mutedText {{ color: {p['text_secondary']}; font-size: 13px; font-weight: 400; }}
#sectionLabel {{ color: {p['text_accent']}; font-size: 12px; font-weight: 700; text-transform: uppercase; }}
#fieldLabel {{ color: {p['text_body']}; font-size: 13px; font-weight: 600; }}
#stepBadge {{
    background-color: {p['step_badge']}; color: {p['accent_text']};
    font-weight: 700; font-size: 13px; border-radius: 8px;
}}
#stepText {{ color: {p['text_dim']}; font-size: 13px; }}

/* ================================================================
   Inputs / Combo
   ================================================================ */
QLineEdit, QComboBox {{
    background-color: {p['bg_input']}; color: {p['text_primary']};
    border: 1px solid {p['border']}; border-radius: 8px;
    padding: 9px 13px; font-size: 13px;
    selection-background-color: {p['accent_soft']}; selection-color: {p['text_primary']};
}}
QLineEdit:hover, QComboBox:hover {{ border-color: {p['border_hover']}; }}
QLineEdit:focus, QComboBox:focus {{
    border-color: {p['accent_hover']}; background-color: {p['bg_input']};
}}
QLineEdit:disabled, QComboBox:disabled {{
    background-color: {p['bg_surface']}; color: {p['text_dim']}; border-color: {p['border']};
}}
QComboBox::drop-down {{ border: none; width: 30px; }}
QComboBox QAbstractItemView {{
    background-color: {p['bg_dropdown']}; color: {p['text_body']};
    border: 1px solid {p['border']}; border-radius: 8px; padding: 6px;
    selection-background-color: {p['accent']}; selection-color: {p['text_primary']};
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    min-height: 30px; padding: 7px 10px; border-radius: 6px;
}}
QComboBox QAbstractItemView::item:hover {{ background-color: {p['sidebar_hover']}; }}

#video_url_input, #modern_url_input {{
    font-size: 16px; padding: 14px 20px; border-radius: 12px;
    background-color: {p['table_stripe']}; border: 1px solid {p['border']};
}}
#video_url_input:focus, #modern_url_input:focus {{
    background-color: {p['bg_input']}; border-color: {p['accent_bright']};
}}

/* ================================================================
   Segmented button & Hub Switcher
   ================================================================ */
#segButton {{
    background-color: {p['seg_button_bg']}; color: {p['text_dim']};
    border: 1px solid {p['border']}; border-radius: 8px;
    font-size: 13px; font-weight: 700; padding: 8px 14px;
}}
#segButton:hover {{ border-color: {p['accent_soft']}; color: {p['text_primary']}; }}
#segButton:checked {{
    background-color: {p['seg_button_checked']}; color: {p['accent_text']};
    border-color: {p['accent_hover']};
}}

#hubSwitchButton {{
    background-color: {p['seg_button_bg']}; color: {p['text_dim']};
    border: 1px solid {p['border']}; border-radius: 10px;
    font-size: 15px; font-weight: 700; padding: 10px 22px;
}}
#hubSwitchButton:hover {{ border-color: {p['accent_soft']}; color: {p['text_primary']}; }}
#hubSwitchButton:checked {{
    background-color: {p['seg_button_checked']}; color: {p['accent_text']};
    border-color: {p['accent_hover']};
}}

/* ================================================================
   Buttons
   ================================================================ */
QPushButton {{
    background-color: {p['bg_button']}; color: {p['text_body']};
    border: 1px solid {p['border']}; border-radius: 8px;
    padding: 10px 18px; font-weight: 700; font-size: 13px;
}}
QPushButton:hover {{
    background-color: {p['bg_button_hover']};
    border-color: {p['border_hover']}; color: {p['text_primary']};
}}
QPushButton:pressed {{ background-color: {p['bg_surface']}; border-color: {p['accent_soft']}; }}
QPushButton:focus {{ border-color: {p['accent_hover']}; }}
QPushButton:disabled {{
    background-color: {p['bg_surface']}; color: {p['text_dim']}; border-color: {p['border']};
}}
#cookie_browse_button, #output_browse_button, #subDownloadBtn {{
    background-color: {p['cookie_browse_bg']}; color: {p['text_primary']};
    border: 1px solid {p['cookie_browse_border']}; font-weight: 700;
}}
#cookie_browse_button:hover, #output_browse_button:hover, #subDownloadBtn:hover {{
    background-color: {p['cookie_browse_hover']}; border-color: {p['accent_hover']};
}}
#download_button, #modern_download_button {{
    background-color: {p['accent_bright']}; color: {p['accent_text']};
    border: 1px solid {p['accent_hover']}; font-weight: 700; font-size: 15px;
    border-radius: 8px; min-height: 46px;
}}
#modern_download_button {{ font-size: 16px; font-weight: 800; border-radius: 12px; }}
#download_button:hover, #modern_download_button:hover {{ background-color: {p['accent_bright_hover']}; border-color: {p['accent_hover']}; }}
#download_button:pressed, #modern_download_button:pressed {{ background-color: {p['accent']}; }}
#download_button:disabled, #modern_download_button:disabled {{
    background-color: {p['bg_surface']}; color: {p['text_dim']}; border-color: {p['border']};
}}
#queue_add_button {{
    background-color: #1E293B; color: #38BDF8;
    border: 1px solid #38BDF8; font-weight: 700; font-size: 14px;
    border-radius: 8px; min-height: 46px; padding: 8px 16px;
}}
#queue_add_button:hover {{
    background-color: #38BDF8; color: #0F172A;
}}
#queue_add_button:disabled {{
    background-color: {p['bg_surface']}; color: {p['text_dim']}; border-color: {p['border']};
}}
#queue_start_button {{
    background-color: #10B981; color: #FFFFFF;
    border: 1px solid #059669; font-weight: 800; font-size: 14px;
    border-radius: 8px; min-height: 46px; padding: 8px 18px;
}}
#queue_start_button:hover {{
    background-color: #34D399; border-color: #10B981;
}}
#queue_start_button:disabled {{
    background-color: {p['bg_surface']}; color: {p['text_dim']}; border-color: {p['border']};
}}
#cancel_button {{
    background-color: transparent; color: #EF4444;
    border: 1px solid transparent; font-weight: 700; border-radius: 8px;
}}
#cancel_button:hover {{
    background-color: rgba(239, 68, 68, 0.12); border-color: rgba(239, 68, 68, 0.35);
    color: #F87171;
}}
#cancel_button:disabled {{
    background-color: transparent; color: {p['text_dim']}; border-color: transparent;
}}
#ghostButton {{
    background-color: transparent; color: {p['text_body']};
    border: 1px solid transparent; font-weight: 700; border-radius: 8px;
}}
#ghostButton:hover {{
    background-color: {p['sidebar_active']}; border-color: {p['accent_hover']};
    color: {p['text_primary']};
}}
#ghostButton:disabled {{
    background-color: transparent; color: {p['text_dim']}; border-color: transparent;
}}
#langToggle {{
    background-color: {p['lang_toggle_bg']}; color: {p['text_dim']};
    border: 1px solid {p['lang_toggle_border']}; border-radius: 8px;
    font-weight: 700; font-size: 12px;
}}
#langToggle:hover {{
    background-color: {p['lang_toggle_hover']}; color: {p['text_primary']};
    border-color: {p['accent_soft']};
}}

/* ================================================================
   Segmented button & Hub Switcher
   ================================================================ */
#segButton {{
    background-color: {p['seg_button_bg']}; color: {p['text_dim']};
    border: 1px solid {p['border']}; border-radius: 8px;
    font-size: 13px; font-weight: 700; padding: 8px 14px;
}}
#segButton:hover {{ border-color: {p['accent_soft']}; color: {p['text_primary']}; }}
#segButton:checked {{
    background-color: {p['seg_button_checked']}; color: {p['accent_text']};
    border-color: {p['accent_hover']};
}}

#hubSwitchButton {{
    background-color: {p['seg_button_bg']}; color: {p['text_dim']};
    border: 1px solid {p['border']}; border-radius: 10px;
    font-size: 15px; font-weight: 700; padding: 10px 22px;
}}
#hubSwitchButton:hover {{ border-color: {p['accent_soft']}; color: {p['text_primary']}; }}
#hubSwitchButton:checked {{
    background-color: {p['seg_button_checked']}; color: {p['accent_text']};
    border-color: {p['accent_hover']};
}}

/* ================================================================
   Checks and toggles
   ================================================================ */
QCheckBox {{ color: {p['text_body']}; font-size: 13px; font-weight: 600; spacing: 10px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 5px;
    background-color: {p['check_indicator']}; border: 1px solid {p['border']};
}}
QCheckBox::indicator:hover {{ border-color: {p['accent_bright']}; }}
QCheckBox:focus {{ color: {p['text_primary']}; }}
QCheckBox::indicator:checked {{
    background-color: {p['check_checked']}; border-color: {p['accent_hover']};
}}
#embedPanel QCheckBox {{ color: {p['text_body']}; font-size: 13px; font-weight: 600; }}
#embedPanel QCheckBox::indicator {{ width: 20px; height: 20px; border-radius: 6px; }}
#membersToggle, #thumbnailToggle {{
    background-color: {p['bg_input']}; color: {p['text_body']};
    border: 1px solid {p['border']}; border-radius: 8px;
    padding: 10px 14px; text-align: left; font-size: 13px; font-weight: 700;
}}
#membersToggle:hover, #thumbnailToggle:hover {{
    background-color: {p['sidebar_hover']}; border-color: {p['accent_soft']}; color: {p['text_primary']};
}}
#membersToggle:checked, #thumbnailToggle:checked {{
    background-color: {p['sidebar_active']}; border-color: {p['accent_hover']}; color: {p['text_primary']};
}}

/* ================================================================
   Progress and status
   ================================================================ */
QProgressBar {{
    background-color: {p['bg']}; border: 1px solid {p['border']};
    border-radius: 8px; text-align: center;
    color: {p['text_primary']}; font-size: 12px; font-weight: 700;
}}
QProgressBar::chunk {{ background-color: {p['progress']}; border-radius: 7px; }}
#status_label {{ color: {p['text_primary']}; font-size: 15px; font-weight: 700; }}

/* ================================================================
   Log panel
   ================================================================ */
#logPanel {{
    background-color: {p['log_bg']}; border: 1px solid {p['border']}; border-radius: 8px;
}}
#logTitle {{ color: {p['text_accent']}; font-size: 12px; font-weight: 700; text-transform: uppercase; }}
QPlainTextEdit {{
    background-color: {p['bg']}; color: {p['text_dim']};
    font-family: "Cascadia Code", "Consolas", monospace; font-size: 12px;
    border: 1px solid {p['border']}; border-radius: 8px; padding: 10px;
    selection-background-color: {p['accent_soft']}; selection-color: {p['text_primary']};
}}
QPlainTextEdit:focus {{ border-color: {p['border_hover']}; }}

/* ================================================================
   Warning and badges
   ================================================================ */
#warningBox {{
    background-color: {p['warning_bg']}; border: 1px solid {p['border']}; border-radius: 8px;
}}
#warningLabel {{ color: {p['warning_text']}; font-size: 12px; font-weight: 500; }}

/* ================================================================
   Theme swatch
   ================================================================ */
#themeSwatch {{
    border-radius: 22px; min-width: 44px; max-width: 44px;
    min-height: 44px; max-height: 44px; border: 2px solid transparent;
    padding: 0; margin: 0;
}}
#themeSwatch:hover {{ border-color: {p['accent_hover']}; }}
#themeSwatch:checked {{ border-color: {p['accent_hover']}; border-width: 3px; }}
#settingsSeparator {{
    color: {p['border']}; background-color: {p['border']};
    border: none; min-height: 1px; max-height: 1px;
}}
#urlPrefixLabel {{
    color: {p['text_primary']};
    font-size: 15px;
    font-weight: 700;
    padding-left: 2px;
}}
/* ================================================================
   Video info panel
   ================================================================ */
#videoInfoCard {{
    background-color: {p['bg_card']};
    border: 1px solid {p['border']}; border-radius: 12px;
}}
#thumbnailFrame {{
    background-color: {p['bg_surface']};
    border: 1px solid {p['border']}; border-radius: 10px;
    min-width: 384px; max-width: 384px;
    min-height: 216px; max-height: 216px;
}}
#thumbnailLabel {{
    color: {p['text_dim']}; font-size: 12px;
    background-color: transparent;
}}
#infoFieldLabel {{
    color: {p['text_secondary']}; font-size: 12px; font-weight: 700;
}}
#infoFieldValue {{
    color: {p['text_primary']}; font-size: 13px; font-weight: 500;
}}
#descriptionBox {{
    background-color: {p['bg_surface']}; color: {p['text_body']};
    border: 1px solid {p['border']}; border-radius: 8px;
    font-size: 12px; padding: 8px;
}}
#infoLoadingLabel {{
    color: {p['text_dim']}; font-size: 13px; font-style: italic;
}}
#downloadOptionsCard {{
    background-color: {p['bg_card']};
    border: 1px solid {p['border']}; border-radius: 12px;
}}
/* ================================================================
   Downloads / History page
   ================================================================ */
#historyToolbar {{
    background-color: {p['bg_card']};
    border: 1px solid {p['border']}; border-radius: 10px;
}}
#historySearchInput {{
    background-color: {p['bg_input']}; color: {p['text_primary']};
    border: 1px solid {p['border']}; border-radius: 8px;
    padding: 8px 14px; font-size: 13px;
}}
#historySearchInput:focus {{
    border-color: {p['accent_bright']}; background-color: {p['bg_input']};
}}
#historyToolButton {{
    background-color: {p['bg_button']}; color: {p['text_primary']};
    border: 1px solid {p['border']}; border-radius: 8px;
    font-size: 12px; font-weight: 700; padding: 8px 12px;
}}
#historyToolButton:hover {{
    background-color: {p['bg_button_hover']}; border-color: {p['accent_soft']};
}}
#historyDeleteButton {{
    background-color: {p['bg_button']}; color: #ff6b6b;
    border: 1px solid {p['border']}; border-radius: 8px;
    font-size: 12px; font-weight: 700; padding: 8px 12px;
}}
#historyDeleteButton:hover {{
    background-color: rgba(255, 107, 107, 0.15); border-color: #ff6b6b;
}}
#historyClearButton {{
    background-color: {p['bg_button']}; color: {p['text_secondary']};
    border: 1px solid {p['border']}; border-radius: 8px;
    font-size: 12px; font-weight: 700; padding: 8px 12px;
}}
#historyClearButton:hover {{
    background-color: {p['bg_button_hover']}; border-color: {p['border_hover']};
    color: {p['text_primary']};
}}
#historyTypeCombo {{
    background-color: {p['bg_input']}; color: {p['text_primary']};
    border: 1px solid {p['border']}; border-radius: 8px;
    padding: 6px 12px; font-size: 12px; font-weight: 600;
}}
#historyListWidget {{
    background-color: {p['bg_card']}; color: {p['text_primary']};
    border: 1px solid {p['border']}; border-radius: 10px;
    padding: 6px; outline: none;
}}
#historyListWidget::item {{
    background-color: transparent; border-radius: 8px;
    margin: 2px 0px; padding: 0px;
    border: 1px solid transparent;
}}
#historyListWidget::item:hover {{
    background-color: {p['sidebar_hover']}; border-color: {p['border']};
}}
#historyListWidget::item:selected {{
    background-color: {p['sidebar_active']}; border-color: {p['accent_hover']};
}}
#historyThumbFrame {{
    background-color: {p['bg_surface']};
    border: 1px solid {p['border']}; border-radius: 6px;
}}
#historyItemTitle {{
    color: {p['text_primary']}; font-size: 13px; font-weight: 700;
}}
#historyItemFormat {{
    color: {p['text_accent']}; font-size: 11px; font-weight: 700;
}}
#historyItemDetails {{
    color: {p['text_secondary']}; font-size: 11px; font-weight: 400;
}}
#historyEmptyLabel {{
    color: {p['text_dim']}; font-size: 14px; font-style: italic;
    padding: 40px;
}}
"""


def build_stylesheet(theme_key: str) -> str:
    """Return the QSS for *theme_key*."""
    palette = THEMES[normalize_theme_key(theme_key)]
    return _build_qss(palette)


def apply_theme(app_or_widget, theme_key: str = "wine") -> None:
    """Apply the theme stylesheet to a QApplication or QWidget."""
    app_or_widget.setStyleSheet(build_stylesheet(theme_key))
