"""Downloads / History page — clean, modern download management.

Allows viewing past downloads (videos, audio, thumbnails), searching through history,
opening containing folder, playing media, viewing metadata details, and deleting files.
"""

from __future__ import annotations

import base64
import os
import subprocess
from pathlib import Path

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from videcook.services.history_service import (
    HistoryItem,
    clear_history_entries,
    delete_history_entry,
    load_history,
    resolve_history_item_file,
)
from videcook.utils.i18n import LanguageManager


class HistoryItemWidget(QWidget):
    """Custom widget rendered for each history record item in the list."""

    def __init__(self, item: HistoryItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.item = item
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(14)

        # 1. Thumbnail / Icon container
        thumb_container = QFrame()
        thumb_container.setObjectName("historyThumbFrame")
        thumb_container.setFixedSize(88, 54)
        thumb_layout = QVBoxLayout(thumb_container)
        thumb_layout.setContentsMargins(0, 0, 0, 0)
        thumb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        thumb_lbl = QLabel()
        thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Render thumbnail if base64 data exists
        pixmap_set = False
        if self.item.thumbnail_b64:
            try:
                raw_bytes = base64.b64decode(self.item.thumbnail_b64)
                px = QPixmap()
                if px.loadFromData(raw_bytes) and not px.isNull():
                    scaled = px.scaled(
                        QSize(86, 52),
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    thumb_lbl.setPixmap(scaled)
                    pixmap_set = True
            except Exception:
                pass

        if not pixmap_set:
            # Fallback icon by download type
            if self.item.download_type == "audio":
                thumb_lbl.setText("🎵")
            elif self.item.download_type == "thumbnail":
                thumb_lbl.setText("🖼️")
            else:
                thumb_lbl.setText("🎬")
            font = thumb_lbl.font()
            font.setPointSize(16)
            thumb_lbl.setFont(font)

        thumb_layout.addWidget(thumb_lbl)
        layout.addWidget(thumb_container)

        # 2. Text details column
        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Title
        title_lbl = QLabel(self.item.title or Path(self.item.file_path).name or "İsimsiz")
        title_lbl.setObjectName("historyItemTitle")
        title_lbl.setWordWrap(False)
        text_col.addWidget(title_lbl)

        # Format / Type line
        format_text = self.item.format_label
        if not format_text:
            if self.item.download_type == "audio":
                format_text = "SES"
            elif self.item.download_type == "thumbnail":
                format_text = "THUMBNAIL"
            else:
                format_text = "VIDEO"
        format_lbl = QLabel(format_text)
        format_lbl.setObjectName("historyItemFormat")
        text_col.addWidget(format_lbl)

        # Details: Size, Duration, Date
        details_parts = []
        details_parts.append(f"Dosya boyutu: {self.item.formatted_size()}")
        if self.item.duration_seconds > 0:
            details_parts.append(f"Süre: {self.item.formatted_duration()}")
        if self.item.timestamp:
            details_parts.append(self.item.formatted_date())

        details_lbl = QLabel("  •  ".join(details_parts))
        details_lbl.setObjectName("historyItemDetails")
        text_col.addWidget(details_lbl)

        layout.addLayout(text_col, stretch=1)


class HistoryDetailsDialog(QDialog):
    """Detailed popup dialog showing all download properties."""

    def __init__(
        self,
        item: HistoryItem,
        i18n: LanguageManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.item = item
        self._i18n = i18n
        self.setWindowTitle(i18n.get_text("history.details_title"))
        self.setMinimumWidth(560)
        self._build_ui()

    def _build_ui(self) -> None:
        t = self._i18n.get_text
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        def make_val(text: str) -> QLabel:
            lbl = QLabel(text or "—")
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            return lbl

        form.addRow(QLabel(f"<b>{t('info.title')}</b>"), make_val(self.item.title))
        form.addRow(QLabel(f"<b>{t('label.type')}:</b>"), make_val(self.item.download_type.upper()))
        form.addRow(QLabel(f"<b>{t('label.quality')}:</b>"), make_val(self.item.format_label))
        form.addRow(QLabel(f"<b>{t('info.filesize')}</b>"), make_val(self.item.formatted_size()))
        if self.item.duration_seconds > 0:
            form.addRow(QLabel(f"<b>{t('info.duration')}</b>"), make_val(self.item.formatted_duration()))
        form.addRow(QLabel(f"<b>{t('history.file_path')}:</b>"), make_val(self.item.file_path))
        if self.item.url:
            form.addRow(QLabel(f"<b>URL:</b>"), make_val(self.item.url))
        form.addRow(QLabel(f"<b>{t('history.date')}:</b>"), make_val(self.item.formatted_date()))

        layout.addLayout(form)

        # Action button row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        open_folder_btn = QPushButton(t("action.show_folder"))
        open_folder_btn.clicked.connect(self._on_open_folder)
        btn_row.addWidget(open_folder_btn)

        open_file_btn = QPushButton(t("history.open_file"))
        open_file_btn.clicked.connect(self._on_open_file)
        btn_row.addWidget(open_file_btn)

        btn_row.addStretch(1)

        close_btn = QPushButton(t("action.close"))
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def _on_open_folder(self) -> None:
        p = resolve_history_item_file(self.item) or (Path(self.item.file_path) if self.item.file_path else None)
        if not p:
            QMessageBox.warning(self, "Videcook", self._i18n.get_text("history.folder_not_found"))
            return
        target_dir = p.parent if p.exists() else p
        if os.name == "nt":
            if p.is_file():
                subprocess.Popen(f'explorer /select,"{os.path.normpath(str(p))}"')
            elif target_dir.exists():
                os.startfile(str(target_dir))
            else:
                QMessageBox.warning(self, "Videcook", self._i18n.get_text("history.folder_not_found"))
        else:
            subprocess.Popen(["xdg-open", str(target_dir)])

    def _on_open_file(self) -> None:
        p = resolve_history_item_file(self.item)
        if not p or not p.is_file():
            QMessageBox.warning(self, "Videcook", self._i18n.get_text("history.file_not_found"))
            return
        if os.name == "nt":
            os.startfile(str(p))
        else:
            subprocess.Popen(["xdg-open", str(p)])


class HistoryPage(QWidget):
    """Downloads history management page."""

    def __init__(self, i18n: LanguageManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._items: list[HistoryItem] = []
        self._build_ui()
        self.retranslate()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._load_and_refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 16, 32, 24)
        layout.setSpacing(14)

        # ================================================================
        # TOP TOOLBAR
        # ================================================================
        toolbar_card = QFrame()
        toolbar_card.setObjectName("historyToolbar")
        toolbar_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        tb_layout = QHBoxLayout(toolbar_card)
        tb_layout.setContentsMargins(14, 10, 14, 10)
        tb_layout.setSpacing(10)

        # 1. Search Box
        self._search_input = QLineEdit()
        self._search_input.setObjectName("historySearchInput")
        self._search_input.setPlaceholderText("İndirme geçmişinde ara...")
        self._search_input.setMinimumHeight(38)
        self._search_input.setMinimumWidth(220)
        self._search_input.textChanged.connect(self._filter_items)
        tb_layout.addWidget(self._search_input, stretch=2)

        # 2. Action Buttons
        self._open_folder_btn = QPushButton("📁 Klasörü aç")
        self._open_folder_btn.setObjectName("historyToolButton")
        self._open_folder_btn.setMinimumHeight(38)
        self._open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_folder_btn.clicked.connect(self._on_open_folder_clicked)
        tb_layout.addWidget(self._open_folder_btn)

        self._play_btn = QPushButton("▶️ Aç")
        self._play_btn.setObjectName("historyToolButton")
        self._play_btn.setMinimumHeight(38)
        self._play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._play_btn.clicked.connect(self._on_play_clicked)
        tb_layout.addWidget(self._play_btn)

        self._details_btn = QPushButton("ℹ️ Ayrıntılar")
        self._details_btn.setObjectName("historyToolButton")
        self._details_btn.setMinimumHeight(38)
        self._details_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._details_btn.clicked.connect(self._on_details_clicked)
        tb_layout.addWidget(self._details_btn)

        self._delete_file_btn = QPushButton("🗑️ Dosyayı sil")
        self._delete_file_btn.setObjectName("historyDeleteButton")
        self._delete_file_btn.setMinimumHeight(38)
        self._delete_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._delete_file_btn.clicked.connect(self._on_delete_file_clicked)
        tb_layout.addWidget(self._delete_file_btn)

        self._clear_history_btn = QPushButton("❌ Geçmişi temizle")
        self._clear_history_btn.setObjectName("historyClearButton")
        self._clear_history_btn.setMinimumHeight(38)
        self._clear_history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_history_btn.clicked.connect(self._on_clear_history_clicked)
        tb_layout.addWidget(self._clear_history_btn)

        # 3. Type Filter Dropdown
        self._type_combo = QComboBox()
        self._type_combo.setObjectName("historyTypeCombo")
        self._type_combo.setMinimumHeight(38)
        self._type_combo.addItem("Tümü", "all")
        self._type_combo.addItem("Video", "video")
        self._type_combo.addItem("Ses", "audio")
        self._type_combo.addItem("Thumbnail", "thumbnail")
        self._type_combo.currentIndexChanged.connect(self._filter_items)
        tb_layout.addWidget(self._type_combo)

        layout.addWidget(toolbar_card)

        # ================================================================
        # HISTORY ITEMS LIST
        # ================================================================
        self._list_widget = QListWidget()
        self._list_widget.setObjectName("historyListWidget")
        self._list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._list_widget, stretch=1)

        # Empty state hint
        self._empty_label = QLabel("Henüz indirilmiş bir dosya bulunmuyor.")
        self._empty_label.setObjectName("historyEmptyLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._empty_label)

    # ------------------------------------------------------------------
    # Data loading & filtering
    # ------------------------------------------------------------------

    def _load_and_refresh(self) -> None:
        self._items = load_history()
        self._filter_items()

    def _filter_items(self) -> None:
        query = self._search_input.text().strip().lower()
        selected_type = self._type_combo.currentData() or "all"

        self._list_widget.clear()

        visible_count = 0
        for item in self._items:
            # Type filter
            if selected_type != "all" and item.download_type != selected_type:
                continue

            # Search text filter
            if query:
                searchable = f"{item.title} {item.format_label} {item.file_path}".lower()
                if query not in searchable:
                    continue

            list_item = QListWidgetItem(self._list_widget)
            list_item.setSizeHint(QSize(0, 78))
            list_item.setData(Qt.ItemDataRole.UserRole, item.id)

            custom_widget = HistoryItemWidget(item)
            self._list_widget.addItem(list_item)
            self._list_widget.setItemWidget(list_item, custom_widget)
            visible_count += 1

        is_empty = visible_count == 0
        self._list_widget.setVisible(not is_empty)
        self._empty_label.setVisible(is_empty)

    def _get_selected_item(self) -> HistoryItem | None:
        current_item = self._list_widget.currentItem()
        if not current_item:
            return None
        item_id = current_item.data(Qt.ItemDataRole.UserRole)
        for item in self._items:
            if item.id == item_id:
                return item
        return None

    def _require_selection(self) -> HistoryItem | None:
        """Helper to ensure an item is selected, showing a warning if not."""
        item = self._get_selected_item()
        if not item:
            t = self._i18n.get_text
            QMessageBox.warning(
                self,
                "Videcook",
                t("history.select_item_warning"),
            )
            return None
        return item

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    def _on_item_double_clicked(self, list_item: QListWidgetItem) -> None:
        item_id = list_item.data(Qt.ItemDataRole.UserRole)
        for item in self._items:
            if item.id == item_id:
                self._open_media_file(item)
                break

    def _on_open_folder_clicked(self) -> None:
        item = self._require_selection()
        if not item:
            return

        p = resolve_history_item_file(item) or (Path(item.file_path) if item.file_path else None)
        if not p:
            QMessageBox.warning(
                self,
                "Videcook",
                self._i18n.get_text("history.folder_not_found"),
            )
            return

        target_dir = p.parent if p.exists() else p
        if os.name == "nt":
            if p.is_file():
                subprocess.Popen(f'explorer /select,"{os.path.normpath(str(p))}"')
            elif target_dir.exists():
                os.startfile(str(target_dir))
            else:
                QMessageBox.warning(
                    self,
                    "Videcook",
                    self._i18n.get_text("history.folder_not_found"),
                )
        else:
            subprocess.Popen(["xdg-open", str(target_dir)])

    def _on_play_clicked(self) -> None:
        item = self._require_selection()
        if not item:
            return
        self._open_media_file(item)

    def _open_media_file(self, item: HistoryItem) -> None:
        p = resolve_history_item_file(item)
        if not p or not p.is_file():
            QMessageBox.warning(
                self,
                "Videcook",
                self._i18n.get_text("history.file_not_found"),
            )
            return

        if os.name == "nt":
            os.startfile(str(p))
        else:
            subprocess.Popen(["xdg-open", str(p)])

    def _on_details_clicked(self) -> None:
        item = self._require_selection()
        if not item:
            return
        dialog = HistoryDetailsDialog(item, self._i18n, self)
        dialog.exec()

    def _on_delete_file_clicked(self) -> None:
        item = self._require_selection()
        if not item:
            return

        t = self._i18n.get_text
        confirm = QMessageBox.question(
            self,
            t("history.delete_confirm_title"),
            t("history.delete_confirm_msg").format(title=item.title),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            delete_history_entry(item.id, delete_file=True)
            self._load_and_refresh()

    def _on_clear_history_clicked(self) -> None:
        t = self._i18n.get_text
        if not self._items:
            QMessageBox.information(
                self,
                "Videcook",
                t("history.history_already_empty"),
            )
            return

        confirm = QMessageBox.question(
            self,
            t("history.clear_confirm_title"),
            t("history.clear_confirm_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            clear_history_entries(delete_files=False)
            self._load_and_refresh()

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def retranslate(self) -> None:
        t = self._i18n.get_text
        self._search_input.setPlaceholderText(t("history.search_placeholder"))
        self._open_folder_btn.setText(t("history.open_folder_btn"))
        self._play_btn.setText(t("history.play_btn"))
        self._details_btn.setText(t("history.details_btn"))
        self._delete_file_btn.setText(t("history.delete_file_btn"))
        self._clear_history_btn.setText(t("history.clear_history_btn"))
        self._empty_label.setText(t("history.empty_label"))

        # Retranslate combo items
        self._type_combo.blockSignals(True)
        cur_idx = self._type_combo.currentIndex()
        self._type_combo.clear()
        self._type_combo.addItem(t("history.filter_all"), "all")
        self._type_combo.addItem(t("history.filter_video"), "video")
        self._type_combo.addItem(t("history.filter_audio"), "audio")
        self._type_combo.addItem(t("history.filter_thumbnail"), "thumbnail")
        self._type_combo.setCurrentIndex(max(0, cur_idx))
        self._type_combo.blockSignals(False)

        self._filter_items()

    def set_i18n(self, i18n: LanguageManager) -> None:
        self._i18n = i18n
        self.retranslate()
