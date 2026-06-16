"""PyQt6 Iron Man HUD interface for AURA."""

from __future__ import annotations

import math
import sys
import random
from datetime import datetime
from typing import Any

try:
    import ctypes
    from ctypes.wintypes import MSG
except ImportError:
    ctypes = None
    MSG = None

from PyQt6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QCursor,
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
from PyQt6.QtGui import QIcon
import os
import sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

BG_COLOR = "#0a0a0f"
ACCENT = "#00d4ff"
SECONDARY = "#0066ff"
PANEL_BG = "rgba(4, 18, 34, 170)"
FONT_FAMILY = "Courier New"


class HudCharacter(QWidget):
    """Animated AURA robot character drawn with QPainter."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = "idle"
        self.phase = 0.0
        self.blink_ratio = 1.0
        self.blink_timer = 0
        self.speaker_level = 0.0
        self.mic_level = 0.0
        self.setMinimumSize(320, 340)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(30)

    def set_idle(self) -> None:
        self.state = "idle"

    def set_listening(self) -> None:
        self.state = "listening"

    def set_thinking(self) -> None:
        self.state = "thinking"

    def set_speaking(self) -> None:
        self.state = "speaking"

    def _tick(self) -> None:
        speed = {"idle": 0.035, "listening": 0.1, "thinking": 0.18, "speaking": 0.08}.get(
            self.state, 0.04
        )
        self.phase = (self.phase + speed) % (math.pi * 2)

        # Blinking logic
        self.blink_timer += 1
        if self.blink_timer % 140 == 0:
            self.blink_ratio = 0.1
        elif self.blink_ratio == 0.1:
            self.blink_ratio = 1.0

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
        self._draw_robot(painter, center, base_radius * 0.6)
        self._draw_waveform(painter, width, height)

    def _draw_rings(self, painter: QPainter, center: QPointF, radius: float) -> None:
        pulse = (math.sin(self.phase) + 1) / 2
        expansion = pulse * (18 if self.state == "listening" else 8)

        for index in range(4):
            ring_radius = radius + index * 24 + expansion
            alpha = max(30, 160 - index * 30)
            pen = QPen(QColor(0, 212, 255, alpha), 1.5)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, ring_radius, ring_radius)

        arc_pen = QPen(QColor(0, 102, 255, 180), 3)
        painter.setPen(arc_pen)
        rect = QRectF(
            center.x() - radius - 48,
            center.y() - radius - 48,
            (radius + 48) * 2,
            (radius + 48) * 2,
        )
        start = int((self.phase * 180 / math.pi) * 16)
        painter.drawArc(rect, start, 115 * 16)
        painter.drawArc(rect, start + 180 * 16, 70 * 16)

    def _draw_robot(self, painter: QPainter, center: QPointF, radius: float) -> None:
        # Gentle floating bobbing effect
        bob = math.sin(self.phase) * 6.0
        head_center = QPointF(center.x(), center.y() + bob)

        # 1. Antennas
        painter.setPen(QPen(QColor(0, 212, 255, 180), 2))
        painter.drawLine(head_center + QPointF(-25, -35), head_center + QPointF(-35, -55))
        painter.drawLine(head_center + QPointF(25, -35), head_center + QPointF(35, -55))

        # Antenna glow tips
        pulse = (math.sin(self.phase * 2.5) + 1) / 2
        light_color = QColor(255, 60, 60) if self.state == "speaking" else QColor(0, 212, 255)
        alpha = int(120 + pulse * 135)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(light_color.red(), light_color.green(), light_color.blue(), alpha))
        painter.drawEllipse(head_center + QPointF(-35, -55), 6, 6)
        painter.drawEllipse(head_center + QPointF(35, -55), 6, 6)

        # 2. Ear bolts
        painter.setBrush(QColor("#101b2b"))
        painter.setPen(QPen(QColor(0, 212, 255, 200), 1.6))
        painter.drawRoundedRect(QRectF(head_center.x() - 56, head_center.y() - 15, 6, 30), 2, 2)
        painter.drawRoundedRect(QRectF(head_center.x() + 50, head_center.y() - 15, 6, 30), 2, 2)

        # 3. Outer Head Plate
        head_rect = QRectF(head_center.x() - 50, head_center.y() - 40, 100, 80)
        head_grad = QLinearGradient(head_rect.topLeft(), head_rect.bottomRight())
        head_grad.setColorAt(0.0, QColor("#14223d"))
        head_grad.setColorAt(1.0, QColor("#081021"))
        painter.setBrush(head_grad)
        painter.setPen(QPen(QColor(0, 212, 255, 220), 2.2))
        painter.drawRoundedRect(head_rect, 22, 22)

        # 4. Glossy Dark Glass Screen
        screen_rect = QRectF(head_center.x() - 42, head_center.y() - 32, 84, 64)
        screen_grad = QLinearGradient(screen_rect.topLeft(), screen_rect.bottomRight())
        screen_grad.setColorAt(0.0, QColor(4, 10, 26, 250))
        screen_grad.setColorAt(1.0, QColor(1, 2, 8, 250))
        painter.setBrush(screen_grad)
        painter.setPen(QPen(QColor(0, 102, 255, 100), 1.0))
        painter.drawRoundedRect(screen_rect, 14, 14)

        # 5. Glowing Digital Eyes
        eye_y = head_center.y() - 4
        left_eye_x = head_center.x() - 20
        right_eye_x = head_center.x() + 20

        eye_color = QColor(0, 212, 255, 240)
        if self.state == "listening":
            eye_color = QColor(0, 255, 120, 240)
        elif self.state == "speaking":
            eye_color = QColor(0, 212, 255, 240)

        painter.setBrush(eye_color)
        painter.setPen(Qt.PenStyle.NoPen)

        eye_height = 20.0 * self.blink_ratio
        eye_width = 12.0

        if self.state == "thinking":
            # Spinning loading arcs for eyes
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor("#00d4ff"), 2.2))
            start_angle = int((self.phase * 180 / math.pi) * 16)
            painter.drawArc(QRectF(left_eye_x - 9, eye_y - 9, 18, 18), start_angle, 120 * 16)
            painter.drawArc(QRectF(left_eye_x - 9, eye_y - 9, 18, 18), start_angle + 180 * 16, 120 * 16)
            painter.drawArc(QRectF(right_eye_x - 9, eye_y - 9, 18, 18), -start_angle, 120 * 16)
            painter.drawArc(QRectF(right_eye_x - 9, eye_y - 9, 18, 18), -start_angle + 180 * 16, 120 * 16)
        elif self.state == "listening":
            # Widened circular eyes reactive to microphone input volume
            ew = eye_width + self.mic_level * 10
            eh = (20.0 + self.mic_level * 8) * self.blink_ratio
            painter.drawEllipse(QPointF(left_eye_x, eye_y), ew/2, eh/2)
            painter.drawEllipse(QPointF(right_eye_x, eye_y), ew/2, eh/2)
        else:
            # Normal oval eyes
            painter.drawEllipse(QRectF(left_eye_x - eye_width/2, eye_y - eye_height/2, eye_width, eye_height))
            painter.drawEllipse(QRectF(right_eye_x - eye_width/2, eye_y - eye_height/2, eye_width, eye_height))

        # 6. Mouth waveform inside screen
        mouth_y = head_center.y() + 16
        painter.setPen(QPen(QColor(0, 212, 255, 220), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if self.state == "speaking":
            # Waveform animated by speaker volume levels
            mouth_path = QPainterPath()
            mouth_path.moveTo(head_center.x() - 16, mouth_y)
            h1 = math.sin(self.phase * 6) * (self.speaker_level * 22.0)
            h2 = math.cos(self.phase * 5) * (self.speaker_level * 16.0)
            mouth_path.cubicTo(
                head_center.x() - 8, mouth_y + h1,
                head_center.x() + 8, mouth_y + h2,
                head_center.x() + 16, mouth_y
            )
            painter.drawPath(mouth_path)
        elif self.state == "listening":
            # Pulsing microphone listening line
            ml = 4 + int(self.mic_level * 16)
            painter.drawLine(QPointF(head_center.x() - ml, mouth_y), QPointF(head_center.x() + ml, mouth_y))
        else:
            # Gentle smile
            mouth_path = QPainterPath()
            mouth_path.moveTo(head_center.x() - 8, mouth_y - 1)
            mouth_path.quadTo(head_center.x(), mouth_y + 3, head_center.x() + 8, mouth_y - 1)
            painter.drawPath(mouth_path)

    def _draw_waveform(self, painter: QPainter, width: int, height: int) -> None:
        baseline = height - 45
        bar_count = 30
        bar_width = 4
        gap = 4
        total_width = bar_count * bar_width + (bar_count - 1) * gap
        start_x = (width - total_width) / 2

        for index in range(bar_count):
            if self.state == "speaking":
                amplitude = 12 + 40 * abs(math.sin(self.phase * 2.2 + index * 0.4)) * self.speaker_level
            elif self.state == "listening":
                amplitude = 8 + 24 * abs(math.sin(self.phase * 1.5 + index * 0.2)) * self.mic_level
            else:
                amplitude = 6 + 4 * abs(math.sin(self.phase + index * 0.15))

            x = start_x + index * (bar_width + gap)
            y = baseline - amplitude / 2
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 212, 255, 160))
            painter.drawRoundedRect(QRectF(x, y, bar_width, amplitude), 1.5, 1.5)


class KnowledgeGraphWidget(QWidget):
    """Interactive Force-Directed Cognitive Personality Knowledge Graph."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[tuple[str, str, str]] = []
        self.dragged_node: str | None = None
        self.hovered_node: str | None = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._simulation_tick)
        self.timer.start(30)

        self.setMinimumWidth(360)
        self.setMouseTracking(True)

    def set_triples(self, triples: list[dict[str, str]]) -> None:
        new_nodes: dict[str, dict[str, Any]] = {}
        new_edges = []

        for t in triples:
            src = str(t.get("source", "")).strip()
            rel = str(t.get("relation", "")).strip()
            tgt = str(t.get("target", "")).strip()
            if not src or not tgt:
                continue
            new_edges.append((src, rel, tgt))

            for name in (src, tgt):
                if name not in new_nodes:
                    if name in self.nodes:
                        new_nodes[name] = self.nodes[name]
                    else:
                        cx = self.width() / 2 if self.width() > 0 else 180
                        cy = self.height() / 2 if self.height() > 0 else 300
                        rx = cx + random.uniform(-60, 60)
                        ry = cy + random.uniform(-60, 60)
                        new_nodes[name] = {
                            "pos": QPointF(rx, ry),
                            "vel": QPointF(0.0, 0.0),
                            "is_boss": (name.lower() in ("you", "boss")),
                        }
        self.nodes = new_nodes
        self.edges = new_edges
        self.update()

    def _simulation_tick(self) -> None:
        if not self.nodes:
            return

        dt = 0.45
        damping = 0.82
        kr = 14000.0  # Repulsion
        ks = 0.09    # Spring tension
        L0 = 110.0   # Rest length
        kg = 0.024   # Center gravity

        cx = self.width() / 2
        cy = self.height() / 2
        center = QPointF(cx, cy)

        # 1. Node Repulsion
        names = list(self.nodes.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                n1 = names[i]
                n2 = names[j]
                p1 = self.nodes[n1]["pos"]
                p2 = self.nodes[n2]["pos"]
                dx = p1.x() - p2.x()
                dy = p1.y() - p2.y()
                dist_sq = dx * dx + dy * dy
                if dist_sq < 120:
                    dist_sq = 120.0
                dist = math.sqrt(dist_sq)

                fx = (dx / dist) * (kr / dist_sq)
                fy = (dy / dist) * (kr / dist_sq)

                if n1 != self.dragged_node:
                    self.nodes[n1]["vel"] = QPointF(self.nodes[n1]["vel"].x() + fx, self.nodes[n1]["vel"].y() + fy)
                if n2 != self.dragged_node:
                    self.nodes[n2]["vel"] = QPointF(self.nodes[n2]["vel"].x() - fx, self.nodes[n2]["vel"].y() - fy)

        # 2. Edge springs pulling nodes
        for src, rel, tgt in self.edges:
            if src not in self.nodes or tgt not in self.nodes:
                continue
            p1 = self.nodes[src]["pos"]
            p2 = self.nodes[tgt]["pos"]
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < 1.0:
                dist = 1.0

            force = ks * (dist - L0)
            fx = (dx / dist) * force
            fy = (dy / dist) * force

            if src != self.dragged_node:
                self.nodes[src]["vel"] = QPointF(self.nodes[src]["vel"].x() + fx, self.nodes[src]["vel"].y() + fy)
            if tgt != self.dragged_node:
                self.nodes[tgt]["vel"] = QPointF(self.nodes[tgt]["vel"].x() - fx, self.nodes[tgt]["vel"].y() - fy)

        # 3. Apply Gravity and update positions
        for name, data in self.nodes.items():
            if name == self.dragged_node:
                continue
            p = data["pos"]
            g_fx = (center.x() - p.x()) * kg
            g_fy = (center.y() - p.y()) * kg

            vel = data["vel"]
            new_vx = (vel.x() + g_fx) * damping
            new_vy = (vel.y() + g_fy) * damping

            data["vel"] = QPointF(new_vx, new_vy)

            speed = math.sqrt(new_vx * new_vx + new_vy * new_vy)
            if speed > 22.0:
                new_vx = (new_vx / speed) * 22.0
                new_vy = (new_vy / speed) * 22.0

            new_x = p.x() + new_vx * dt
            new_y = p.y() + new_vy * dt

            # Constrain inside widget
            new_x = max(35, min(self.width() - 35, new_x))
            new_y = max(35, min(self.height() - 35, new_y))

            data["pos"] = QPointF(new_x, new_y)

        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            for name, data in self.nodes.items():
                p = data["pos"]
                dx = pos.x() - p.x()
                dy = pos.y() - p.y()
                if dx * dx + dy * dy <= 480:  # Radius match
                    self.dragged_node = name
                    break

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()
        if self.dragged_node:
            self.nodes[self.dragged_node]["pos"] = QPointF(
                max(30, min(self.width() - 30, pos.x())),
                max(30, min(self.height() - 30, pos.y()))
            )
            self.update()
            return

        self.hovered_node = None
        for name, data in self.nodes.items():
            p = data["pos"]
            dx = pos.x() - p.x()
            dy = pos.y() - p.y()
            if dx * dx + dy * dy <= 480:
                self.hovered_node = name
                break
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        self.dragged_node = None

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Panel title
        painter.setFont(QFont(FONT_FAMILY, 9, QFont.Weight.Bold))
        painter.setPen(QColor("#00d4ff"))
        painter.drawText(
            self.rect().adjusted(15, 15, -15, -15),
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
            "COGNITIVE PERSONALITY GRAPH"
        )

        # 1. Draw connections
        for src, rel, tgt in self.edges:
            if src not in self.nodes or tgt not in self.nodes:
                continue
            p1 = self.nodes[src]["pos"]
            p2 = self.nodes[tgt]["pos"]

            is_active = (src == self.hovered_node or tgt == self.hovered_node)
            color = QColor(0, 212, 255, 230 if is_active else 80)
            pen_width = 1.8 if is_active else 1.0
            painter.setPen(QPen(color, pen_width, Qt.PenStyle.SolidLine if is_active else Qt.PenStyle.DashLine))
            painter.drawLine(p1, p2)

            # Draw relation badge text in middle
            mid_x = (p1.x() + p2.x()) / 2
            mid_y = (p1.y() + p2.y()) / 2
            painter.setFont(QFont(FONT_FAMILY, 7))
            painter.setPen(QColor(120, 230, 255, 210 if is_active else 120))
            text_rect = QRectF(mid_x - 45, mid_y - 7, 90, 14)
            painter.fillRect(text_rect, QColor(10, 15, 28, 220))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, rel)

        # 2. Draw nodes
        for name, data in self.nodes.items():
            pos = data["pos"]
            is_boss = data["is_boss"]
            is_hovered = (name == self.hovered_node or name == self.dragged_node)

            radius = 28 if is_boss else 22
            if is_hovered:
                radius += 3

            glow = QLinearGradient(QPointF(pos.x() - radius, pos.y() - radius), QPointF(pos.x() + radius, pos.y() + radius))
            if is_boss:
                glow.setColorAt(0.0, QColor(255, 60, 60, 170 if is_hovered else 120))
                glow.setColorAt(1.0, QColor(200, 20, 20, 95 if is_hovered else 45))
                border_color = QColor("#ff3b30")
            else:
                glow.setColorAt(0.0, QColor(0, 212, 255, 170 if is_hovered else 120))
                glow.setColorAt(1.0, QColor(0, 102, 255, 95 if is_hovered else 45))
                border_color = QColor("#00d4ff")

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow)
            painter.drawEllipse(pos, radius, radius)

            # Outer ring stroke
            painter.setPen(QPen(border_color, 2.0 if is_hovered else 1.2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(pos, radius, radius)

            # Node label text
            painter.setPen(QColor(240, 253, 255))
            painter.setFont(QFont(FONT_FAMILY, 7 if len(name) > 8 else 8, QFont.Weight.Bold if is_boss else QFont.Weight.Normal))
            rect = QRectF(pos.x() - radius - 4, pos.y() - radius, (radius + 4) * 2, radius * 2)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, name)


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
        line_count = max(1, len(self.text) // 46 + 1)
        return QSize(400, 58 + line_count * 18)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        margin = 10
        bubble_width = int(self.width() * 0.8)
        x = self.width() - bubble_width - margin if self.is_user else margin
        rect = QRectF(x, margin, bubble_width, self.height() - margin * 2)

        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        painter.setPen(QPen(QColor(0, 212, 255, 180), 1.2))
        painter.setBrush(
            QColor(0, 30, 50, 180) if self.is_user else QColor(0, 24, 75, 170)
        )
        painter.drawPath(path)

        painter.setFont(QFont(FONT_FAMILY, 8))
        painter.setPen(QColor(120, 230, 255, 160))
        meta = f"{self.sender}  {self.timestamp}"
        painter.drawText(
            QRectF(rect.x() + 12, rect.y() + 8, rect.width() - 24, 16),
            Qt.AlignmentFlag.AlignLeft,
            meta,
        )

        painter.setFont(QFont(FONT_FAMILY, 9))
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
        painter.setPen(QPen(QColor(0, 212, 255, 20), 1))
        for y in range(0, self.height(), 8):
            painter.drawLine(0, y, self.width(), y)
        painter.setPen(QPen(QColor(0, 102, 255, 14), 1))
        for x in range(0, self.width(), 40):
            painter.drawLine(x, 0, x, self.height())


class AuraWindow(QMainWindow):
    message_submitted = pyqtSignal(str)
    mic_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.status = "IDLE"
        self.resize_margin = 8

        self.setWindowTitle("AURA")
        self.setWindowIcon(QIcon(resource_path("assets/logo.png")))
        self.resize(1200, 700)
        self.setMinimumSize(1200, 700)
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

    def nativeEvent(self, eventType, message) -> tuple[bool, int]:
        try:
            if ctypes is not None and eventType == b"windows_generic_MSG":
                msg = MSG.from_address(int(message))
                if msg.message == 0x0084:  # WM_NCHITTEST
                    # Use QCursor.pos() for DPI-aware logical coordinates
                    global_pos = QCursor.pos()
                    local_pos = self.mapFromGlobal(global_pos)
                    lx = local_pos.x()
                    ly = local_pos.y()
                    
                    margin = self.resize_margin
                    w = self.width()
                    h = self.height()
                    
                    # Check corners
                    if not self.isMaximized():
                        if lx < margin and ly < margin:
                            return True, 13  # HTTOPLEFT
                        elif lx > w - margin and ly < margin:
                            return True, 14  # HTTOPRIGHT
                        elif lx < margin and ly > h - margin:
                            return True, 16  # HTBOTTOMLEFT
                        elif lx > w - margin and ly > h - margin:
                            return True, 17  # HTBOTTOMRIGHT
                        # Check edges
                        elif lx < margin:
                            return True, 10  # HTLEFT
                        elif lx > w - margin:
                            return True, 11  # HTRIGHT
                        elif ly < margin:
                            return True, 12  # HTTOP
                        elif ly > h - margin:
                            return True, 15  # HTBOTTOM
                    
                    # Check title bar area
                    if ly < 60:
                        if (hasattr(self, "min_button") and hasattr(self, "max_button") and hasattr(self, "close_button") and
                            (self.min_button.geometry().contains(local_pos) or
                             self.max_button.geometry().contains(local_pos) or
                             self.close_button.geometry().contains(local_pos))):
                            return False, 0  # Let Qt process clicks on window buttons
                        return True, 2  # HTCAPTION (Title bar dragging)
        except Exception as e:
            print("ERROR IN NATIVE EVENT:", e)
                    
        return False, 0

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

        # 1. Left Panel (Robot/Voice Monitor)
        left_panel = self._panel()
        left_panel.setMinimumWidth(330)
        left_panel.setMaximumWidth(360)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(10)

        self.hud = HudCharacter()
        
        # Caption label - replaces the old IDLE status label
        self.caption_label = QLabel("Systems online. Standing by.")
        self.caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption_label.setWordWrap(True)
        self.caption_label.setMinimumHeight(48)
        self.caption_label.setStyleSheet("color: #78e6ff; font-size: 11px;")
        
        # Dynamic Meters and Controls Layout
        control_row = QHBoxLayout()
        control_row.setSpacing(8)
        
        # Mic Level Progress bar (visual style)
        mic_box = QVBoxLayout()
        mic_title = QLabel("MIC IN")
        mic_title.setFont(QFont(FONT_FAMILY, 7, QFont.Weight.Bold))
        mic_title.setStyleSheet("color: rgba(0, 212, 255, 180);")
        self.mic_bar = QFrame()
        self.mic_bar.setFrameShape(QFrame.Shape.Box)
        self.mic_bar.setFixedHeight(8)
        self.mic_bar.setStyleSheet("background-color: #031424; border: 1px solid #00d4ff; border-radius: 2px;")
        self.mic_level_inner = QFrame(self.mic_bar)
        self.mic_level_inner.setStyleSheet("background-color: #00ff7b;")
        self.mic_level_inner.setGeometry(0, 0, 0, 8)
        mic_box.addWidget(mic_title)
        mic_box.addWidget(self.mic_bar)
        control_row.addLayout(mic_box, 1)

        # Speaker Level Progress bar (visual style)
        spk_box = QVBoxLayout()
        spk_title = QLabel("SYS OUT")
        spk_title.setFont(QFont(FONT_FAMILY, 7, QFont.Weight.Bold))
        spk_title.setStyleSheet("color: rgba(0, 212, 255, 180);")
        self.spk_bar = QFrame()
        self.spk_bar.setFrameShape(QFrame.Shape.Box)
        self.spk_bar.setFixedHeight(8)
        self.spk_bar.setStyleSheet("background-color: #031424; border: 1px solid #00d4ff; border-radius: 2px;")
        self.spk_level_inner = QFrame(self.spk_bar)
        self.spk_level_inner.setStyleSheet("background-color: #ff3b30;")
        self.spk_level_inner.setGeometry(0, 0, 0, 8)
        spk_box.addWidget(spk_title)
        spk_box.addWidget(self.spk_bar)
        control_row.addLayout(spk_box, 1)

        # Mute push button (toggle checkable style)
        self.mute_button = QPushButton("MUTE")
        self.mute_button.setCheckable(True)
        self.mute_button.setFixedSize(54, 24)
        self.mute_button.setStyleSheet(
            """
            QPushButton {
                background: rgba(0, 90, 130, 80);
                border: 1px solid #00d4ff;
                border-radius: 4px;
                color: #e8fbff;
                font-size: 9px;
                padding: 0;
            }
            QPushButton:hover {
                background: rgba(0, 160, 210, 120);
            }
            QPushButton:checked {
                background: rgba(255, 60, 60, 120);
                border: 1px solid #ff3b30;
                color: #ffffff;
            }
            """
        )
        self.mute_button.clicked.connect(self._toggle_mute)
        control_row.addWidget(self.mute_button)

        left_layout.addWidget(self.hud, 1)
        left_layout.addWidget(self.caption_label)
        left_layout.addLayout(control_row)
        content_layout.addWidget(left_panel)

        # 2. Middle Panel (Chat Log Panel)
        middle_panel = self._panel()
        middle_panel.setMinimumWidth(440)
        middle_layout = QVBoxLayout(middle_panel)
        middle_layout.setContentsMargins(14, 14, 14, 14)
        middle_layout.setSpacing(10)

        self.chat = QListWidget()
        self.chat.setSpacing(8)
        self.chat.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        middle_layout.addWidget(self.chat, 1)

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
        middle_layout.addLayout(input_row)
        content_layout.addWidget(middle_panel)

        # 3. Right Panel (Holographic Graph Panel)
        right_panel = self._panel()
        right_panel.setMinimumWidth(400)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        self.graph_widget = KnowledgeGraphWidget()
        right_layout.addWidget(self.graph_widget)
        content_layout.addWidget(right_panel)

    def _panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("hudPanel")
        shadow = QGraphicsDropShadowEffect(panel)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(0, 212, 255, 120))
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
                border: 1px solid rgba(0, 212, 255, 150);
                border-radius: 8px;
            }}
            QListWidget {{
                background: rgba(0, 0, 0, 70);
                border: 1px solid rgba(0, 212, 255, 110);
                border-radius: 8px;
                outline: none;
            }}
            QListWidget::item {{
                border: none;
                background: transparent;
            }}
            QLineEdit {{
                background: rgba(0, 0, 0, 150);
                border: 1px solid rgba(0, 212, 255, 130);
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

    def is_muted(self) -> bool:
        return self.mute_button.isChecked()

    def _toggle_mute(self) -> None:
        is_muted = self.mute_button.isChecked()
        if is_muted:
            self.mute_button.setText("MUTED")
            self.stop_requested.emit()
        else:
            self.mute_button.setText("MUTE")

    def set_status(self, status: str) -> None:
        normalized = status.strip().upper()
        self.status = normalized

        # Map state to HUD animations and status caption
        if normalized.startswith("LISTEN"):
            caption = "Listening..."
            color = "#f5d742"
            self.hud.set_listening()
        elif normalized.startswith("TRANSCRIB"):
            caption = "Transcribing voice data..."
            color = "#f5d742"
            self.hud.set_listening()
        elif normalized.startswith("THINK"):
            caption = "Cognitive processing..."
            color = "#00d4ff"
            self.hud.set_thinking()
        elif normalized.startswith("SPEAK"):
            caption = "Speaking..."
            color = "#ff3b30"
            self.hud.set_speaking()
        else:
            caption = "Systems online. Standing by."
            color = "#2dff73"
            self.hud.set_idle()

        self.caption_label.setText(caption)
        self.status_dot.setStyleSheet(
            f"background: {color}; border: 1px solid #dff; border-radius: 7px;"
        )

    def set_caption(self, text: str) -> None:
        self.caption_label.setText(text)

    def update_mic_level(self, rms: float, peak: float) -> None:
        # Scale for visibility in smaller layout bounds
        width = int(rms * (self.mic_bar.width() - 2) * 6.5)
        width = max(0, min(self.mic_bar.width() - 2, width))
        self.mic_level_inner.setGeometry(1, 1, width, 6)
        self.hud.mic_level = rms

    def update_spk_level(self, rms: float, peak: float) -> None:
        width = int(rms * (self.spk_bar.width() - 2) * 5.5)
        width = max(0, min(self.spk_bar.width() - 2, width))
        self.spk_level_inner.setGeometry(1, 1, width, 6)
        self.hud.speaker_level = rms


def main() -> int:
    app = QApplication(sys.argv)
    window = AuraWindow()
    window.add_message("AURA", "Systems online. I am ready, Boss.")
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
