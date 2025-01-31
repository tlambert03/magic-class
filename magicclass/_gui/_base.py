from __future__ import annotations
import functools
from typing import (
    Any,
    Callable,
    TYPE_CHECKING,
    Iterable,
    Iterator,
    TypeVar,
    overload,
    MutableSequence,
)
from types import MethodType
from abc import ABCMeta
from typing_extensions import _AnnotatedAlias, Literal
import inspect
import warnings
from enum import Enum
from docstring_parser import parse, compose
from qtpy.QtWidgets import QWidget, QDockWidget

from psygnal import Signal
from magicgui.signature import MagicParameter
from magicgui.widgets import (
    FunctionGui,
    FileEdit,
    EmptyWidget,
    Widget,
    Container,
    Image,
    Table,
    Label,
    MainWindow,
)
from magicgui.application import use_app
from magicgui.widgets._bases.widget import Widget
from magicgui.widgets._bases import ButtonWidget
from macrokit import Symbol

from .keybinding import as_shortcut
from .mgui_ext import (
    AbstractAction,
    Action,
    FunctionGuiPlus,
    PushButtonPlus,
    _LabeledWidgetAction,
    mguiLike,
)
from .utils import copy_class, callable_to_classes
from ._macro import GuiMacro
from ._macro_utils import inject_recorder, value_widget_callback
from ._icon import get_icon

from ..utils import (
    get_signature,
    iter_members,
    Tooltips,
    move_to_screen_center,
    argcount,
    is_instance_method,
    method_as_getter,
    eval_attribute,
)
from ..widgets import Separator, FreeWidget
from ..fields import MagicField
from ..signature import (
    MagicMethodSignature,
    get_additional_option,
    split_annotated_type,
)
from ..wrappers import upgrade_signature
from ..types import BoundLiteral
from ..functools import wraps

if TYPE_CHECKING:
    import numpy as np
    import napari
    from types import TracebackType
    from typing_extensions import Self


class PopUpMode(Enum):
    """Define how to popup FunctionGui."""

    popup = "popup"
    first = "first"
    last = "last"
    above = "above"
    below = "below"
    dock = "dock"
    dialog = "dialog"
    parentlast = "parentlast"
    parentsub = "parentsub"


def _msgbox_raising(e: Exception, parent: Widget):
    from ._message_box import QtErrorMessageBox

    return QtErrorMessageBox.raise_(e, parent=parent.native)


def _stderr_raising(e: Exception, parent: Widget):
    pass


def _stdout_raising(e: Exception, parent: Widget):
    print(f"{e.__class__.__name__}: {e}")


def _napari_notification_raising(e: Exception, parent: Widget):
    from napari.utils.notifications import show_error

    return show_error(str(e))


class ErrorMode(Enum):
    msgbox = "msgbox"
    stderr = "stderr"
    stdout = "stdout"
    napari = "napari"

    def get_handler(self):
        """Get error handler."""
        return ErrorModeHandlers[self]

    def wrap_handler(self, func: Callable, parent):
        """Wrap function with the error handler."""
        handler = self.get_handler()

        @functools.wraps(func)
        def wrapped_func(*args, **kwargs):
            try:
                out = func(*args, **kwargs)
            except Exception as e:
                e.__traceback__ = _cleanup_tb(e.__traceback__)
                handler(e, parent=parent)
                out = e
            return out

        return wrapped_func


ErrorModeHandlers = {
    ErrorMode.msgbox: _msgbox_raising,
    ErrorMode.stderr: _stderr_raising,
    ErrorMode.stdout: _stdout_raising,
    ErrorMode.napari: _napari_notification_raising,
}


defaults = {
    "popup_mode": PopUpMode.popup,
    "error_mode": ErrorMode.msgbox,
    "close_on_run": True,
    "macro-max-history": 1000,
}

_RESERVED = frozenset(
    {
        "__magicclass_parent__",
        "__magicclass_children__",
        "_close_on_run",
        "_error_mode",
        "_popup_mode",
        "_my_symbol",
        "_macro_instance",
        "macro",
        "annotation",
        "enabled",
        "find_ancestor",
        "gui_only",
        "height",
        "label_changed",
        "label",
        "layout",
        "labels",
        "margins",
        "max_height",
        "max_width",
        "min_height",
        "min_width",
        "name",
        "options",
        "param_kind",
        "parent_changed",
        "tooltip",
        "visible",
        "widget_type",
        "width",
        "wraps",
        "_unwrap_method",
        "_search_parent_magicclass",
        "_iter_child_magicclasses",
    }
)


