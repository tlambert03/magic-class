from __future__ import annotations
import functools
from typing import Any, TYPE_CHECKING
from types import MethodType
import inspect
from magicgui.widgets import EmptyWidget
from ..signature import get_signature, upgrade_signature

if TYPE_CHECKING:
    from ..signature import MagicMethodSignature

_PARTIALIZE = {"gui_only": True, "widget_type": EmptyWidget, "visible": False}


class partial(functools.partial):
    """
    Partialize a function and its signature.

    This object is similar to ``functools.partial``, but it also update
    widget options to build magicgui widget with subset of widgets. More
    precisely, partializing ``x=0`` will add option
    ``x={"gui_only": True, "widget_type": EmptyWidget, "visible": False}``.

    Parameters
    ----------
    func : Callable
        Callable object to be partialized.

    Examples
    --------
    Suppose you have a magic class.

    >>> @magicclass
    >>> class A:
    >>>     def f(self, i: int): ...

    You can partialize method ``f``.

    >>> ui = A()
    >>> ui.append(partial(ui.f, i=1))
    """

    __signature__: MagicMethodSignature

    def __new__(cls, func, /, *args, **kwargs):
        # prepare widget options
        options: dict[str, Any] = {}
        bound = inspect.signature(func).bind_partial(*args, **kwargs)
        for name in bound.arguments.keys():
            options[name] = _PARTIALIZE

        # unwrap function if it is a method
        if isinstance(func, MethodType):
            _func = _unwrap_method(func)
            options["self"] = {"bind": func.__self__, "widget_type": EmptyWidget}
        else:
            _func = func

        # construct partial object
        self = functools.partial.__new__(cls, _func, *args, **kwargs)
        self.__signature__ = get_signature(self)
        self.__name__ = _func.__name__

        upgrade_signature(self, gui_options=options)
        return self

    def set_options(
        self,
        text: str | None = None,
        **kwargs,
    ):
        """Set options for the buttons or actions."""
        kwargs.update(text=text)
        upgrade_signature(self, caller_options=kwargs)
        return self


class partialmethod(functools.partialmethod):
    """
    Partialize a method and its signature.

    This object is similar to ``functools.partialmethod``, but it also update
    widget options to build magicgui widget with subset of widgets. More
    precisely, partializing ``x=0`` will add option
    ``x={"gui_only": True, "widget_type": EmptyWidget, "visible": False}``.

    Parameters
    ----------
    func : Callable
        Callable object to be partialized.

    Examples
    --------

    >>> @magicclass
    >>> class A:
    >>>     def f(self, i: int): ...
    >>>     g = partialmethod(f, i=1)

    """

    __signature__: MagicMethodSignature

    def __init__(self, func, /, *args, **kwargs):
        # prepare widget options
        options: dict[str, Any] = {}
        bound = inspect.signature(func).bind_partial(*args, **kwargs)
        for name in bound.arguments.keys():
            options[name] = _PARTIALIZE

        # unwrap function if it is a method
        if isinstance(func, MethodType):
            _func = _unwrap_method(func)
            options["self"] = {"bind": func.__self__, "widget_type": EmptyWidget}
        else:
            _func = func

        # construct partial object
        super().__init__(_func, *args, **kwargs)
        self.__signature__ = get_signature(partial(_func, *args, **kwargs))
        self.__name__ = _func.__name__

        upgrade_signature(self, gui_options=options)

    def __call__(self, *args: Any, **kwargs: Any):
        # needed to be defined because magicclass checks callable
        raise TypeError("partialmethod object is not callable")

    def __set_name__(self, owner, name):
        self.__signature__.caller_options.setdefault("text", name.replace("_", " "))

    def set_options(
        self,
        text: str | None = None,
        **kwargs,
    ):
        """Set options for the buttons or actions."""
        kwargs.update(text=text)
        upgrade_signature(self, caller_options=kwargs)
        return self


def _unwrap_method(func: MethodType):
    def _unwrapped(*args, **kwargs):
        return func(*args, **kwargs)

    _unwrapped.__name__ = func.__name__
    _unwrapped.__qualname__ = func.__qualname__
    _unwrapped.__annotations__ = func.__annotations__
    _unwrapped.__module__ = func.__module__
    _unwrapped.__doc__ = func.__doc__
    _unwrapped.__signature__ = get_signature(func)
    return _unwrapped
