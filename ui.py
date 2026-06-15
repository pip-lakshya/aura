"""PyQt6 Iron Man HUD interface for AURA."""

from __future__ import annotations

import math
import sys
from datetime import datetime

from PyQt6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


BG_COLOR = "#0a0a0f"
ACCENT = "#00d4ff"
SECONDARY = "#0066ff"
PANEL_BG = "rgba(4, 18, 34, 170)"
FONT_FAMILY = "Courier New"


class HudCharacter(QWidget):
    """Animated AURA character drawn with QPainter."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = "idle"
        self.phase = 0.0
        self.setMinimumSize(340, 360)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(30)

    def set_idle(self) -> None:
        self.state = "idle"

    def set_listening(self) -> None:
        self.state = "listening"

    def set_speaking(self) -> None:
        self.state = "speaking"

    def _tick(self) -> None:
        speed = {"idle": 0.035, "listening": 0.13, "speaking": 0.08}.get(
            self.state, 0.04
        )
        self.phase = (self.phase + speed) % (math.pi * 2)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

        width = self.width()
        height = self.height()
        center = QPointF(width / 2, height * 0.42)
        base_radius = min(width, height) * 0.22

        self._draw_rings(painter, center, base_radius)
        self._draw_orb(painter, center, base_radius * 0.42)
        self._draw_waveform(painter, width, height)

    def _draw_rings(self, painter: QPainter, center: QPointF, radius: float) -> None:
        pulse = (math.sin(self.phase) + 1) / 2
        expansion = pulse * (18 if self.state == "listening" else 8)

        for index in range(4):
            ring_radius = radius + index * 24 + expansion
            alpha = max(35, 180 - index * 35)
            pen = QPen(QColor(0, 212, 255, alpha), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, ring_radius, ring_radius)

        arc_pen = QPen(QColor(0, 102, 255, 210), 4)
        painter.setPen(arc_pen)
        rect = QRectF(
            center.x() - radius - 58,
            center.y() - radius - 58,
            (radius + 58) * 2,
            (radius + 58) * 2,
        )
        start = int((self.phase * 180 / math.pi) * 16)
        painter.drawArc(rect, start, 115 * 16)
        painter.drawArc(rect, start + 180 * 16, 70 * 16)

    def _draw_orb(self, painter: QPainter, center: QPointF, radius: float) -> None:
        pulse = (math.sin(self.phase * 1.5) + 1) / 2
        orb_radius = radius + pulse * 8
        glow_radius = orb_radius * 2.8

        glow = QLinearGradient(
            QPointF(center.x(), center.y() - glow_radius),
            QPointF(center.x(), center.y() + glow_radius),
        )
        glow.setColorAt(0.0, QColor(0, 212, 255, 12))
        glow.setColorAt(0.5, QColor(0, 212, 255, 90))
        glow.setColorAt(1.0, QColor(0, 102, 255, 20))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(center, glow_radius, glow_radius)

        painter.setBrush(QColor(0, 212, 255, 220))
        painter.drawEllipse(center, orb_radius, orb_radius)
        painter.setBrush(QColor(230, 252, 255, 240))
        painter.drawEllipse(center, orb_radius * 0.38, orb_radius * 0.38)

    def _draw_waveform(self, painter: QPainter, width: int, height: int) -> None:
        baseline = height - 55
        bar_count = 34
        bar_width = 5
        gap = 5
        total_width = bar_count * bar_width + (bar_count - 1) * gap
        start_x = (width - total_width) / 2

        for index in range(bar_count):
            if self.state == "speaking":
                amplitude = 12 + 34 * abs(math.sin(self.phase * 2 + index * 0.45))
            elif self.state == "listening":
                amplitude = 10 + 18 * abs(math.sin(self.phase + index * 0.25))
            else:
                amplitude = 8 + 6 * abs(math.sin(self.phase + index * 0.18))

            x = start_x + index * (bar_width + gap)
            y = baseline - amplitude / 2
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 212, 255, 170))
            painter.drawRoundedRect(QRectF(x, y, bar_width, amplitude), 2, 2)


class MessageBubble(QWidget):
    def __init__(self, sender: str, text: str, timestamp: str, parent=None) -> None:
        super().__init__(parent)
        self.sender = sender.upper()
        self.text = text
        self.timestamp = timestamp
        self.is_user = self.sender == "USER"
        self.setMinimumHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def sizeHint(self) -> QSize:
        line_count = max(1, len(self.text) // 52 + 1)
        return QSize(460, 58 + line_count * 18)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        margin = 10
        bubble_width = int(self.width() * 0.76)
        x = self.width() - bubble_width - margin if self.is_user else margin
        rect = QRectF(x, margin, bubble_width, self.height() - margin * 2)

        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        painter.setPen(QPen(QColor(0, 212, 255, 210), 1.4))
        painter.setBrush(
            QColor(0, 30, 50, 190) if self.is_user else QColor(0, 28, 85, 180)
        )
        painter.drawPath(path)

        painter.setFont(QFont(FONT_FAMILY, 8))
        painter.setPen(QColor(120, 230, 255, 180))
        meta = f"{self.sender}  {self.timestamp}"
        painter.drawText(
            QRectF(rect.x() + 12, rect.y() + 8, rect.width() - 24, 16),
            Qt.AlignmentFlag.AlignLeft,
            meta,
        )

        painter.setFont(QFont(FONT_FAMILY, 10))
        painter.setPen(QColor(235, 252, 255))
        painter.drawText(
            QRectF(rect.x() + 12, rect.y() + 28, rect.width() - 24, rect.height() - 36),
            Qt.TextFlag.TextWordWrap,
            self.text,
        )


class ScanlineOverlay(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setPen(QPen(QColor(0, 212, 255, 24), 1))
        for y in range(0, self.height(), 8):
            painter.drawLine(0, y, self.width(), y)
        painter.setPen(QPen(QColor(0, 102, 255, 18), 1))
        for x in range(0, self.width(), 40):
            painter.drawLine(x, 0, x, self.height())


class AuraWindow(QMainWindow):
    message_submitted = pyqtSignal(str)
    mic_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.drag_position = QPoint()
        self.status = "IDLE"

        self.setWindowTitle("AURA")
        self.resize(900, 600)
        self.setMinimumSize(900, 600)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.root = QWidget()
        self.root.setObjectName("root")
        self.setCentralWidget(self.root)

        self.overlay = ScanlineOverlay(self.root)

        self._build_ui()
        self._apply_styles()
        self.set_status("IDLE")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.overlay.setGeometry(self.root.rect())

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)


    def toggle_maximize_restore(self) -> None:
        if self.isMaximized():
            self.showNormal()
            self.max_button.setText("□")
        else:
            self.showMaximized()
            self.max_button.setText("❐")
    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self.root)
        main_layout.setContentsMargins(16, 14, 16, 16)
        main_layout.setSpacing(12)

        top_bar = QHBoxLayout()
        logo_block = QVBoxLayout()
        self.logo = QLabel("AURA")
        self.logo.setObjectName("logoLabel")
        self.subtitle = QLabel("ADAPTIVE UNIFIED RETRIEVAL ASSISTANT")
        logo_block.addWidget(self.logo)
        logo_block.addWidget(self.subtitle)

        top_bar.addLayout(logo_block)
        top_bar.addStretch(1)
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(14, 14)
        top_bar.addWidget(self.status_dot)
        main_layout.addLayout(top_bar)
        self.min_button = QPushButton("-")
        self.max_button = QPushButton("□")
        self.close_button = QPushButton("X")

        self.min_button.setFixedSize(34, 28)
        self.max_button.setFixedSize(34, 28)
        self.close_button.setFixedSize(34, 28)

        self.min_button.clicked.connect(self.showMinimized)
        self.max_button.clicked.connect(self.toggle_maximize_restore)
        self.close_button.clicked.connect(self.close)

        top_bar.addWidget(self.min_button)
        top_bar.addWidget(self.max_button)
        top_bar.addWidget(self.close_button)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(14)
        main_layout.addLayout(content_layout, 1)

        left_panel = self._panel()
        left_panel.setMinimumWidth(360)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(18, 18, 18, 18)
        left_layout.setSpacing(12)

        self.hud = HudCharacter()
        self.status_label = QLabel("IDLE")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.hud, 1)
        left_layout.addWidget(self.status_label)
        content_layout.addWidget(left_panel)

        right_panel = self._panel()
        right_panel.setMinimumWidth(500)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(10)

        self.chat = QListWidget()
        self.chat.setSpacing(8)
        self.chat.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_layout.addWidget(self.chat, 1)

        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Transmit memory or query...")
        self.input.returnPressed.connect(self._send_from_input)
        self.mic_button = QPushButton("MIC")
        self.mic_button.clicked.connect(self.mic_requested.emit)
        self.stop_button = QPushButton("STOP")
        self.stop_button.clicked.connect(self.stop_requested.emit)
        self.send_button = QPushButton("SEND")
        self.send_button.clicked.connect(self._send_from_input)
        input_row.addWidget(self.input, 1)
        input_row.addWidget(self.mic_button)
        input_row.addWidget(self.stop_button)
        input_row.addWidget(self.send_button)
        right_layout.addLayout(input_row)

        content_layout.addWidget(right_panel)

    def _panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("hudPanel")
        shadow = QGraphicsDropShadowEffect(panel)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(0, 212, 255, 150))
        panel.setGraphicsEffect(shadow)
        return panel

    def _apply_styles(self) -> None:
        self.root.setStyleSheet(
            f"""
            QWidget#root {{
                background: {BG_COLOR};
                color: #e8fbff;
                font-family: "{FONT_FAMILY}", monospace;
            }}
            QLabel {{
                color: #e8fbff;
                font-family: "{FONT_FAMILY}", monospace;
            }}
            QLabel#logoLabel {{
                color: {ACCENT};
            }}
            QFrame#hudPanel {{
                background: {PANEL_BG};
                border: 1px solid rgba(0, 212, 255, 190);
                border-radius: 8px;
            }}
            QListWidget {{
                background: rgba(0, 0, 0, 70);
                border: 1px solid rgba(0, 212, 255, 130);
                border-radius: 8px;
                outline: none;
            }}
            QListWidget::item {{
                border: none;
                background: transparent;
            }}
            QLineEdit {{
                background: rgba(0, 0, 0, 150);
                border: 1px solid rgba(0, 212, 255, 150);
                border-radius: 6px;
                color: #e8fbff;
                padding: 10px;
                selection-background-color: {SECONDARY};
            }}
            QLineEdit:focus {{
                border: 1px solid {ACCENT};
            }}
            QPushButton {{
                background: rgba(0, 90, 130, 180);
                border: 1px solid {ACCENT};
                border-radius: 6px;
                color: #e8fbff;
                font-weight: bold;
                padding: 10px 14px;
            }}
            QPushButton:hover {{
                background: rgba(0, 160, 210, 210);
            }}
            QScrollBar:vertical {{
                background: rgba(0, 0, 0, 80);
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(0, 212, 255, 170);
                border-radius: 4px;
            }}
            """
        )
        self.logo.setFont(QFont(FONT_FAMILY, 26, QFont.Weight.Bold))
        self.subtitle.setFont(QFont(FONT_FAMILY, 9))
        self.subtitle.setStyleSheet("color: rgba(190, 242, 255, 190);")
        self.status_label.setFont(QFont(FONT_FAMILY, 16, QFont.Weight.Bold))
        self.status_label.setStyleSheet(f"color: {ACCENT};")

    def _send_from_input(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.message_submitted.emit(text)

    def add_message(self, sender: str, text: str) -> None:
        timestamp = datetime.now().strftime("%H:%M")
        bubble = MessageBubble(sender, text, timestamp)
        item = QListWidgetItem()
        item.setSizeHint(bubble.sizeHint())
        self.chat.addItem(item)
        self.chat.setItemWidget(item, bubble)
        self.chat.scrollToBottom()

    def set_input_text(self, text: str) -> None:
        self.input.setText(text)
        self.input.setCursorPosition(len(text))
        self.input.setFocus()

    def set_status(self, status: str) -> None:
        normalized = status.strip().upper()
        self.status = normalized
        self.status_label.setText(normalized)

        if normalized.startswith("LISTEN") or normalized.startswith("TRANSCRIB"):
            color = "#f5d742"
            self.hud.set_listening()
        elif normalized.startswith("SPEAK"):
            color = "#ff3b30"
            self.hud.set_speaking()
        else:
            color = "#2dff73"
            self.hud.set_idle()

        self.status_dot.setStyleSheet(
            f"background: {color}; border: 1px solid #dff; border-radius: 7px;"
        )


def main() -> int:
    app = QApplication(sys.argv)
    window = AuraWindow()
    window.add_message("AURA", "Systems online. I am ready.")
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