def check_override(cls: type):
    """
    Some of the methods should not be overriden because they are essential for magic
    class construction.

    Parameters
    ----------
    cls : type
        Base class to test override.

    Raises
    ------
    AttributeError
        If forbidden override found.
    """
    subclass_members = set(cls.__dict__.keys())
    collision = subclass_members & _RESERVED
    if collision:
        raise AttributeError(
            f"Cannot override magic class reserved attributes: {collision}"
        )


_ANCESTORS: dict[tuple[int, int], MagicTemplate] = {}

_T = TypeVar("_T", bound="MagicTemplate")
_F = TypeVar("_F", bound=Callable)


class _MagicTemplateMeta(ABCMeta):
    """This metaclass enables type checking of nested magicclasses."""

    @overload
    def __get__(self: type[_T], obj: Any, objtype=None) -> _T:
        ...

    @overload
    def __get__(self: type[_T], obj: Literal[None], objtype=None) -> type[_T]:
        ...

    def __get__(self, obj, objtype=None):
        return self


_W = TypeVar("_W")


class MagicTemplate(MutableSequence[_W], metaclass=_MagicTemplateMeta):
    __doc__ = ""
    __magicclass_parent__: None | MagicTemplate
    __magicclass_children__: list[MagicTemplate]
    _close_on_run: bool
    _component_class: type[Action | Widget]
    _error_mode: ErrorMode
    _list: list[Action | Widget]
    _macro_instance: GuiMacro
    _my_symbol: Symbol
    _popup_mode: PopUpMode
    annotation: Any
    changed: Signal
    enabled: bool
    gui_only: bool
    height: int
    icon: Any
    label_changed: Signal
    label: str
    layout: str
    labels: bool
    margins: tuple[int, int, int, int]
    max_height: int
    max_width: int
    min_height: int
    min_width: int
    name: str
    native: QWidget
    options: dict
    param_kind: inspect._ParameterKind
    parent: Widget
    parent_changed: Signal
    tooltip: str
    visible: bool
    widget_type: str
    width: int

    __init_subclass__ = check_override

    def show(self, run: bool) -> None:
        raise NotImplementedError()

    def hide(self) -> None:
        raise NotImplementedError()

    def close(self) -> None:
        raise NotImplementedError()

    @overload
    def __getitem__(self, key: int | str) -> _W:
        ...

    @overload
    def __getitem__(self, key: slice) -> Self[_W]:
        ...

    def __getitem__(self, key):
        raise NotImplementedError()

    def index(self, value: Any, start: int, stop: int) -> int:
        raise NotImplementedError()

    def remove(self, value: Widget | str):
        raise NotImplementedError()

    def _fast_insert(self, key: int, widget: _W | Callable) -> None:
        raise NotImplementedError()

    def insert(self, key: int, widget: _W | Callable) -> None:
        self._fast_insert(key, widget)
        self._unify_label_widths()

    def render(self) -> np.ndarray:
        raise NotImplementedError()

    def _unify_label_widths(self):
        raise NotImplementedError()

    def reset_choices(self, *args):
        raise NotImplementedError()

    @property
    def macro(self) -> GuiMacro:
        """The macro object bound to the ancestor widget."""
        if self.__magicclass_parent__ is None:
            return self._macro_instance
        else:
            return self.__magicclass_parent__.macro

    @property
    def parent_viewer(self) -> napari.Viewer | None:
        """Return napari.Viewer if magic class is a dock widget of a viewer."""
        parent_self = self._search_parent_magicclass()
        if parent_self.native.parent() is None:
            return None
        try:
            from napari.utils._magicgui import find_viewer_ancestor
        except ImportError:
            return None
        viewer = find_viewer_ancestor(parent_self.native)
        return viewer

    @property
    def parent_dock_widget(self) -> QDockWidget | None:
        """
        Return dock widget object if magic class is a dock widget of a main
        window widget, such as a napari Viewer.
        """
        parent_self = self._search_parent_magicclass()
        try:
            dock = parent_self.native.parent()
            if not isinstance(dock, QDockWidget):
                dock = None
        except AttributeError:
            dock = None

        return dock

    def find_ancestor(self, ancestor: type[_T], cache: bool = False) -> _T:
        """
        Find magic class ancestor whose type matches the input.

        This method is useful when a child widget class is defined outside a magic
        class while it needs access to its parent.

        Parameters
        ----------
        ancestor : type of MagicTemplate
            Type of ancestor to search for.
        cache : bool, default is False
            If true, the result will be cached. Caching is not safe if the widget is
            going to be used as a child of other widgets.

        Returns
        -------
        MagicTemplate
            Magic class object if found.
        """
        if cache and (anc := _ANCESTORS.get((id(self), id(ancestor)), None)):
            return anc

        if not isinstance(ancestor, type):
            raise TypeError(
                "The first argument of 'find_ancestor' must be a type but got "
                f"{type(ancestor)}"
            )

        current_self = self
        while type(current_self) is not ancestor:
            current_self = current_self.__magicclass_parent__
            if current_self is None:
                raise RuntimeError(
                    f"Magic class {ancestor.__name__} not found. {ancestor.__name__} "
                    f"is not an ancestor of {self.__class__.__name__}"
                )
        if cache:
            _ANCESTORS[(id(self), id(ancestor))] = current_self
        return current_self

    def objectName(self) -> str:
        """
        Return object name of the QWidget.

        This function makes the object name discoverable by napari's
        `viewer.window.add_dock_widget` function. At the same time, since this function
        will always be called when the widget is added as a dock widget of napari, we
        can import macro recorders for napari types in the appropriate timing.
        """
        try:
            from . import _napari_type  # load default macro recorder.
        except Exception:
            pass
        return self.native.objectName()

    @classmethod
    def wraps(
        cls,
        method: _F | None = None,
        *,
        template: Callable | None = None,
        copy: bool = False,
    ) -> _F:
        """
        Wrap a parent method in a child magic-class.

        Wrapped method will appear in the child widget but behaves as if it is in
        the parent widget. Basically, this function is used as a wrapper like below.

        .. code-block:: python

            @magicclass
            class C:
                @magicclass
                class D:
                    def func(self, ...): ... # pre-definition
                @D.wraps
                def func(self, ...): ...

        Parameters
        ----------
        method : Callable, optional
            Method of parent class.
        template : Callable, optional
            Function template for signature.
        copy: bool, default is False
            If true, wrapped method is still enabled.

        Returns
        -------
        Callable
            Same method as input, but has updated signature.
        """
        if (not copy) and get_additional_option(method, "into", None) is not None:
            # If method is already wrapped, wraps should create a copy.
            copy = True

        def wrapper(method: _F):
            # Base function to get access to the original function
            if isinstance(method, FunctionGui):
                func = method._function
            else:
                func = method

            if template is not None:
                wraps(template)(func)

            predefined = getattr(cls, func.__name__, None)
            if predefined is not None:
                # Update signature to the parent one. This step is necessary when widget design
                # is defined on the parent side. Parameters should be replaced with a simplest
                # one to avoid creating useless widgets.
                parent_sig = get_signature(func)
                _simple_param = inspect.Parameter(
                    "self", inspect.Parameter.POSITIONAL_OR_KEYWORD
                )
                if not hasattr(predefined, "__signature__"):
                    predefined.__signature__ = parent_sig.replace(
                        parameters=(_simple_param,),
                    )
                else:
                    sig: inspect.Signature = predefined.__signature__
                    predefined.__signature__ = sig.replace(
                        parameters=parent_sig.parameters.values(),
                        return_annotation=parent_sig.return_annotation,
                    )
                upgrade_signature(predefined, additional_options={"copyto": []})

            if copy:
                copyto_list = get_additional_option(func, "copyto", [])
                copyto_list.append(cls.__name__)
                upgrade_signature(func, additional_options={"copyto": copyto_list})
            else:
                upgrade_signature(func, additional_options={"into": cls.__name__})
            return method

        return wrapper if method is None else wrapper(method)

    def _unwrap_method(
        self,
        method_name: str,
        widget: FunctionGui | PushButtonPlus | Action,
        moveto: str,
        copyto: list[str],
    ):
        """
        This private method converts class methods that are wrapped by its child widget class
        into widget in child widget. Practically same widget is shared between parent and child,
        but only visible in the child side.

        Parameters
        ----------
        moveto : str
            Name of child widget class name.
        method_name : str
            Name of method.
        widget : FunctionGui
            Widget to be added.

        Raises
        ------
        RuntimeError
            If ``child_clsname`` was not found in child widget list. This error will NEVER be raised
            in the user's side.
        """
        if moveto is not None:
            matcher = copyto + [moveto]
        else:
            matcher = copyto

        _found = 0
        _n_match = len(matcher)
        for child_instance in self._iter_child_magicclasses():
            _name = child_instance.__class__.__name__
            if _name in matcher:
                n_children = len(child_instance)

                # get the position of predefined child widget
                try:
                    index = _get_index(child_instance, method_name)
                    new = False
                except ValueError:
                    index = n_children
                    new = True

                self._fast_insert(len(self), widget)
                copy = _name in copyto

                if isinstance(widget, FunctionGui):
                    if copy:
                        widget = widget.copy()
                    if new:
                        child_instance._fast_insert(n_children, widget)
                    else:
                        del child_instance[index - 1]
                        child_instance._fast_insert(index, widget)
                    widget.visible = True

                else:
                    widget.visible = copy
                    if new:
                        child_widget = child_instance._create_widget_from_method(
                            _empty_func(method_name)
                        )
                        child_widget.text = widget.text
                        child_instance._fast_insert(n_children, child_widget)
                    else:
                        child_widget = child_instance[index]

                    child_widget.changed.disconnect()
                    child_widget.changed.connect(widget.changed)
                    child_widget.tooltip = widget.tooltip
                    child_widget._doc = widget._doc

                widget._unwrapped = True

                _found += 1
                if _found == _n_match:
                    break

        else:
            raise RuntimeError(
                f"{method_name} not found in class {self.__class__.__name__}"
            )

    def _convert_attributes_into_widgets(self):
        """
        This function is called in dynamically created __init__. Methods, fields and nested
        classes are converted to magicgui widgets.
        """
        raise NotImplementedError()

    def _create_widget_from_field(self, name: str, fld: MagicField):
        """
        This function is called when magic-class encountered a MagicField in its definition.

        Parameters
        ----------
        name : str
            Name of variable
        fld : MagicField
            A field object that describes what type of widget it should be.
        """
        raise NotImplementedError()

    def _create_widget_from_method(self, obj: MethodType):
        """Convert instance methods into GUI objects, such as push buttons or actions."""
        if hasattr(obj, "__name__"):
            obj_name = obj.__name__
        else:
            _inner_func = obj
            while hasattr(_inner_func, "func"):
                _inner_func = _inner_func.func
            obj_name = getattr(_inner_func, "__name__", str(_inner_func))
        text = obj_name.replace("_", " ")
        widget = self._component_class(name=obj_name, text=text, gui_only=True)

        func = _create_gui_method(self, obj)

        # Prepare a button or action
        widget.tooltip = Tooltips(func).desc
        widget._doc = func.__doc__

        # Get the number of parameters except for empty widgets.
        # With these lines, "bind" method of magicgui works inside magicclass.
        fgui_classes = callable_to_classes(func)
        n_empty = len(
            [_wdg_cls for _wdg_cls in fgui_classes if _wdg_cls is EmptyWidget]
        )
        nparams = argcount(func) - n_empty

        has_preview = get_additional_option(func, "preview", None) is not None

        if nparams == 0 and not has_preview:
            # We don't want a dialog with a single widget "Run" to show up.
            def run_function():
                # NOTE: callback must be defined inside function. Magic class must be
                # "compiled" otherwise function wrappings are not ready!
                mgui = _build_mgui(widget, func, self)
                mgui.native.setParent(self.native, mgui.native.windowFlags())
                out = mgui()

                return out

        elif nparams == 1 and issubclass(fgui_classes[0], FileEdit) and not has_preview:
            # We don't want to open a magicgui dialog and again open a file dialog.
            def run_function():
                mgui = _build_mgui(widget, func, self)
                mgui.native.setParent(self.native, mgui.native.windowFlags())
                fdialog: FileEdit = mgui[0]
                if result := fdialog._show_file_dialog(
                    fdialog.mode,
                    caption=fdialog._btn_text,
                    start_path=str(fdialog.value),
                    filter=fdialog.filter,
                ):
                    fdialog.value = result
                    out = mgui(result)
                else:
                    out = None
                return out

        else:
            _prep_func = _define_popup(self, func, widget)

            def run_function():
                mgui = _build_mgui(widget, func, self)
                if mgui.call_count == 0:  # connect only once
                    _prep_func(mgui)
                    if self._popup_mode not in (
                        PopUpMode.popup,
                        PopUpMode.dock,
                        PopUpMode.parentsub,
                        PopUpMode.dialog,
                    ):
                        mgui.label = ""
                        # to avoid name collision
                        mgui.name = f"mgui-{id(mgui._function)}"
                        mgui.margins = (0, 0, 0, 0)
                        title = Separator(
                            orientation="horizontal", title=text, button=True
                        )
                        # TODO: should remove mgui from self?
                        title.btn_clicked.connect(mgui.hide)
                        mgui.insert(0, title)

                    if self._close_on_run and not mgui._auto_call:
                        if self._popup_mode not in (
                            PopUpMode.dock,
                            PopUpMode.parentsub,
                            PopUpMode.dialog,
                        ):
                            mgui.called.connect(mgui.hide)
                        elif self._popup_mode in (PopUpMode.dock, PopUpMode.parentsub):
                            # If FunctioGui is docked or in a subwindow, we should close
                            # the parent QDockWidget/QMdiSubwindow.
                            mgui.called.connect(lambda: mgui.parent.hide())

                if nparams == 1 and issubclass(fgui_classes[0], FileEdit):
                    fdialog: FileEdit = mgui[0]
                    if result := fdialog._show_file_dialog(
                        fdialog.mode,
                        caption=fdialog._btn_text,
                        start_path=str(fdialog.value),
                        filter=fdialog.filter,
                    ):
                        fdialog.value = result
                    else:
                        return None

                if self._popup_mode not in (
                    PopUpMode.dock,
                    PopUpMode.dialog,
                    PopUpMode.parentsub,
                ):
                    widget.mgui.show()
                elif self._popup_mode == PopUpMode.dock:
                    mgui.parent.show()  # show dock widget
                elif self._popup_mode == PopUpMode.parentsub:
                    mgui.native.parent().setVisible(True)
                else:
                    mgui.exec_as_dialog(parent=self)

                return None

        widget.changed.connect(run_function)

        # If design is given, load the options.
        widget.from_options(func)

        # keybinding
        keybinding = get_additional_option(func, "keybinding", None)
        if keybinding is not None:
            shortcut = as_shortcut(keybinding)
            widget.set_shortcut(shortcut)

        return widget

    def _search_parent_magicclass(self) -> MagicTemplate:
        """Find the ancestor."""
        current_self = self
        while (
            parent := getattr(current_self, "__magicclass_parent__", None)
        ) is not None:
            current_self = parent
        return current_self

    def _iter_child_magicclasses(self) -> Iterable[MagicTemplate]:
        """Iterate over all the child magic classes"""
        for child in self.__magicclass_children__:
            yield child
            yield from child._iter_child_magicclasses()

    def _call_with_return_callback(self, fname: str, *args, **kwargs) -> None:
        from ..core import get_function_gui

        fgui = get_function_gui(self, fname)
        fgui(*args, **kwargs)
        return None


