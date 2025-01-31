from __future__ import annotations
from enum import Enum
import typing
from typing import (
    Any,
    Union,
    Iterable,
    overload,
    TypeVar,
    Callable,
    Literal,
)
from typing_extensions import Annotated, _AnnotatedAlias
from magicgui.widgets import Widget, EmptyWidget

from .fields import MagicField
from .signature import split_annotated_type

try:
    from typing import _tp_cache
except ImportError:
    _tp_cache = lambda x: x

__all__ = [
    "WidgetType",
    "bound",
    "Bound",
    "Choices",
    "OneOf",
    "SomeOf",
    "Optional",
    "Union",
]


class WidgetType(Enum):
    none = "none"
    scrollable = "scrollable"
    draggable = "draggable"
    split = "split"
    collapsible = "collapsible"
    hcollapsible = "hcollapsible"
    button = "button"
    toolbox = "toolbox"
    tabbed = "tabbed"
    stacked = "stacked"
    list = "list"
    subwindows = "subwindows"
    groupbox = "groupbox"
    frame = "frame"
    mainwindow = "mainwindow"


WidgetTypeStr = Literal[
    "none",
    "scrollable",
    "draggable",
    "split",
    "collapsible",
    "button",
    "toolbox",
    "tabbed",
    "stacked",
    "list",
    "subwindows",
    "groupbox",
    "frame",
    "mainwindow",
    "hcollapsible",
]


PopUpModeStr = Literal[
    "popup",
    "first",
    "last",
    "above",
    "below",
    "dock",
    "dialog",
    "parentlast",
]


ErrorModeStr = Literal["msgbox", "stderr", "stdout"]

Color = Union[Iterable[float], str]


_W = TypeVar("_W", bound=Widget)
_V = TypeVar("_V", bound=object)

# fmt: off
@overload
def bound(obj: Callable[[_W], _V]) -> type[_V]: ...
@overload
def bound(obj: Callable[[Any, _W], _V]) -> type[_V]: ...
@overload
def bound(obj: MagicField[_W, _V]) -> type[_V]: ...
@overload
def bound(obj: type[_W]) -> type: ...
# fmt: on


def bound(obj):
    """Function version of ``Bound[...]``."""
    # NOTE: This could be more useful than Bound??
    if callable(obj):
        outtype = obj.__annotations__.get("return", Any)
    elif isinstance(obj, MagicField):
        outtype = obj.annotation or Any
    elif isinstance(obj, (type, str)):
        outtype = Any
    else:
        raise TypeError("'bound' can only convert callable, MagicField or type objects")
    while isinstance(outtype, _AnnotatedAlias):
        outtype, _ = split_annotated_type(outtype)
    if isinstance(obj, str):
        obj = BoundLiteral(obj)
    return Annotated[outtype, {"bind": obj, "widget_type": EmptyWidget}]


class BoundLiteral:
    """
    A class used to represent a future evaluable expression.

    This object will be created when a string is passed to the ``Bound[...]`` type.
    """

    def __init__(self, expr: str):
        self._expr = expr

    def eval(self, cls: type) -> Any:
        from .utils import eval_attribute

        return eval_attribute(cls, self._expr)


class _BoundAlias(type):
    """
    This metaclass is necessary for ``mypy`` to reveal type.

    For instance, if type annotation is added like this

    >>> def _get_int(self, _=None) -> int:
    >>>     return 0

    >>> def func(self, x: Bound[_get_int]):
    >>>     # do something

    ``x`` will be considered to be ``Bound`` type otherwise.
    """

    @overload
    def __getitem__(cls, value: MagicField[_W, _V]) -> type[_V]:
        ...

    @overload
    def __getitem__(cls, value: Callable[..., _V]) -> type[_V]:
        ...

    @overload
    def __getitem__(cls, value: type[_V]) -> type[_V]:
        ...

    @_tp_cache
    def __getitem__(cls, value):
        if isinstance(value, tuple):
            raise TypeError(
                "Bound[...] should be used with only one "
                "argument (the object to be bound)."
            )
        return bound(value)


