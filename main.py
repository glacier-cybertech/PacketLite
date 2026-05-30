import sys
import os
from PyQt6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QMenu, QGraphicsItem, QGraphicsLineItem, QInputDialog
from PyQt6.QtCore import Qt, QLineF
from PyQt6.QtGui import QWheelEvent, QColor, QPixmap, QPen, QIcon, QPalette, QPainter

# Ensure these are imported from your local files
from engine import Router, PC, Switch, Cable
from models import Node

def apply_dark_theme(app):
    """Applies a professional dark palette to the entire application."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(palette)
    
    # Modern CSS for Menus and Tooltips
    app.setStyleSheet("""
        QMenu {
            background-color: #2d2d2d;
            color: white;
            border: 1px solid #555;
            padding: 5px;
        }
        QMenu::item:selected {
            background-color: #2a82da;
        }
        QMenu::separator {
            height: 1px;
            background: #555;
            margin: 5px;
        }
    """)

class VisualCable(QGraphicsLineItem):
    def __init__(self, node_a, node_b, cable_logic):
        super().__init__()
        self.node_a, self.node_b = node_a, node_b
        self.cable_logic = cable_logic  # Direct tracking of the engine mapping layer
        # Neon Cyan pen for the 'Cyber' look
        self.setPen(QPen(QColor("#00FFCC"), 2))
        self.setZValue(-1)
        self.update_position()

    def update_position(self):
        p1 = self.node_a.sceneBoundingRect().center()
        p2 = self.node_b.sceneBoundingRect().center()
        self.setLine(QLineF(p1, p2))

class VisualNode(QGraphicsPixmapItem):
    def __init__(self, node_data, pos, canvas):
        super().__init__(QPixmap(node_data.icon_image))
        self.node_data, self.canvas = node_data, canvas
        self.visual_cables = []
        self.setPos(pos)
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable | 
                      QGraphicsItem.GraphicsItemFlag.ItemIsSelectable | 
                      QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for c in self.visual_cables: c.update_position()
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton: self.show_menu(event.screenPos())
        super().mousePressEvent(event)

    def initiate_ping(self):
        """Opens an input dialog and triggers the logic ping request."""
        logic = self.node_data.object_field
        target_ip, ok = QInputDialog.getText(
            self.canvas, 'Ping Request', 'Enter Target IP Address:',
            text="192.168.68.1"
        )
        
        if ok and target_ip:
            logic.send_icmp_request(target_ip)

    def delete_node(self):
        """Cleanly tears down visual and backend cable infrastructure before removal."""
        scene = self.scene()
        if not scene:
            return

        # Explicitly casting to a list handles mutations to prevent iteration index shifting
        for v_cable in list(self.visual_cables):
            # Locate opposite edge device node
            neighbor = v_cable.node_b if v_cable.node_a == self else v_cable.node_a
            
            # Flush reference tracking arrays on visual container bounds
            if v_cable in neighbor.visual_cables:
                neighbor.visual_cables.remove(v_cable)
            
            # Fetch backend pointer data
            logic_cable = v_cable.cable_logic
            this_logic_device = self.node_data.object_field
            neighbor_logic_device = neighbor.node_data.object_field

            # Sever the physical engine links on both logical components
            if hasattr(this_logic_device, 'cables') and logic_cable in this_logic_device.cables:
                this_logic_device.cables.remove(logic_cable)
            if hasattr(neighbor_logic_device, 'cables') and logic_cable in neighbor_logic_device.cables:
                neighbor_logic_device.cables.remove(logic_cable)

            # Purge the visual canvas vector element
            scene.removeItem(v_cable)

        # Flush local edge list container data 
        self.visual_cables.clear()

        # Evict node graphic asset element boundary from view plane
        scene.removeItem(self)

    def show_menu(self, screen_pos):
        menu = QMenu()
        logic = self.node_data.object_field
        menu.addAction(f"Device: {logic.name}").setEnabled(False)
        menu.addSeparator()

        # Display IP if the device has one
        if hasattr(logic, 'local_ip'):
            current_ip = logic.local_ip if logic.local_ip else "Not Assigned"
            menu.addAction(f"IP: {current_ip}").setEnabled(False)

        # DHCP Option
        if isinstance(logic, PC):
            menu.addAction("Send DHCP Request", logic.send_dhcp_request)
        
        # ICMP / PING OPTION
        if hasattr(logic, 'ICMPhandler') and logic.ICMPhandler is not None:
            menu.addAction("Send Ping (ICMP)", self.initiate_ping)
            menu.addSeparator()

        menu.addAction("Connect", lambda: self.canvas.start_connection(self))
        menu.addAction("Delete", self.delete_node)
        menu.exec(screen_pos)

class NetworkCanvas(QGraphicsView):
    def __init__(self, registry):
        super().__init__()
        self.setWindowTitle("Packet Lite")
        self.setWindowIcon(QIcon("assets/router.png"))
        self.registry = registry
        
        # Set Dark Scene Background
        self.scene = QGraphicsScene(0, 0, 5000, 5000)
        self.scene.setBackgroundBrush(QColor("#1e1e1e"))
        self.setScene(self.scene)
        
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.connection_source = None
        self.draw_grid()

    def draw_grid(self):
        """Adds a faint grid to the background."""
        pen = QPen(QColor("#333333"), 0.5)
        for i in range(0, 5000, 100):
            self.scene.addLine(i, 0, i, 5000, pen)
            self.scene.addLine(0, i, 5000, i, pen)

    def wheelEvent(self, event):
        f = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.scale(f, f)

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if self.connection_source and isinstance(item, VisualNode):
            self.finish_connection(item)
            return
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        if self.itemAt(event.pos()): return
        menu = QMenu()
        for label, cls in self.registry.items():
            menu.addAction(f"Add {label}", lambda l=label, c=cls: self.spawn(l, c, self.mapToScene(event.pos())))
        menu.exec(self.mapToGlobal(event.pos()))

    def start_connection(self, node):
        self.connection_source = node
        self.setCursor(Qt.CursorShape.CrossCursor)

    def finish_connection(self, target):
        o1 = self.connection_source.node_data.object_field
        o2 = target.node_data.object_field
        cable = Cable(o1, o2)
        o1.cables.append(cable)
        o2.cables.append(cable)
        
        # Explicit pass through of backend architecture token
        v_cable = VisualCable(self.connection_source, target, cable)
        self.scene.addItem(v_cable)
        
        self.connection_source.visual_cables.append(v_cable)
        target.visual_cables.append(v_cable)
        self.connection_source = None
        self.unsetCursor()

    def spawn(self, label, cls, pos):
        node = Node(label, f"assets/{label.lower()}.png", cls())
        v_node = VisualNode(node, pos, self)
        self.scene.addItem(v_node)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Apply Global Dark Palette
    apply_dark_theme(app)
    
    NODE_REGISTRY = {"Router": Router, "PC": PC, "Switch": Switch}
    view = NetworkCanvas(NODE_REGISTRY)
    view.show()
    sys.exit(app.exec())