class BaseGui(MagicTemplate[_W]):
    def __init__(self, close_on_run, popup_mode, error_mode):
        self._macro_instance = GuiMacro(
            max_lines=defaults["macro-max-history"],
            flags={"Get": False, "Return": False},
        )
        self.__magicclass_parent__: BaseGui | None = None
        self.__magicclass_children__: list[MagicTemplate] = []
        self._close_on_run = close_on_run
        self._popup_mode = popup_mode or PopUpMode.popup
        self._error_mode = error_mode or ErrorMode.msgbox
        self._my_symbol = Symbol.var("ui")
        self._icon = None

        self.macro.widget.__magicclass_parent__ = self

    @property
    def icon(self):
        return self._icon

    @icon.setter
    def icon(self, val):
        icon = get_icon(val)
        qicon = icon.get_qicon(self)
        self._icon = icon
        if hasattr(self.native, "setIcon"):
            self.native.setIcon(qicon)
        else:
            self.native.setWindowIcon(qicon)
        if hasattr(self.native, "setIconSize"):
            self.native.setIconSize(self.native.size())


class ContainerLikeGui(BaseGui[Action], mguiLike):
    # This class enables similar API between magicgui widgets and additional widgets
    # in magicclass such as menu and toolbar.
    _component_class = Action
    changed = Signal(object)
    _list: list[AbstractAction | ContainerLikeGui]

    def reset_choices(self, *_: Any):
        """Reset child Categorical widgets"""
        all_widgets: set[Widget] = set()

        for item in self._list:
            widget = getattr(item, "_inner_widget", item)
            all_widgets.add(widget)
        for widget in self.__magicclass_children__:
            all_widgets.add(widget)

        for w in all_widgets:
            if hasattr(w, "reset_choices"):
                w.reset_choices()

    def _create_widget_from_field(self, name: str, fld: MagicField):
        if fld.not_ready():
            raise TypeError(
                f"MagicField {name} does not contain enough information for widget creation"
            )

        fld.name = fld.name or name
        action = fld.get_action(self)

        if action.support_value and fld.record:
            # By default, set value function will be connected to the widget.
            getvalue = type(fld) is MagicField
            f = value_widget_callback(self, action, name, getvalue=getvalue)
            action.changed.connect(f)

        return action

    def __getitem__(self, key: int | str) -> ContainerLikeGui | AbstractAction:
        if isinstance(key, int):
            return self._list[key]

        out = None
        for obj in self._list:
            if obj.name == key:
                out = obj
                break
        if out is None:
            raise KeyError(key)
        return out

    def __setitem__(self, key, value):
        raise NotImplementedError()

    def __delitem__(self, key: int | str) -> None:
        self.native.removeAction(self[key].native)

    def __iter__(self) -> Iterator[ContainerLikeGui | AbstractAction]:
        return iter(self._list)

    def __len__(self) -> int:
        return len(self._list)

    def append(self, obj: Callable | ContainerLikeGui | AbstractAction) -> None:
        return self.insert(len(self._list), obj)

    def _unify_label_widths(self):
        _hide_labels = (
            _LabeledWidgetAction,
            ButtonWidget,
            FreeWidget,
            Label,
            FunctionGui,
            BaseGui,
            Image,
            Table,
            Action,
        )
        need_labels = [w for w in self if not isinstance(w, _hide_labels)]

        if self.labels and need_labels:
            measure = use_app().get_obj("get_text_width")
            widest_label = max(measure(w.label) for w in need_labels)
            for w in need_labels:
                labeled_widget = w._labeled_widget()
                if labeled_widget:
                    labeled_widget.label_width = widest_label

    def render(self):
        try:
            import numpy as np
        except ImportError:
            raise ModuleNotFoundError(
                "could not find module 'numpy'. "
                "Please `pip install numpy` to render widgets."
            ) from None
        import qtpy

        img = self.native.grab().toImage()
        bits = img.constBits()
        h, w, c = img.height(), img.width(), 4
        if qtpy.API_NAME == "PySide2":
            arr = np.array(bits).reshape(h, w, c)
        else:
            bits.setsize(h * w * c)
            arr = np.frombuffer(bits, np.uint8).reshape(h, w, c)

        return arr[:, :, [2, 1, 0, 3]]

    def _repr_png_(self):
        """Return PNG representation of the widget for QtConsole."""
        from io import BytesIO

        try:
            from imageio import imsave
        except ImportError:
            print(
                "(For a nicer magicmenu widget representation in "
                "Jupyter, please `pip install imageio`)"
            )
            return None

        with BytesIO() as file_obj:
            imsave(file_obj, self.render(), format="png")
            file_obj.seek(0)
            return file_obj.read()