class Bound(metaclass=_BoundAlias):
    """
    Make Annotated type from a MagicField or a method, such as:

    >>> from magicclass import magicclass, field
    >>> @magicclass
    >>> class MyClass:
    >>>     i = field(int)
    >>>     def func(self, v: Bound[i]):
    >>>         ...

    ``Bound[value]`` is identical to ``Annotated[Any, {"bind": value}]``.
    """

    def __new__(cls, *args):
        raise TypeError(
            "`Bound(...)` is deprecated since 0.5.21. Bound is now a generic alias instead "
            "of a function. Please use `Bound[...]`."
        )

    def __init_subclass__(cls, *args, **kwargs):
        raise TypeError(f"Cannot subclass {cls.__module__}.Bound")


class _OneOfAlias(type):
    """metaclass of ``OneOf``."""

    @overload
    def __getitem__(cls, value: Callable[..., Iterable[tuple[Any, _V]]]) -> type[_V]:
        ...

    @overload
    def __getitem__(cls, value: Callable[..., Iterable[_V]]) -> type[_V]:
        ...

    @overload
    def __getitem__(cls, value: Iterable[tuple[Any, _V]]) -> type[_V]:
        ...

    @overload
    def __getitem__(cls, value: Iterable[_V]) -> type[_V]:
        ...

    @overload
    def __getitem__(cls, value: slice) -> type[int | float]:
        ...

    @_tp_cache
    def __getitem__(cls, value):
        if callable(value):
            outtype = value.__annotations__.get("return", Any)
        elif hasattr(value, "__iter__"):
            outtype = Any
        elif isinstance(value, slice):
            outtype, value = _normalize_slice(value)
        else:
            raise TypeError("'bound' can only convert callable or iterable objects.")
        return Annotated[outtype, {"choices": value, "nullable": False}]


def _normalize_slice(value: slice) -> type | list:
    start, stop, step = value.start or 0, value.stop or 0, value.step or 1
    if float in [type(start), type(stop), type(step)]:
        import math

        ndigits = -int(min(math.log10(start), math.log10(stop), math.log10(step))) + 4
        outtype = float
        outvalue: list[float] = []
        if step > 0:
            x = start
            while x < stop:
                outvalue.append(x)
                x = round(x + step, ndigits)
        else:
            x = stop
            while start < x:
                outvalue.append(x)
                x = round(x + step, ndigits)

    else:
        outtype = int
        outvalue = list(range(start, stop, step))
    return outtype, outvalue


class OneOf(metaclass=_OneOfAlias):
    """
    Make Annotated type from a method, such as:

    >>> from magicclass import magicclass
    >>> @magicclass
    >>> class MyClass:
    >>>     def func(self, v: OneOf[(1, 2, 3)]):
    >>>         ...

    ``OneOf[value]`` is identical to ``Annotated[Any, {"choices": value}]``.
    """

    def __new__(cls, *args):
        raise TypeError(
            "`Bound(...)` is deprecated since 0.5.21. Bound is now a generic alias instead "
            "of a function. Please use `Bound[...]`."
        )

    def __init_subclass__(cls, *args, **kwargs):
        raise TypeError(f"Cannot subclass {cls.__module__}.{cls.__name__}")


Choices = OneOf  # alias


class _SomeOfAlias(type):
    """This metaclass is necessary for ``mypy`` to reveal type."""

    @overload
    def __getitem__(
        cls, value: Callable[..., Iterable[tuple[Any, _V]]]
    ) -> type[list[_V]]:
        ...

    @overload
    def __getitem__(cls, value: Callable[..., Iterable[_V]]) -> type[list[_V]]:
        ...

    @overload
    def __getitem__(cls, value: Iterable[tuple[Any, _V]]) -> type[list[_V]]:
        ...

    @overload
    def __getitem__(cls, value: Iterable[_V]) -> type[list[_V]]:
        ...

    @overload
    def __getitem__(cls, value: slice) -> type[int | float]:
        ...

    @_tp_cache
    def __getitem__(cls, value):
        if callable(value):
            outtype = value.__annotations__.get("return", Any)
        elif hasattr(value, "__iter__"):
            outtype = Any
        elif isinstance(value, slice):
            outtype, value = _normalize_slice(value)
        else:
            raise TypeError("'bound' can only convert callable or iterable objects.")
        return Annotated[
            outtype, {"choices": value, "nullable": False, "widget_type": "Select"}
        ]


