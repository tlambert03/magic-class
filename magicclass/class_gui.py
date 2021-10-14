from __future__ import annotations
from typing import TypeVar
from inspect import signature
from qtpy.QtWidgets import QMenuBar
from magicgui.widgets import Container, MainWindow,Label, LineEdit, FunctionGui
from magicgui.widgets._bases import Widget, ButtonWidget, ValueWidget
from magicgui.widgets._concrete import _LabeledWidget

from .macro import Expr, Head
from .utils import iter_members, extract_tooltip, get_parameters, define_callback
from .widgets import PushButtonPlus, FrozenContainer
from .field import MagicField
from .menu_gui import MenuGui
from .containers import ButtonContainer, ScrollableContainer, CollapsibleContainer, ToolBox
from ._base import BaseGui

C = TypeVar("C")
    
class ClassGuiBase(BaseGui):
    # This class is always inherited by @magicclass decorator.
    _component_class = PushButtonPlus
    _container_widget: type[C]
    _widget: C
    _result_widget: LineEdit
    
    def _create_widget_from_field(self, name: str, fld: MagicField):
        cls = self.__class__
        if fld.not_ready():
            try:
                fld.default_factory = cls.__annotations__[name]
                if isinstance(fld.default_factory, str):
                    # Sometimes annotation is not type but str. 
                    from pydoc import locate
                    fld.default_factory = locate(fld.default_factory)
                    
            except (AttributeError, KeyError):
                pass
            
        widget = fld.to_widget()
        widget.name = widget.name or name
            
        if isinstance(widget, (ValueWidget, Container)):
            # If the field has callbacks, connect it to the newly generated widget.
            for callback in fld.callbacks:
                # funcname = callback.__name__
                widget.changed.connect(define_callback(self, callback))
                
            if hasattr(widget, "value"):        
                # By default, set value function will be connected to the widget.
                @widget.changed.connect
                def _set_value(event):
                    if not event.source.enabled:
                        # If widget is read only, it means that value is set in script (not manually).
                        # Thus this event should not be recorded as a macro.
                        return None
                    value = event.source.value # TODO: fix after psygnal start to be used.
                    self.changed(value=self)
                    if isinstance(value, Exception):
                        return None
                    sub = Expr(head=Head.getattr, args=[name, "value"]) # name.value
                    expr = Expr(head=Head.setattr, args=["{x}", sub, value]) # {x}.name.value = value
                    
                    last_expr = self._recorded_macro[-1]
                    if last_expr.head == expr.head and last_expr.args[1].args[0] == expr.args[1].args[0]:
                        self._recorded_macro[-1] = expr
                    else:
                        self._recorded_macro.append(expr)
                    return None
        
        setattr(self, name, widget)
        return widget
    
    def _convert_attributes_into_widgets(self):
        """
        This function is called in dynamically created __init__. Methods, fields and nested
        classes are converted to magicgui widgets.
        """        
        cls = self.__class__
        
        # Add class docstring as label.
        if cls.__doc__:
            doc = extract_tooltip(cls)
            lbl = Label(value=doc)
            self.append(lbl)
        
        # Bind all the methods and annotations
        base_members = set(x[0] for x in iter_members(self._container_widget)) 
        base_members |= set(x[0] for x in iter_members(ClassGuiBase))
        for name, attr in filter(lambda x: x[0] not in base_members, iter_members(cls)):
            if name in ClassGuiBase.__annotations__.keys():
                continue
            
            # First make sure none of them is type object nor MagicField object.
            if isinstance(attr, type):
                # Nested magic-class
                widget = attr()
                setattr(self, name, widget)
            
            elif isinstance(attr, MagicField):
                # If MagicField is given by field() function.
                widget = self._create_widget_from_field(name, attr)
            
            elif isinstance(attr, FunctionGui):
                widget = attr
                p0 = list(signature(attr).parameters)[0]
                getattr(widget, p0).bind(self) # set self to the first argument
                
            else:
                # convert class method into instance method
                if not hasattr(attr, "__magicclass_wrapped__"):
                    widget = getattr(self, name, None)
                    
                else:
                    # If the method is redefined, the newer one should be used instead, while the
                    # order of widgets should be follow the place of the older method.
                    widget = attr.__magicclass_wrapped__.__get__(self)
            
            if isinstance(widget, MenuGui):
                widget.__magicclass_parent__ = self
                if self._menubar is None:
                    self._menubar = QMenuBar(parent=self.native)
                    self.native.layout().setMenuBar(self._menubar)
                
                widget.native.setParent(self._menubar, widget.native.windowFlags())
                self._menubar.addMenu(widget.native)
            
            elif isinstance(widget, Widget) or callable(widget):
                if (not isinstance(widget, Widget)) and callable(widget):
                    # Methods (FunctionGui not included)
                    widget = self._create_widget_from_method(widget)
                
                elif isinstance(widget, ClassGuiBase):
                    # magic-class has to know its parent
                    widget.__magicclass_parent__ = self

                elif isinstance(widget, FunctionGui):
                    # magic-class has to know when the nested FunctionGui is called.
                    f = _nested_function_gui_callback(self, widget)
                    widget.called.connect(f)
                    
                else:
                    widget.name = widget.name or name
                    if hasattr(widget, "text"):
                        widget.text = widget.text or name
                
                # Now, "widget" is a Widget object.
                
                if name.startswith("_"):
                    continue
                
                _hide_labels = (_LabeledWidget, ButtonWidget, ClassGuiBase, FrozenContainer, Label)
                
                if isinstance(widget, ValueWidget):
                    widget.changed.connect(lambda x: self.changed(value=self))
                if isinstance(widget, ClassGuiBase):
                    widget.margins = (0, 0, 0, 0)
                    
                _widget = widget

                if self.labels:
                    if not isinstance(widget, _hide_labels):
                        _widget = _LabeledWidget(widget)
                        widget.label_changed.connect(self._unify_label_widths)

                key = len(self)
                self._list.insert(key, widget)
                self._widget._mgui_insert_widget(key, _widget)
                
        # Append result widget in the bottom
        if self._result_widget is not None:
            self._result_widget.enabled = False
            self.append(self._result_widget)
        
        self._unify_label_widths()

        return None