def _get_widget_name(widget: Widget):
    # To escape reference
    return widget.name


def _create_gui_method(self: BaseGui, obj: MethodType):
    func_sig = inspect.signature(obj)
    # Method type cannot set __signature__ attribute.
    @functools.wraps(obj)
    def func(*args, **kwargs):
        return obj(*args, **kwargs)

    func.__signature__ = func_sig

    # This block enables instance methods in "bind" or "choices" of ValueWidget.
    all_params: list[inspect.Parameter] = []
    for param in func.__signature__.parameters.values():
        if isinstance(param.annotation, _AnnotatedAlias):
            annot, opt = split_annotated_type(param.annotation)
            param = MagicParameter.from_parameter(param, gui_options=opt)

        if isinstance(param, MagicParameter):
            _param = MagicParameter(
                name=param.name,
                kind=param.kind,
                default=param.default,
                annotation=split_annotated_type(param.annotation)[0],
                gui_options=param.options.copy(),
            )
            _arg_bind = _param.options.get("bind", None)
            _arg_choices = _param.options.get("choices", None)

            # If bound method is a class method, use self.method(widget).
            if isinstance(_arg_bind, str):
                try:
                    _arg_bind = eval_attribute(type(self), _arg_bind)
                except Exception:
                    pass
                else:
                    warnings.warn(
                        "Binding method name string is deprecated for the safety reason. "
                        "Please use method itself.",
                        DeprecationWarning,
                    )

            if isinstance(_arg_bind, BoundLiteral):
                _arg_bind = _arg_bind.eval(type(self))

            if is_instance_method(_arg_bind):
                _param.options["bind"] = method_as_getter(self, _arg_bind)

            # If a MagicFiled is bound, bind the value of the connected widget.
            elif isinstance(_arg_bind, MagicField):
                _param.options["bind"] = _arg_bind.as_remote_getter(self)

            # If choices are provided by a class method, use self.method(widget).
            if isinstance(_arg_choices, str):
                _arg_choices = eval_attribute(type(self), _arg_choices)

            if is_instance_method(_arg_choices):
                _param.options["choices"] = method_as_getter(self, _arg_choices)

        else:
            _param = param

        all_params.append(_param)

    func.__signature__ = func.__signature__.replace(parameters=all_params)
    if isinstance(func.__signature__, MagicMethodSignature):
        func.__signature__.additional_options = getattr(
            func_sig, "additional_options", {}
        )
    return func


