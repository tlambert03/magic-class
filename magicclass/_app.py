from qtpy.QtWidgets import QApplication
from qtpy import PYQT5
from qtpy.QtCore import Qt

APPLICATION = None


def gui_qt():
    """Call "%gui qt" magic."""
    try:
        from IPython import get_ipython
    except ImportError:
        get_ipython = lambda: False

    shell = get_ipython()

    if shell and shell.active_eventloop != "qt":
        shell.enable_gui("qt")
    return None


def gui_qt_is_active() -> bool:
    """True only if "%gui qt" magic is called in ipython kernel."""
    try:
        from IPython import get_ipython
    except ImportError:
        get_ipython = lambda: False

    shell = get_ipython()

    return shell and shell.active_eventloop == "qt"


def get_app():
    """Get QApplication."""
    gui_qt()
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    global APPLICATION
    APPLICATION = app
    return app


def run_app():
    """Start the event loop."""
    if not gui_qt_is_active():
        return get_app().exec_()


# def consistent_dpi():
#     QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
#     QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

# def menubar_in_widget():
#     QApplication.setAttribute(Qt.AA_DontUseNativeMenuBar)
