from __future__ import annotations
import inspect
from dataclasses import is_dataclass, _POST_INIT_NAME
from .class_gui import ClassGui
from .widgets import Separator
from .utils import check_collision, get_app, current_location, inline

_BASE_CLASS_SUFFIX = "_Base"

def magicclass(cls:type|None=None, *, layout:str="vertical", parent=None, close_on_run:bool=True,
               popup:bool=True, result_widget:bool=False):
    """
    Decorator that can convert a Python class into a widget with push buttons.
    
    >>> @magicclass
    >>> class C:
    >>>     ...
    >>> c = C(a=0)
    >>> c.show()
            
    Parameters
    ----------
    cls : type, optional
        Class to be decorated.
    layout : str, "vertical" or "horizontal", default is "vertical"
        Layout of the main widget.
    parent : magicgui.widgets._base.Widget, optional
        Parent widget if exists.
    close_on_run : bool, default is True
        If True, magicgui created by every method will be deleted after the method is completed without
        exceptions, i.e. magicgui is more like a dialog.
    popup : bool, default is True
        If True, magicgui created by every method will be poped up, else they will be appended as a
        part of the main widget.
    
    Returns
    -------
    Decorated class or decorator.
    """    
    def wrapper(cls):
        if not isinstance(cls, type):
            raise TypeError(f"magicclass can only wrap classes, not {type(cls)}")
        
        check_collision(cls, ClassGui)
        doc = cls.__doc__
        sig = inspect.signature(cls)
        oldclass = type(cls.__name__ + _BASE_CLASS_SUFFIX, (cls,), {})
        newclass = type(cls.__name__, (ClassGui, oldclass), {})
        newclass.__signature__ = sig
        newclass.__doc__ = doc
        
        # Mark the line number of class definition, which is important to determine the order
        # of widgets when magicclassees were nested. 
        if hasattr(newclass, "_class_line_number"):
            raise AttributeError(
                f"Class {newclass.__name__} already has an attribute '_class_line_number'."
                 "Thus it is incompatible with magic-class."
                 )
        if cls is None:
            newclass._class_line_number = current_location(3)
        else:
            newclass._class_line_number = current_location(2)
        
        def __init__(self, *args, **kwargs):
            app = get_app() # Without "app = " Jupyter freezes after closing the window!
            ClassGui.__init__(self, layout=layout, parent=parent, close_on_run=close_on_run, 
                              popup=popup, result_widget=result_widget, name=cls.__name__)
            super(oldclass, self).__init__(*args, **kwargs)
            self._convert_methods_into_widgets()
            
            if hasattr(self, _POST_INIT_NAME) and not is_dataclass(cls):
                self.__post_init__()
            
            # Record class instance construction
            self._record_macro(cls.__name__, args, kwargs)

        setattr(newclass, "__init__", __init__)
        return newclass
    
    return wrapper if cls is None else wrapper(cls)

class _h_separator(ClassGui, Separator):
    def __init__(self):
        Separator.__init__(self, orientation="horizontal")

class _v_separator(ClassGui, Separator):
    def __init__(self):
        Separator.__init__(self, orientation="vertical")
        
def separator(name:str=None, orientation:str="horizontal"):
    if orientation == "horizontal":
        sep_ = inline(_h_separator, name=name)
    elif orientation == "vertical":
        sep_ = inline(_v_separator, name=name)
    else:
        raise ValueError("'orientation' must be either 'horizontal' or 'vertical'.")
    sep_._class_line_number = current_location(2)
    return sep_
