from __future__ import annotations
from typing import Callable, Iterable, Any, Generic, TypeVar
from qtpy.QtWidgets import (
    QPushButton,
    QAction,
    QWidgetAction,
    QToolButton,
    QWidget,
    QMenu,
)
from psygnal import Signal
from magicgui.widgets import PushButton
from magicgui.widgets._concrete import _LabeledWidget
from magicgui.widgets._bases import Widget, ValueWidget
from magicgui.backends._qtpy.widgets import QBaseButtonWidget
from ._function_gui import FunctionGuiPlus
from ._icon import get_icon

# magicgui widgets that need to be extended to fit into magicclass


class PushButtonPlus(PushButton):
    """A Qt specific PushButton widget with a magicgui bound."""

    def __init__(self, text: str | None = None, **kwargs):
        super().__init__(text=text, **kwargs)
        self.native: QPushButton
        self._icon = None
        self.mgui: FunctionGuiPlus | None = None  # tagged function GUI
        self._doc = ""
        self._unwrapped = False

    @property
    def running(self) -> bool:
        """Return true if embedded magicgui widget is running from GUI."""
        return getattr(self.mgui, "running", False)

    def set_shortcut(self, key):
        """Set keyboard shortcut to the button."""
        self.native.setShortcut(key)

    def reset_choices(self, *_: Any):
        """Reset child Categorical widgets."""
        if self.mgui is not None:
            self.mgui.reset_choices()

    @property
    def background_color(self):
        """The background color of the button."""
        return self.native.palette().button().color().getRgb()

    @background_color.setter
    def background_color(self, color: str | Iterable[float]):
        stylesheet = self.native.styleSheet()
        d = _stylesheet_to_dict(stylesheet)
        d.update({"background-color": _to_rgb(color)})
        stylesheet = _dict_to_stylesheet(d)
        self.native.setStyleSheet(stylesheet)

    @property
    def icon(self):
        """Get icon object."""
        return self._icon

    @icon.setter
    def icon(self, val):
        icon = get_icon(val)
        icon.install(self)
        self._icon = icon
        self.native.setIconSize(self.native.size())

    @property
    def font_size(self):
        """Font size of the button."""
        return self.native.font().pointSize()

    @font_size.setter
    def font_size(self, size: int):
        font = self.native.font()
        font.setPointSize(size)
        self.native.setFont(font)

    @property
    def font_color(self):
        """Font color of the button."""
        return self.native.palette().text().color().getRgb()

    @font_color.setter
    def font_color(self, color: str | Iterable[float]):
        stylesheet = self.native.styleSheet()
        d = _stylesheet_to_dict(stylesheet)
        d.update({"color": _to_rgb(color)})
        stylesheet = _dict_to_stylesheet(d)
        self.native.setStyleSheet(stylesheet)

    @property
    def font_family(self):
        """Font family of the button."""
        return self.native.font().family()

    @font_family.setter
    def font_family(self, family: str):
        font = self.native.font()
        font.setFamily(family)
        self.native.setFont(font)

    def from_options(self, options: dict[str, Any] | Callable):
        """Set button design options using a dictionary or a function."""

        if callable(options):
            try:
                options = options.__signature__.caller_options
            except AttributeError:
                return None

        for k, v in options.items():
            setattr(self, k, v)
        return None


class _QToolButton(QBaseButtonWidget):
    def __init__(self, **kwargs):
        super().__init__(QToolButton, **kwargs)


class ToolButtonPlus(PushButtonPlus):
    """Buttons for toolbar in magic-class."""

    def __init__(self, text: str | None = None, **kwargs):
        kwargs["widget_type"] = _QToolButton
        ValueWidget.__init__(self, **kwargs)
        self.text = text or self.name.replace("_", " ")
        self.native: QToolButton

    def set_menu(self, qmenu: QMenu):
        """Set menu-like behavior to the tool button."""
        self.native.setMenu(qmenu)
        self.native.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.native.setIcon(qmenu.icon())  # icon have to be copied.

    def set_shortcut(self, key):
        """Set keyboard shortcut to the tool button."""
        self.native.setShortcut(key)

    def reset_choices(self, *_: Any):
        """Reset child Categorical widgets."""
        if self.mgui is not None:
            self.mgui.reset_choices()


class mguiLike:
    """Abstract class that provide magicgui.widgets like properties."""

    native: QWidget | QAction

    @property
    def parent(self):
        """Return the parent object."""
        return self.native.parent()

    @parent.setter
    def parent(self, obj: mguiLike | Widget):
        """Set the parent object."""
        self.native.setParent(obj.native)

    @property
    def name(self) -> str:
        """Name of the object."""
        return self.native.objectName()

    @name.setter
    def name(self, value: str):
        """Set the name of the object."""
        self.native.setObjectName(value)

    @property
    def tooltip(self) -> str:
        """Tooltip of the object."""
        return self.native.toolTip()

    @tooltip.setter
    def tooltip(self, value: str):
        """Set the tooltip of the object."""
        self.native.setToolTip(value)

    @property
    def enabled(self) -> bool:
        """True if the object is enabled."""
        return self.native.isEnabled()

    @enabled.setter
    def enabled(self, value: bool):
        """Set the enabled state of the object."""
        self.native.setEnabled(value)

    @property
    def visible(self) -> bool:
        """Visibility of the object."""
        return self.native.isVisible()

    @visible.setter
    def visible(self, value: bool):
        """Set the visibility of the object."""
        self.native.setVisible(value)

    @property
    def widget_type(self):
        return self.__class__.__name__