def _build_mgui(widget_: Action | PushButtonPlus, func: Callable, parent: BaseGui):
    if widget_.mgui is not None:
        return widget_.mgui
    try:
        sig = getattr(func, "__signature__", None)
        if isinstance(sig, MagicMethodSignature):
            opt = sig.additional_options
        else:
            opt = {}

        # confirmation
        conf = opt.get("confirm", None)
        if conf is not None:
            func = _implement_confirmation(func, parent, **conf)

        # Wrap function to deal with errors in a right way.
        func = parent._error_mode.wrap_handler(func, parent=parent)

        call_button = opt.get("call_button", None)
        layout = opt.get("layout", "vertical")
        labels = opt.get("labels", True)
        auto_call = opt.get("auto_call", False)
        mgui = FunctionGuiPlus(
            func, call_button, layout=layout, labels=labels, auto_call=auto_call
        )
        preview_setting = opt.get("preview", None)
        if preview_setting is not None:
            btn_text, is_auto_call, previewer = preview_setting
            mgui.append_preview(
                previewer.__get__(parent), btn_text, auto_call=is_auto_call
            )

    except Exception as e:
        msg = (
            "Exception was raised during building magicgui from method "
            f"{func.__name__}.\n{e.__class__.__name__}: {e}"
        )
        raise type(e)(msg)

    widget_.mgui = mgui
    name = widget_.name or ""
    mgui.native.setWindowTitle(name.replace("_", " ").strip())

    return _connect_functiongui_event(mgui, opt)


