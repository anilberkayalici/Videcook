"""Modal dialogs for adding and managing custom edit prompt presets."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from videcook.core.preset_manager import (
    add_edit_preset,
    delete_edit_preset,
    get_edit_presets,
    move_edit_preset,
)


class AddPresetDialog(QDialog):
    """Small modal popup to create and save a new prompt preset."""

    def __init__(self, parent: QWidget | None = None, initial_prompt: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("✨ Yeni Şablon Ekle")
        self.setFixedSize(460, 320)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setStyleSheet("""
            QDialog {
                background-color: #0E0917;
                color: #F8FAFC;
                border: 1px solid #271A40;
                border-radius: 12px;
            }
            QLabel {
                color: #E2E8F0;
                font-weight: 600;
                font-size: 12px;
            }
            QLineEdit, QTextEdit {
                background-color: #160E24;
                border: 1px solid #3C285E;
                border-radius: 8px;
                color: #F8FAFC;
                padding: 8px 10px;
                font-size: 13px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #9333EA;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel("✨ Yeni Hızlı Şablon Oluştur")
        header.setStyleSheet("font-size: 15px; font-weight: 700; color: #C084FC;")
        layout.addWidget(header)

        # Name input
        name_label = QLabel("Şablon Adı / Buton Başlığı:")
        layout.addWidget(name_label)
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Örn: 🔥 Anime Dövüş Sahnesi")
        layout.addWidget(self._name_input)

        # Prompt input
        prompt_label = QLabel("Şablon İstem / Prompt:")
        layout.addWidget(prompt_label)
        self._prompt_input = QTextEdit()
        self._prompt_input.setPlaceholderText("Şablona tıklandığında AI'ya gönderilecek talimat...")
        if initial_prompt.strip():
            self._prompt_input.setPlainText(initial_prompt.strip())
        layout.addWidget(self._prompt_input)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._cancel_btn = QPushButton("İptal")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                color: #CBD5E1;
                font-weight: 600;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        self._cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._cancel_btn)

        self._save_btn = QPushButton("💾 Şablonu Kaydet")
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7C3AED, stop:1 #9333EA);
                border: none;
                border-radius: 8px;
                color: #FFFFFF;
                font-weight: 700;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8B5CF6, stop:1 #A855F7);
            }
        """)
        self._save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self._save_btn)

        layout.addLayout(btn_row)

    def _on_save(self) -> None:
        name = self._name_input.text().strip()
        prompt = self._prompt_input.toPlainText().strip()
        if not name:
            QMessageBox.warning(self, "Uyarı", "Lütfen şablon için bir isim girin.")
            self._name_input.setFocus()
            return
        if not prompt:
            QMessageBox.warning(self, "Uyarı", "Lütfen şablon için bir prompt metni girin.")
            self._prompt_input.setFocus()
            return

        ok = add_edit_preset(name, prompt)
        if ok:
            self.accept()
        else:
            QMessageBox.critical(self, "Hata", "Şablon kaydedilirken bir hata oluştu.")


class ManagePresetsDialog(QDialog):
    """Modal dialog to manage, delete, and reorder custom prompt presets."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("⚙️ Şablonları Yönet")
        self.setFixedSize(560, 440)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setStyleSheet("""
            QDialog {
                background-color: #0E0917;
                color: #F8FAFC;
                border: 1px solid #271A40;
                border-radius: 12px;
            }
            QListWidget {
                background-color: #160E24;
                border: 1px solid #3C285E;
                border-radius: 8px;
                color: #F8FAFC;
                padding: 6px;
            }
            QListWidget::item {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 6px;
                padding: 8px 10px;
                margin-bottom: 4px;
            }
            QListWidget::item:selected {
                background-color: rgba(147, 51, 234, 0.25);
                border: 1px solid #9333EA;
                color: #FFFFFF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel("⚙️ Hızlı Şablon İstemlerini Yönet")
        header.setStyleSheet("font-size: 15px; font-weight: 700; color: #C084FC;")
        layout.addWidget(header)

        # Subtitle
        desc = QLabel("Şablonları silebilir, yukarı/aşağı taşıyabilir veya yeni şablon ekleyebilirsiniz:")
        desc.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(desc)

        # Main horizontal: List + Action Buttons
        main_hbox = QHBoxLayout()
        main_hbox.setSpacing(12)

        self._list_widget = QListWidget()
        main_hbox.addWidget(self._list_widget, stretch=1)

        # Action Buttons
        actions_vbox = QVBoxLayout()
        actions_vbox.setSpacing(8)

        self._add_btn = QPushButton("➕ Yeni Ekle")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.setStyleSheet("""
            QPushButton {
                background: rgba(16, 185, 129, 0.15);
                border: 1px solid rgba(16, 185, 129, 0.4);
                border-radius: 6px;
                color: #34D399;
                font-weight: 600;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background: rgba(16, 185, 129, 0.3);
            }
        """)
        self._add_btn.clicked.connect(self._on_add_new)
        actions_vbox.addWidget(self._add_btn)

        self._up_btn = QPushButton("⬆️ Yukarı")
        self._up_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._up_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                color: #CBD5E1;
                font-weight: 600;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        self._up_btn.clicked.connect(self._on_move_up)
        actions_vbox.addWidget(self._up_btn)

        self._down_btn = QPushButton("⬇️ Aşağı")
        self._down_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._down_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                color: #CBD5E1;
                font-weight: 600;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        self._down_btn.clicked.connect(self._on_move_down)
        actions_vbox.addWidget(self._down_btn)

        self._del_btn = QPushButton("🗑️ Sil")
        self._del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._del_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.15);
                border: 1px solid rgba(239, 68, 68, 0.4);
                border-radius: 6px;
                color: #F87171;
                font-weight: 600;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.3);
            }
        """)
        self._del_btn.clicked.connect(self._on_delete)
        actions_vbox.addWidget(self._del_btn)

        actions_vbox.addStretch(1)
        main_hbox.addLayout(actions_vbox)

        layout.addLayout(main_hbox, stretch=1)

        # Bottom Close button
        bottom_row = QHBoxLayout()
        bottom_row.addStretch(1)
        self._close_btn = QPushButton("Tamam / Kapat")
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7C3AED, stop:1 #9333EA);
                border: none;
                border-radius: 8px;
                color: #FFFFFF;
                font-weight: 700;
                padding: 8px 24px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8B5CF6, stop:1 #A855F7);
            }
        """)
        self._close_btn.clicked.connect(self.accept)
        bottom_row.addWidget(self._close_btn)
        layout.addLayout(bottom_row)

        self._refresh_list()

    def _refresh_list(self, selected_idx: int = 0) -> None:
        self._list_widget.clear()
        presets = get_edit_presets()
        for p in presets:
            item = QListWidgetItem(f"{p['name']}\n➔ {p['prompt'][:60]}...")
            item.setData(Qt.ItemDataRole.UserRole, p)
            self._list_widget.addItem(item)

        if 0 <= selected_idx < self._list_widget.count():
            self._list_widget.setCurrentRow(selected_idx)

    def _on_add_new(self) -> None:
        dlg = AddPresetDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_list(selected_idx=self._list_widget.count())

    def _on_move_up(self) -> None:
        row = self._list_widget.currentRow()
        if row > 0:
            move_edit_preset(row, row - 1)
            self._refresh_list(selected_idx=row - 1)

    def _on_move_down(self) -> None:
        row = self._list_widget.currentRow()
        if 0 <= row < self._list_widget.count() - 1:
            move_edit_preset(row, row + 1)
            self._refresh_list(selected_idx=row + 1)

    def _on_delete(self) -> None:
        row = self._list_widget.currentRow()
        if row < 0:
            QMessageBox.information(self, "Bilgi", "Lütfen silmek istediğiniz şablonu seçin.")
            return

        presets = get_edit_presets()
        preset_name = presets[row]["name"] if 0 <= row < len(presets) else "Bu şablon"

        reply = QMessageBox.question(
            self,
            "Şablonu Sil",
            f"'{preset_name}' şablonunu silmek istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_edit_preset(row)
            self._refresh_list(selected_idx=max(0, row - 1))