class SomeOf(metaclass=_SomeOfAlias):
    """
    Make Annotated type from a method, such as:

    >>> from magicclass import magicclass

    >>> @magicclass
    >>> class MyClass:
    >>>     def func(self, v: Choices[(1, 2, 3)]):
    >>>         ...

    ``Choices[value]`` is identical to ``Annotated[Any, {"choices": value}]``.
    """

    def __new__(cls, *args):
        raise TypeError(
            "`Bound(...)` is deprecated since 0.5.21. Bound is now a generic alias instead "
            "of a function. Please use `Bound[...]`."
        )

    def __init_subclass__(cls, *args, **kwargs):
        raise TypeError(f"Cannot subclass {cls.__module__}.SomeOf")


_T = TypeVar("_T")


class _OptionalAlias(type):
    @overload
    def __getitem__(cls, value: type[_T]) -> type[typing.Optional[_T]]:
        ...

    @overload
    def __getitem__(
        cls, value: tuple[type[_T], dict[str, Any]]
    ) -> type[typing.Optional[_T]]:
        ...

    def __getitem__(cls, value):
        if not isinstance(value, (type, typing._GenericAlias)):
            raise TypeError(
                "The first argument of Optional must be a type but "
                f"got {type(value)}."
            )
        from .widgets import OptionalWidget

        opt = dict(widget_type=OptionalWidget)
        if isinstance(value, _AnnotatedAlias):
            type0, opt0 = split_annotated_type(value)
            type_ = typing.Optional[type0]
            opt.update(annotation=type_, options=opt0)
            return Annotated[type_, opt]
        else:
            opt.update(annotation=typing.Optional[value])
            return Annotated[typing.Optional[value], opt]


class Optional(metaclass=_OptionalAlias):
    """
    Make Annotated type similar to ``typing.Optional``.

    Arguments annotated with ``Optional[int]`` will create a
    ``OptionalWidget`` with a ``SpinBox`` as an inner widget.

    >>> from magicclass import magicclass, set_options
    >>> from magicclass.types import Optional

    >>> @magicclass
    >>> class A:
    >>>     @set_options(a={"options": {"min": -1}})
    >>>     def f(self, a: Optional[int]):
    >>>         print(a)

    >>> ui = A()
    >>> ui.show()
    """

    def __new__(cls, *args, **kwargs):
        raise TypeError("Type Optional cannot be instantiated.")

    def __init_subclass__(cls, *args, **kwargs):
        raise TypeError(f"Cannot subclass {cls.__module__}.Optional.")


class _UnionAlias(type):
    def __getitem__(cls, value):
        from .functools._dispatch import UnionWidget

        annotations = []
        opt = dict(widget_type=UnionWidget, nullable=False, annotations=annotations)
        for val in value:
            if val is not None:
                annotations.append(val)
            else:
                opt["nullable"] = True
        # union = Union[tuple(annotations)]  # type: ignore
        return Annotated[Any, opt]


class Union(metaclass=_UnionAlias):
    """
    Make Annotated type similar to ``typing.Union``.

    Arguments annotated with ``Union[int, str]`` will create a
    ``UnionWidget`` with a ``SpinBox`` and a ``LineEdit`` as inner widgets.

    >>> from magicclass import magicclass
    >>> from magicclass.types import Union

    >>> @magicclass
    >>> class A:
    >>>     def f(self, a: Union[int, str]):
    >>>         print(a)

    >>> ui = A()
    >>> ui.show()
    """

    def __new__(cls, *args, **kwargs):
        raise TypeError("Type Union cannot be instantiated.")

    def __init_subclass__(cls, *args, **kwargs):
        raise TypeError(f"Cannot subclass {cls.__module__}.Union.")


def __getattr__(key: str):
    if key in ["List", "Tuple"]:
        import warnings

        warnings.warn(
            f"Type {key!r} is deprecated. Please use typing.{key}.",
            DeprecationWarning,
            stacklevel=2,
        )
        import typing

        return getattr(typing, key)
    raise AttributeError(f"module {__name__!r} has no attribute {key!r}")