def _connect_functiongui_event(
    mgui: FunctionGuiPlus, opt: dict[str, Any]
) -> FunctionGui:
    _on_calling = opt.get("on_calling", [])
    for cb in _on_calling:
        mgui.calling.connect(cb)

    _on_called = opt.get("on_called", [])
    for cb in _on_called:
        mgui.called.connect(lambda: cb(mgui))
    return mgui


def _get_index(container: Container, widget_or_name: Widget | str) -> int:
    """
    Identical to container[widget_or_name], which sometimes doesn't work
    in magic-class.
    """
    if isinstance(widget_or_name, str):
        name = widget_or_name
    else:
        name = widget_or_name.name
    for i, widget in enumerate(container):
        if widget.name == name:
            break
    else:
        raise ValueError(f"{widget_or_name} not found in {container}")
    return i


def _child_that_has_widget(
    self: BaseGui, method: Callable, widget_or_name: Widget | str
) -> BaseGui:
    child_clsname = get_additional_option(method, "into")
    if child_clsname is None:
        return self
    for child_instance in self._iter_child_magicclasses():
        if child_instance.__class__.__name__ == child_clsname:
            break
    else:
        raise ValueError(f"{widget_or_name} not found.")
    return child_instance


def convert_attributes(cls: type[_T], hide: tuple[type, ...]) -> dict[str, Any]:
    """
    Convert class attributes into macro recordable ones.

    Returned dictionary can be directly used for the third argument of
    ``type`` constructor. To avoid converting all the callables in
    subclasses, subclasses that will be iterated over can be restricted
    using ``hide`` argument.

    Parameters
    ----------
    cls : BaseGui type
        Class that will be converted.
    hide : tuple of types
        MROs that will be ignored during iteration.

    Returns
    -------
    dict
        New namespace.
    """
    _dict: dict[str, Callable] = {}
    _pass_type = (property, classmethod, staticmethod, type, Widget, MagicField)
    mro = [c for c in cls.__mro__ if c not in hide]
    for subcls in reversed(mro):
        for name, obj in subcls.__dict__.items():
            if isinstance(obj, _MagicTemplateMeta):
                new_attr = copy_class(obj, cls, name=name)
            elif (
                name.startswith("_") or isinstance(obj, _pass_type) or not callable(obj)
            ):
                # private method, non-action-like object, not-callable object are passed.
                new_attr = obj
            elif callable(obj) and get_additional_option(obj, "record", True):
                new_attr = inject_recorder(obj)
            else:
                new_attr = obj

            _dict[name] = new_attr
    return _dict


