from __future__ import annotations
from typing import (
    Any,
    TYPE_CHECKING,
    Callable,
    TypeVar,
    overload,
    Generic,
    Union,
)
from typing_extensions import Literal, _AnnotatedAlias
from pathlib import Path
import datetime
import sys
from enum import Enum
from magicgui.widgets import create_widget
from magicgui.widgets._bases import Widget, ValueWidget, ContainerWidget
from magicgui.widgets._bases.value_widget import UNSET

from ._define import define_callback, define_callback_gui

from ..utils import (
    is_instance_method,
    method_as_getter,
    eval_attribute,
)
from .._gui.mgui_ext import Action, WidgetAction

if TYPE_CHECKING:
    from magicgui.widgets._protocols import WidgetProtocol
    from typing_extensions import Self
    from .._gui._base import MagicTemplate
    from .._gui.mgui_ext import AbstractAction

    _M = TypeVar("_M", bound=MagicTemplate)

if sys.version_info >= (3, 10):
    from typing import _BaseGenericAlias
else:
    from typing_extensions import _BaseGenericAlias


class _FieldObject:
    name: str
    tooltip: str

    def get_widget(self, obj: Any) -> Widget:
        raise NotImplementedError()


_W = TypeVar("_W", bound=Widget)
_V = TypeVar("_V", bound=object)