def make_gui(container: type):
    """
    Make a ClassGui class from a Container widget.
    """    
    def wrapper(cls: ClassGuiBase):
        cls = type(cls.__name__, (container, ClassGuiBase), {})
        def __init__(self, 
                    layout: str = "vertical", 
                    parent = None, 
                    close_on_run: bool = True,
                    popup: bool = True, 
                    result_widget: bool = False,
                    labels: bool = True, 
                    name: str = None, 
                    single_call: bool = True
                    ):

            container.__init__(self, layout=layout, labels=labels, name=name)
            BaseGui.__init__(self, close_on_run=close_on_run, popup=popup, single_call=single_call)
            
            if parent is not None:
                self.parent = parent
                
            self._menubar = None
            
            self._result_widget = None
            if result_widget:
                self._result_widget = LineEdit(gui_only=True, name="result")
            
            self.native.setObjectName(self.__class__.__name__)
        
        def show(self, run: bool = False) -> None:
            """
            Show ClassGui. If any of the parent ClassGui is a dock widget in napari, then this will also show up
            as a dock widget (floating if popup=True).
            """        
            current_self = self
            while hasattr(current_self, "__magicclass_parent__") and current_self.__magicclass_parent__:
                current_self = current_self.__magicclass_parent__
            
            viewer = current_self.parent_viewer
            if viewer is not None:
                dock = viewer.window.add_dock_widget(self, area="right", allowed_areas=["left", "right"])
                dock.setFloating(current_self._popup)
            else:
                container.show(self, run=run)
                self.native.activateWindow()
            return None
        
        def close(self):
            viewer = self.parent_viewer
            if viewer is not None:
                try:
                    viewer.window.remove_dock_widget(self.parent)
                except Exception:
                    pass
                
            container.close(self)
                
            return None
        
        cls.__init__ = __init__
        cls.show = show
        cls.close = close
        cls._container_widget = container
        return cls
    return wrapper


@make_gui(Container)
class ClassGui: pass

@make_gui(ScrollableContainer)
class ScrollableClassGui: pass

@make_gui(CollapsibleContainer)
class CollapsibleClassGui: pass

@make_gui(ButtonContainer)
class ButtonClassGui: pass

@make_gui(ToolBox)
class ToolBoxClassGui: pass

@make_gui(MainWindow)
class MainWindowClassGui: pass

def _nested_function_gui_callback(cgui: ClassGuiBase, fgui: FunctionGui):
    def _after_run(e):
        value = e.value
        if isinstance(value, Exception):
            return None
        inputs = get_parameters(fgui)
        args = [Expr(head=Head.assign, args=[k, v]) for k, v in inputs.items()]
        # args[0] is self
        sub = Expr(head=Head.getattr, args=["{x}", fgui.name]) # {x}.func
        expr = Expr(head=Head.call, args=[sub] + args[1:]) # {x}.func(args...)

        if fgui._auto_call:
            # Auto-call will cause many redundant macros. To avoid this, only the last input
            # will be recorded in magic-class.
            last_expr = cgui._recorded_macro[-1]
            if last_expr.head == Head.call and last_expr.args[0].head == Head.getattr and \
                last_expr.args[0].args[1] == expr.args[0].args[1]:
                cgui._recorded_macro.pop()

        cgui._recorded_macro.append(expr)
    return _after_run
