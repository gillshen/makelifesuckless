import sys
from PyQt6.QtWidgets import QApplication
from gui import MainWindow

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(True)
window = MainWindow()
window.show()
sys.exit(app.exec())