class MagicField(_FieldObject, Generic[_W, _V]):
    """
    Field class for magicgui construction.

    This object is compatible with dataclass. MagicField object is in "ready for
    widget construction" state.
    """

    default_object = object()

    def __init__(
        self,
        value: Any = UNSET,
        name: str | None = None,
        label: str | None = None,
        annotation: Any = None,
        widget_type: type | str | None = None,
        options: dict[str, Any] | None = None,
        record: bool = True,
        constructor: Callable[..., Widget] | None = None,
    ):
        if options is None:
            options = {}
        if value is UNSET:
            value = options.pop("value", UNSET)

        if constructor is None:

            def _create_widget(obj):
                return create_widget(
                    self.value,
                    name=self.name,
                    label=self.label,
                    annotation=self.annotation,
                    widget_type=self.widget_type,
                    options=self.options,
                )

            constructor = _create_widget

        self.value = value
        self.name = name
        self.label = label
        self.annotation = annotation
        self.options = options
        self._widget_type = widget_type
        self._constructor = constructor
        self._callbacks: list[Callable] = []
        self._guis: dict[int, _M] = {}
        self._record = record

        # MagicField has to remenber the first class that referred to itself so
        # that it can "know" the namespace it belongs to.
        self._parent_class: type | None = None

    def __repr__(self):
        attrs = ["value", "name", "widget_type", "record", "options"]
        kw = ", ".join(f"{a}={getattr(self, a)!r}" for a in attrs)
        return f"{self.__class__.__name__}({kw})"

    def __set_name__(self, owner: type, name: str) -> None:
        self._parent_class = owner
        if self.name is None:
            self.name = name

    @property
    def constructor(self) -> Callable[..., Widget]:
        """Get widget constructor."""
        return self._constructor

    @property
    def callbacks(self) -> tuple[Callable, ...]:
        """Return callbacks in an immutable way."""
        return tuple(self._callbacks)

    @property
    def record(self) -> bool:
        return self._record

    def construct(self, obj) -> _W:
        """Construct a widget."""
        constructor = self.constructor
        _arg_choices = self.options.get("choices", None)
        if isinstance(_arg_choices, str):
            _arg_choices = eval_attribute(type(obj), _arg_choices)

        if is_instance_method(_arg_choices):
            self.options["choices"] = method_as_getter(obj, _arg_choices)
        try:
            if _is_subclass(constructor, Widget):
                widget = constructor(**self.options)
            else:
                widget = constructor(obj)
                if not isinstance(widget, Widget):
                    raise TypeError(
                        f"{self.__class__.__name__} {self.name} created non-widget "
                        f"object {type(widget)}."
                    )

        finally:
            if _arg_choices is not None:
                self.options["choices"] = _arg_choices

        return widget

    def copy(self) -> Self[_W, _V]:
        """Copy object."""
        return self.__class__(
            value=self.value,
            name=self.name,
            label=self.label,
            annotation=self.annotation,
            widget_type=self.widget_type,
            options=self.options,
            record=self.record,
            constructor=self.constructor,
        )

    @classmethod
    def from_callable(cls, func: Callable[..., _W]) -> Self[_W, Any]:
        """Use a function as the constructor of MagicField."""
        return cls(constructor=func)

    def get_widget(self, obj: Any) -> _W:
        """
        Get a widget from ``obj``. This function will be called every time MagicField is referred
        by ``obj.field``.
        """
        from .._gui import MagicTemplate

        obj_id = id(obj)
        if (widget := self._guis.get(obj_id, None)) is None:
            self._guis[obj_id] = widget = self.construct(obj)
            widget.name = self.name

            if isinstance(widget, (ValueWidget, ContainerWidget)):
                if isinstance(obj, MagicTemplate):
                    _def = define_callback_gui
                else:
                    _def = define_callback
                for callback in self._callbacks:
                    # funcname = callback.__name__
                    widget.changed.connect(_def(obj, callback))

        return widget

    def get_action(self, obj: Any) -> AbstractAction:
        """
        Get an action from ``obj``. This function will be called every time MagicField is referred
        by ``obj.field``.
        """
        from .._gui import MagicTemplate

        obj_id = id(obj)
        if obj_id in self._guis.keys():
            action = self._guis[obj_id]
        else:
            if type(self.value) is bool or self.annotation is bool:
                # we should not use "isinstance" or "issubclass" because subclass
                # may be mapped to different widget by users.
                value = False if self.value is UNSET else self.value
                action = Action(
                    checkable=True,
                    checked=value,
                    text=self.name.replace("_", " "),
                    name=self.name,
                )
                for k, v in self.options.items():
                    setattr(action, k, v)
            else:
                widget = self.construct(obj)
                widget.name = self.name
                action = WidgetAction(widget)

            self._guis[obj_id] = action

            if action.support_value:
                if isinstance(obj, MagicTemplate):
                    _def = define_callback_gui
                else:
                    _def = define_callback
                for callback in self._callbacks:
                    # funcname = callback.__name__
                    action.changed.connect(_def(obj, callback))

        return action

    def as_getter(self, obj: Any) -> Callable[[Any], _V]:
        """Make a function that get the value of Widget or Action."""
        return lambda w: self._guis[id(obj)].value

    def as_remote_getter(self, obj: Any):
        """Called when a MagicField is used in Bound method."""
        qualname = self._parent_class.__qualname__
        _LOCALS = "<locals>."
        if _LOCALS in qualname:
            qualname = qualname.split(_LOCALS)[-1]
        clsnames = qualname.split(".")

        def _func(w):
            # First we have to know where (which instance) MagicField came from.
            if obj.__class__.__name__ not in clsnames:
                ns = ".".join(clsnames)
                raise ValueError(
                    f"Method {self.name!r} is in namespace {ns!r}, so it is invisible "
                    f"from magicclass {obj.__class__.__qualname__!r}."
                )
            i = clsnames.index(type(obj).__name__) + 1
            ins = obj
            for clsname in clsnames[i:]:
                ins = getattr(ins, clsname, ins)

            # Now, ins is an instance of parent class.
            # Extract correct widget from MagicField
            _field_widget = self.get_widget(ins)
            if not hasattr(_field_widget, "value"):
                raise TypeError(
                    f"MagicField {self.name} does not return ValueWidget "
                    "thus cannot be used as a bound value."
                )
            return self.as_getter(ins)(w)

        return _func

    @overload
    def __get__(self, obj: Literal[None], objtype=None) -> MagicField[_W, _V]:
        ...

    @overload
    def __get__(self, obj: Any, objtype=None) -> _W:
        ...

    def __get__(self, obj, objtype=None):
        """Get widget for the object."""
        if obj is None:
            return self
        return self.get_widget(obj)

    def __set__(self, obj, value) -> None:
        raise AttributeError(f"Cannot set value to {self.__class__.__name__}.")

    def ready(self) -> bool:
        """Return true if field is ready to create widgets."""
        return not self.not_ready()

    def not_ready(self) -> bool:
        return (
            self.value is UNSET
            and self.annotation is None
            and self.widget_type is None
            and "choices" not in self.options
        )

    def to_widget(self) -> _W:
        """
        Create a widget from the field.

        Returns
        -------
        Widget
            Widget object that is ready to be inserted into Container.

        Raises
        ------
        ValueError
            If there is not enough information to build a widget.
        """
        return self.get_widget(self.default_object)

    def to_action(self) -> Action | WidgetAction[_W]:
        """
        Create a menu action or a menu widget action from the field.

        Returns
        -------
        Action or WidgetAction
            Object that can be added to menu.

        Raises
        ------
        ValueError
            If there is not enough information to build an action.
        """
        return self.get_action(self.default_object)

    def connect(self, func: Callable) -> Callable:
        """Set callback function to "ready to connect" state."""
        if not callable(func):
            raise TypeError("Cannot connect non-callable object")
        self._callbacks.append(func)
        return func

    def disconnect(self, func: Callable) -> None:
        """
        Disconnect callback from the field.
        This method does NOT disconnect callbacks from widgets that are
        already created.
        """
        i = self._callbacks.index(func)
        self._callbacks.pop(i)
        return None

    def wraps(
        self,
        method: Callable | None = None,
        *,
        template: Callable | None = None,
        copy: bool = False,
    ):
        """
        Call the ``wraps`` class method of magic class.

        This method is needed when a child magic class is defined outside the main magic
        class, and integrated into the main magic class by ``field`` function, like below

        .. code-block:: python

            @magicclass
            class B:
                def func(self): ...  # pre-definition

            @magicclass
            class A:
                b = field(B)

                @b.wraps
                def func(self):
                    # do something

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
        from .._gui import BaseGui

        cls = self.constructor
        if not (isinstance(cls, type) and issubclass(cls, BaseGui)):
            raise TypeError(
                "The wraps method cannot be used for any objects but magic class."
            )
        return cls.wraps(method=method, template=template, copy=copy)

    @property
    def tooltip(self) -> str:
        """Get tooltip of returned widgets."""
        return self.options.get("tooltip", "")

    @tooltip.setter
    def tooltip(self, value):
        self.options.update(tooltip=value)

    @property
    def enabled(self) -> bool:
        """Get interactivity of returned widgets."""
        return self.options.get("enabled", True)

    @enabled.setter
    def enabled(self, value: bool):
        self.options.update(enabled=value)

    @property
    def visible(self) -> bool:
        """Get visibility of returned widgets."""
        return self.options.get("visible", True)

    @visible.setter
    def visible(self, value: bool):
        self.options.update(visible=value)

    @property
    def widget_type(self) -> type[Widget]:
        """Return type of the resulting widget."""
        return self._widget_type


class MagicValueField(MagicField[_W, _V]):
    """
    Field class for magicgui construction. Unlike MagicField, object of this class
    always returns value itself.
    """

    @overload
    def __get__(self, obj: Literal[None], objtype=None) -> MagicValueField[_W, _V] | _V:
        ...

    @overload
    def __get__(self, obj: Any, objtype=None) -> _V:
        ...

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return self._postgethook(obj, self.get_widget(obj).value)

    def __set__(self, obj: _M, value: _V) -> None:
        if obj is None:
            raise AttributeError(f"Cannot set {self.__class__.__name__}.")
        self.get_widget(obj).value = self._presethook(obj, value)

    def post_get_hook(self, hook: Callable[[Any, _V], Any] | Callable[[_V], Any]):
        """
        Define a post-get hook for the field.

        If a post-get hook is set, value will always be converted before returned.
        Following example shows how to convert ``x`` to a float every time it gets
        accessed.

        >>> class A:
        >>>     x = vfield(int)
        >>>     @x.post_get_hook
        >>>     def _x_get(self, value):
        >>>         return float(int)

        Parameters
        ----------
        hook : callable
            Post-get hook function.
        """
        if not callable(hook):
            raise TypeError("Post-get hook must be callable.")
        if is_instance_method(hook):
            self._postgethook = hook
        else:
            self._postgethook = lambda _, x: hook(x)
        return hook

    def pre_set_hook(self, hook: Callable[[Any, Any], _V] | Callable[[Any], _V]):
        """
        Define a pre-set hook for the field.

        If a pre-set hook is set, value will always be converted before being set
        to the widget value. Following example shows how to convert ``x`` to a
        string before setting the value

        >>> class A:
        >>>     x = vfield(str)
        >>>     @x.pre_set_hook
        >>>     def _x_set(self, value):
        >>>         return str(value)

        Parameters
        ----------
        hook : callable
            Pre-set hook function.
        """
        if not callable(hook):
            raise TypeError("Pre-set hook must be callable.")
        if is_instance_method(hook):
            self._presethook = hook
        else:
            self._presethook = lambda _, x: hook(x)
        return hook

    def _postgethook(self, obj, value):
        return value

    def _presethook(self, obj, value):
        return value


# magicgui symple types
_X = TypeVar(
    "_X",
    bound=Union[
        int,
        float,
        bool,
        str,
        Path,
        datetime.datetime,
        datetime.date,
        datetime.time,
        Enum,
        range,
        slice,
        list,
        tuple,
    ],
)


@overload
def field(
    obj: _X,
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicField[ValueWidget, _X]:
    ...


@overload
def field(
    widget_type: type[_W],
    *,
    name: str | None = None,
    label: str | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicField[_W, Any]:
    ...


@overload
def field(
    obj: type[_X],
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicField[ValueWidget, _X]:
    ...


@overload
def field(
    gui_class: type[_M],
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicField[_M, Any]:
    ...


@overload
def field(
    obj: Any,
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: type[_W] = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicField[_W, Any]:
    ...


@overload
def field(
    obj: Any,
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: str | type[WidgetProtocol] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicField[Widget, Any]:
    ...


def field(
    obj: Any = UNSET,
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: str | type[WidgetProtocol] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicField[Widget, Any]:
    """
    Make a MagicField object.

    >>> i = field(1)
    >>> i = field(widget_type="Slider")

    Parameters
    ----------
    obj : Any, default is UNSET
        Reference to determine what type of widget will be created. If Widget
        subclass is given, it will be used as is. If other type of class is given,
        it will used as type annotation. If an object (not type) is given, it will
        be assumed to be the default value.
    name : str, optional
        Name of the widget.
    label : str, optional
        Label of the widget.
    widget_type : str, optional
        Widget type. This argument will be sent to ``create_widget`` function.
    options : WidgetOptions, optional
        Widget options. This parameter will be passed to the ``options`` keyword
        argument of ``create_widget``.
    record : bool, default is True
        A magic-class specific parameter. If true, record value changes as macro.

    Returns
    -------
    MagicField
    """
    return _get_field(obj, name, label, widget_type, options, record, MagicField)


@overload
def vfield(
    obj: _X,
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicValueField[ValueWidget, _X]:
    ...


@overload
def vfield(
    widget_type: type[_W],
    *,
    name: str | None = None,
    label: str | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicValueField[_W, Any]:
    ...


@overload
def vfield(
    annotation: type[_X],
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicValueField[ValueWidget, _X]:
    ...


@overload
def vfield(
    obj: Any,
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: type[_W] = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicValueField[_W, Any]:
    ...


@overload
def vfield(
    obj: Any,
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: str | type[WidgetProtocol] | type[Widget] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicValueField[Widget, Any]:
    ...


def vfield(
    obj: Any = UNSET,
    *,
    name: str | None = None,
    label: str | None = None,
    widget_type: str | type[WidgetProtocol] | None = None,
    options: dict[str, Any] = {},
    record: bool = True,
) -> MagicValueField[Widget, Any]:
    """
    Make a MagicValueField object.

    >>> i = vfield(1)
    >>> i = vfield(widget_type="Slider")

    Unlike MagicField, value itself can be accessed.

    >>> ui.i      # int is returned
    >>> ui.i = 3  # set value to the widget.

    Parameters
    ----------
    obj : Any, default is UNSET
        Reference to determine what type of widget will be created. If Widget
        subclass is given, it will be used as is. If other type of class is given,
        it will used as type annotation. If an object (not type) is given, it will
        be assumed to be the default value.
    name : str, optional
        Name of the widget.
    label : str, optional
        Label of the widget.
    widget_type : str, optional
        Widget type. This argument will be sent to ``create_widget`` function.
    options : WidgetOptions, optional
        Widget options. This parameter will be passed to the ``options`` keyword
        argument of ``create_widget``.
    record : bool, default is True
        A magic-class specific parameter. If true, record value changes as macro.

    Returns
    -------
    MagicValueField
    """
    return _get_field(obj, name, label, widget_type, options, record, MagicValueField)


def widget_property(func: Callable[..., _W]) -> MagicValueField[_W, Any]:
    """
    Create a widget property from a function.

    Generally, this decorator will be used in line with ``HasFields`` trait.
    If a widget has to be initialized depending on the state of the instance,
    you can define a field using a method.

    >>> class A(HasFields):
    >>>     def __init__(self, max: int = 10):
    >>>         self._max = max
    >>>     @widget_property
    >>>     def param(self):
    >>>         return SpinBox(value=1, max=self._max)

    In this example, ``param`` is a field object similar to those defined using
    ``vfield`` but has a variable argument ``max``.

    >>> a = A(max=20)
    >>> a.param  # Out: 1
    >>> a.param = 4  # OK
    >>> a.widgets.param  # SpinBox with value=1 and max=20

    Parameters
    ----------
    func : callable
        Widget constructor function.

    Returns
    -------
    MagicValueField
        A field with given constructor.
    """
    return MagicValueField.from_callable(func)


def _get_field(
    obj,
    name: str,
    label: str,
    widget_type: str | type[WidgetProtocol] | None,
    options: dict[str, Any],
    record: bool,
    field_class: type[MagicField],
) -> MagicField:
    if not isinstance(options, dict):
        raise TypeError(f"Field options must be a dict, got {type(options)}")
    options = options.copy()
    kwargs = dict(
        name=name, label=label, record=record, annotation=None, options=options
    )
    if isinstance(obj, (type, _BaseGenericAlias)):
        if isinstance(obj, _AnnotatedAlias):
            from ..signature import split_annotated_type

            tp, widget_option = split_annotated_type(obj)
            kwargs.update(annotation=tp)
            options.update(**widget_option)
        if _is_subclass(obj, Widget):
            if widget_type is not None:
                raise ValueError("Cannot specify Widget type twice.")
            f = field_class(constructor=obj, widget_type=obj, **kwargs)
        else:
            if kwargs["annotation"] is None:
                kwargs.update(annotation=obj)
            f = field_class(widget_type=widget_type, **kwargs)
    elif obj is UNSET:
        f = field_class(widget_type=widget_type, **kwargs)
    else:
        f = field_class(value=obj, widget_type=widget_type, **kwargs)

    return f


def _is_subclass(obj: Any, class_or_tuple):
    try:
        return issubclass(obj, class_or_tuple)
    except Exception:
        return False