class AbstractAction(mguiLike):
    """
    QAction encapsulated class with a similar API as magicgui Widget.
    This class makes it easier to combine QMenu to magicgui.
    """

    changed = Signal(object)
    support_value: bool
    _native: QAction | QWidgetAction

    @property
    def value(self):
        raise NotImplementedError()

    @property
    def native(self) -> QAction | QWidgetAction:
        """The native Qt object."""
        return self._native

    def from_options(self, options):
        raise NotImplementedError()


class Action(AbstractAction):
    support_value = True

    def __init__(
        self, *args, name: str = None, text: str = None, gui_only: bool = True, **kwargs
    ):
        self._native = QAction(*args, **kwargs)
        self.mgui: FunctionGuiPlus = None
        self._doc = ""
        self._unwrapped = False

        self._icon = None
        if text:
            self.text = text
        if name:
            self.native.setObjectName(name)
        self._callbacks = []

        self.native.triggered.connect(lambda: self.changed.emit(self.value))

    @property
    def running(self) -> bool:
        return getattr(self.mgui, "running", False)

    def set_shortcut(self, key):
        self.native.setShortcut(key)
        return None

    def reset_choices(self, *_: Any):
        """Reset child Categorical widgets."""
        if self.mgui is not None:
            self.mgui.reset_choices()

    @property
    def text(self) -> str:
        return self.native.text()

    @text.setter
    def text(self, value: str):
        self.native.setText(value)

    @property
    def value(self):
        return self.native.isChecked()

    @value.setter
    def value(self, checked: bool):
        self.native.setChecked(checked)

    @property
    def icon(self):
        return self._icon

    @icon.setter
    def icon(self, val):
        icon = get_icon(val)
        icon.install(self)
        self._icon = icon

    def from_options(self, options: dict[str] | Callable):
        if callable(options):
            try:
                options = options.__signature__.caller_options
            except AttributeError:
                return None

        for k, v in options.items():
            setattr(self, k, v)
        return None


_W = TypeVar("_W", bound=Widget)


class WidgetAction(AbstractAction, Generic[_W]):
    """An Action class that contains a Widget object."""

    def __init__(self, widget: _W, label: str = None, parent=None):
        if not isinstance(widget, (Widget, mguiLike)):
            raise TypeError(
                f"The first argument must be a magicgui-like widget, got {type(widget)}"
            )

        self._native = QWidgetAction(parent)
        self.widget = widget
        name = widget.name
        self.native.setObjectName(name)
        self.label = label or name.replace("_", " ")
        self.text = getattr(widget, "text", None) or name.replace("_", " ")

        self.native.setDefaultWidget(widget.native)
        self.support_value = isinstance(
            widget, (ValueWidget, _LabeledWidget)
        ) or hasattr(widget, "value")

        if self.support_value:
            self.widget.changed.connect(lambda: self.changed.emit(self.value))

    @property
    def widget_type(self):
        return self.widget.widget_type

    @property
    def value(self):
        if self.support_value:
            return self.widget.value
        else:
            msg = (
                f"WidgetAction {self.name} has {type(self.widget)} as the default "
                "widget, which does not have value property."
            )
            raise AttributeError(msg)

    @value.setter
    def value(self, v):
        if self.support_value:
            self.widget.value = v
        else:
            msg = (
                f"WidgetAction {self.name} has {type(self.widget)} as the default "
                "widget, which does not have value property."
            )
            raise AttributeError(msg)

    @property
    def text(self) -> str:
        return self.native.text()

    @text.setter
    def text(self, value: str):
        self.native.setText(value)
        if hasattr(self.widget, "text"):
            self.widget.text = value

    @property
    def tooltip(self) -> str:
        """Tooltip of the inner widget."""
        return self.widget.tooltip

    @tooltip.setter
    def tooltip(self, value: str):
        """Set the tooltip of the inner widget."""
        self.widget.tooltip = value

    def _labeled_widget(self):
        return self.widget._labeled_widget()

    def render(self):
        return self.widget.render()

    def _repr_png_(self):
        return self.widget._repr_png_()


class _LabeledWidgetAction(WidgetAction):
    widget: _LabeledWidget

    def __init__(self, widget: Widget, label: str = None):
        if not isinstance(widget, Widget):
            raise TypeError(f"The first argument must be a Widget, got {type(widget)}")

        _labeled_widget = _LabeledWidget(widget, label)
        super().__init__(_labeled_widget)
        self.name = widget.name

        # Strangely, visible.setter does not work for sliders.
        widget.native.setVisible(True)

    @classmethod
    def from_action(cls, action: WidgetAction):
        """Construct a labeled action using another action."""
        self = cls(action.widget, action.label)
        action.parent = self
        return self

    @property
    def label_width(self):
        return self.widget._label_widget.width

    @label_width.setter
    def label_width(self, width):
        self.widget._label_widget.min_width = width


def _to_rgb(color):
    if isinstance(color, str):
        from matplotlib.colors import to_rgb

        color = to_rgb(color)
    rgb = ",".join(str(max(min(int(c * 255), 255), 0)) for c in color)
    return f"rgb({rgb})"


def _stylesheet_to_dict(stylesheet: str):
    if stylesheet == "":
        return {}
    lines = stylesheet.split(";")
    d = dict()
    for line in lines:
        k, v = line.split(":")
        d[k.strip()] = v.strip()
    return d


def _dict_to_stylesheet(d: dict):
    stylesheet = [f"{k}: {v}" for k, v in d.items()]
    return ";".join(stylesheet)
