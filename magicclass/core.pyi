from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Generic, TypeVar, overload, Any, Protocol
from typing_extensions import Literal

from ._gui.menu_gui import ContextMenuGui, MenuGui
from ._gui.toolbar import ToolBarGui
from ._gui.class_gui import ClassGuiBase
from ._gui._base import PopUpMode, ErrorMode, MagicTemplate

if TYPE_CHECKING:
    from .types import WidgetType, WidgetTypeStr, PopUpModeStr, ErrorModeStr
    from ._gui._function_gui import FunctionGuiPlus
    from .stylesheets import StyleSheet
    from qtpy.QtWidgets import QWidget
    from .help import HelpWidget
    from macrokit import Macro

Layout = Literal["vertical", "horizontal"]

_C = TypeVar("_C", bound=type)
_M = TypeVar("_M", bound=MagicTemplate)
_V = TypeVar("_V")
_Base = TypeVar("_Base")

class _MagicClassDecorator(Protocol, Generic[_Base]):
    @overload
    def __call__(self, cls: type[_M]) -> type[_M]: ...
    @overload
    def __call__(self, cls: _C) -> type[_Base] | _C: ...

def build_help(ui: MagicTemplate, parent: QWidget | None = None) -> "HelpWidget": ...
def get_function_gui(ui: MagicTemplate, name: str) -> FunctionGuiPlus: ...
@overload
def magicclass(
    class_: type[_M],
    *,
    layout: Layout = "vertical",
    labels: bool = True,
    name: str | None = None,
    visible: bool | None = None,
    close_on_run: bool | None = None,
    popup_mode: PopUpModeStr | PopUpMode | None = None,
    error_mode: ErrorModeStr | ErrorMode | None = None,
    widget_type: WidgetTypeStr | WidgetType = WidgetType.none,
    icon: Any | None = None,
    stylesheet: str | StyleSheet | None = None,
    parent=None,
) -> type[_M]: ...
@overload
def magicclass(
    class_: _C,
    *,
    layout: Layout = "vertical",
    labels: bool = True,
    name: str | None = None,
    visible: bool | None = None,
    close_on_run: bool | None = None,
    popup_mode: PopUpModeStr | PopUpMode | None = None,
    error_mode: ErrorModeStr | ErrorMode | None = None,
    widget_type: WidgetTypeStr | WidgetType = WidgetType.none,
    icon: Any | None = None,
    stylesheet: str | StyleSheet | None = None,
    parent=None,
) -> type[ClassGuiBase] | _C: ...
@overload
def magicclass(
    *,
    layout: Layout = "vertical",
    labels: bool = True,
    name: str | None = None,
    visible: bool | None = None,
    close_on_run: bool | None = None,
    popup_mode: PopUpModeStr | PopUpMode | None = None,
    error_mode: ErrorModeStr | ErrorMode | None = None,
    widget_type: WidgetTypeStr | WidgetType = WidgetType.none,
    icon: Any | None = None,
    stylesheet: str | StyleSheet | None = None,
    parent=None,
) -> _MagicClassDecorator[ClassGuiBase]: ...
@overload
def magicmenu(
    class_: type[_M],
    *,
    close_on_run: bool | None = None,
    popup_mode: str | PopUpMode | None = None,
    error_mode: str | ErrorMode | None = None,
    labels: bool = True,
    name: str | None = None,
    icon: Any | None = None,
    parent=None,
) -> type[_M]: ...
@overload
def magicmenu(
    class_: _C,
    *,
    close_on_run: bool | None = None,
    popup_mode: str | PopUpMode | None = None,
    error_mode: str | ErrorMode | None = None,
    labels: bool = True,
    name: str | None = None,
    icon: Any | None = None,
    parent=None,
) -> type[MenuGui] | _C: ...
@overload
def magicmenu(
    *,
    close_on_run: bool | None = None,
    popup_mode: str | PopUpMode | None = None,
    error_mode: str | ErrorMode | None = None,
    labels: bool = True,
    name: str | None = None,
    icon: Any | None = None,
    parent=None,
) -> _MagicClassDecorator[MenuGui]: ...
@overload
def magiccontext(
    class_: type[_M],
    *,
    into: Callable | None = None,
    close_on_run: bool | None = None,
    popup_mode: str | PopUpMode | None = None,
    error_mode: str | ErrorMode | None = None,
    labels: bool = True,
    name: str | None = None,
    icon: Any | None = None,
    parent=None,
) -> type[_M]: ...
@overload
def magiccontext(
    class_: _C,
    *,
    into: Callable | None = None,
    close_on_run: bool | None = None,
    popup_mode: str | PopUpMode | None = None,
    error_mode: str | ErrorMode | None = None,
    labels: bool = True,
    name: str | None = None,
    icon: Any | None = None,
    parent=None,
) -> type[ContextMenuGui] | _C: ...
@overload
def magiccontext(
    *,
    into: Callable | None = None,
    close_on_run: bool | None = None,
    popup_mode: str | PopUpMode | None = None,
    error_mode: str | ErrorMode | None = None,
    labels: bool = True,
    name: str | None = None,
    icon: Any | None = None,
    parent=None,
) -> _MagicClassDecorator[ContextMenuGui]: ...
@overload
def magictoolbar(
    class_: type[_M],
    *,
    close_on_run: bool | None = None,
    popup_mode: str | PopUpMode | None = None,
    error_mode: str | ErrorMode | None = None,
    labels: bool = True,
    name: str | None = None,
    icon: Any | None = None,
    parent=None,
) -> type[_M]: ...
@overload
def magictoolbar(
    class_: _C,
    *,
    close_on_run: bool | None = None,
    popup_mode: str | PopUpMode | None = None,
    error_mode: str | ErrorMode | None = None,
    labels: bool = True,
    name: str | None = None,
    icon: Any | None = None,
    parent=None,
) -> type[ToolBarGui] | _C: ...
@overload
def magictoolbar(
    *,
    close_on_run: bool | None = None,
    popup_mode: str | PopUpMode | None = None,
    error_mode: str | ErrorMode | None = None,
    labels: bool = True,
    name: str | None = None,
    icon: Any | None = None,
    parent=None,
) -> _MagicClassDecorator[ToolBarGui]: ...
def repeat(ui: MagicTemplate, index: int = -1) -> None: ...
def update_widget_state(
    ui: MagicTemplate, macro: Macro | str | None = None
) -> None: ...

class Parameters:
    def __init__(self): ...
    def __call__(self, *args: Any) -> None: ...
    def as_dict(self) -> dict[str, Any]: ...