def _define_popup(self: BaseGui, obj, widget: PushButtonPlus | Action):
    # deal with popup mode.
    popup_mode = self._popup_mode
    if popup_mode == PopUpMode.popup:
        # To be popped up correctly, window flags of FunctionGui should be
        # "windowFlags" and should appear at the center.
        def _prep(mgui: FunctionGui):
            mgui.native.setParent(self.native, mgui.native.windowFlags())
            move_to_screen_center(mgui.native)

    elif popup_mode == PopUpMode.parentlast:

        def _prep(mgui: FunctionGui):
            parent_self = self._search_parent_magicclass()
            parent_self.append(mgui)

    elif popup_mode == PopUpMode.first:

        def _prep(mgui: FunctionGui):
            child_self = _child_that_has_widget(self, obj, widget)
            child_self.insert(0, mgui)

    elif popup_mode == PopUpMode.last:

        def _prep(mgui: FunctionGui):
            child_self = _child_that_has_widget(self, obj, widget)
            child_self.append(mgui)

    elif popup_mode == PopUpMode.above:

        def _prep(mgui: FunctionGui):
            child_self = _child_that_has_widget(self, obj, widget)
            i = _get_index(child_self, widget)
            child_self.insert(i, mgui)

    elif popup_mode == PopUpMode.below:

        def _prep(mgui: FunctionGui):
            child_self = _child_that_has_widget(self, obj, widget)
            i = _get_index(child_self, widget)
            child_self.insert(i + 1, mgui)

    elif popup_mode == PopUpMode.dock:
        from .class_gui import MainWindowClassGui

        def _prep(mgui: FunctionGui):

            parent_self = self._search_parent_magicclass()
            viewer = parent_self.parent_viewer
            if viewer is None:
                if isinstance(parent_self, MainWindowClassGui):
                    parent_self.add_dock_widget(mgui)
                else:
                    msg = (
                        "Cannot add dock widget to a normal container. Please use\n"
                        ">>> @magicclass(widget_type='mainwindow')\n"
                        "to create main window widget, or add the container as a dock "
                        "widget in napari."
                    )
                    warnings.warn(msg, UserWarning)

            else:
                viewer.window.add_dock_widget(
                    mgui, name=_get_widget_name(widget), area="right"
                )

    elif popup_mode == PopUpMode.parentsub:

        def _prep(mgui: FunctionGui):
            from .class_gui import find_window_ancestor

            parent_self = find_window_ancestor(self)
            parent_self._widget._mdiarea.addSubWindow(mgui.native)

    elif popup_mode == PopUpMode.dialog:

        def _prep(mgui: FunctionGui):
            mgui.call_button.visible = False

    else:
        raise RuntimeError(popup_mode)
    return _prep


def _implement_confirmation(
    method: MethodType,
    self: BaseGui,
    text: str,
    condition: Callable[[BaseGui], bool] | str,
    callback: Callable[[str, BaseGui], None],
):
    """Implement confirmation callback to a method."""
    sig = inspect.signature(method)

    @wraps(method)
    def _method(*args, **kwargs):
        if self[method.__name__].running:
            arguments = sig.bind(*args, **kwargs)
            arguments.apply_defaults()
            all_args = arguments.arguments
            all_args.update(self=self)
            need_confirmation = False
            if isinstance(condition, str):
                try:
                    need_confirmation = eval(condition, {}, all_args)
                except Exception as e:
                    msg = e.args[0]
                    e.args = (
                        f"Exception happened on evaluating condition {condition!r}.\n"
                        f"{type(e).__name__}: {msg}"
                    )
                    raise e
            elif callable(condition):
                need_confirmation = condition(self)
            else:
                warnings.warn(
                    f"Condition {condition} should be callable or string but got type "
                    f"{type(condition)}. No confirmation was executed.",
                    UserWarning,
                )
            if need_confirmation:
                callback(text.format(**all_args), self)

        return method(*args, **kwargs)

    if hasattr(method, "__signature__"):
        _method.__signature__ = method.__signature__

    return _method


def _cleanup_tb(tb: TracebackType):
    """Remove useless info from a traceback object."""
    current_tb = tb
    while current_tb is not None:
        if current_tb.tb_frame.f_code.co_name == "_recordable":
            tb = current_tb.tb_next
            break
        current_tb = current_tb.tb_next
    return tb


def _empty_func(name: str) -> Callable[[Any], None]:
    """Create a named function that does nothing."""
    f = lambda x: None
    f.__name__ = name
    return f
