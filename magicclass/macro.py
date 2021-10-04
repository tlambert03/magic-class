from __future__ import annotations
from enum import Enum, auto
from collections import UserList, UserString
from pathlib import Path
from copy import deepcopy
from typing import Callable, Iterable, Iterator, Any, overload
import numpy as np

class Identifier(UserString):
    def __init__(self, obj:Any):
        self.valid = True
        if isinstance(obj, Path):
            seq = f"r'{obj}'"
        elif hasattr(obj, "__name__"): # class or function
            seq = obj.__name__
        elif isinstance(obj, str):
            if obj == "{x}":
                seq = obj
            else:
                seq = repr(obj)
        elif np.isscalar(obj): # int, float, bool, ...
            seq = obj
        elif isinstance(obj, (tuple, list)):
            seq = obj
        else:
            seq = f"var{hex(id(obj))}" # hexadecimals are easier to distinguish
            self.valid = False
            
        super().__init__(seq)
        self.type:type = type(obj)
    
    def as_annotation(self):
        return f"# {self}: {self.type}"
        

class Macro(UserList):
    def append(self, __object:Expr):
        if not isinstance(__object, Expr):
            raise TypeError("Cannot append objects to Macro except for MacroExpr objecs.")
        return super().append(__object)
    
    def __str__(self) -> str:
        return "\n".join(map(str, self))
    
    @overload
    def __getitem__(self, key: int | str) -> Expr: ...

    @overload
    def __getitem__(self, key: slice) -> Macro[Expr]: ...
        
    def __getitem__(self, key):
        return super().__getitem__(key)
    
    def __iter__(self) -> Iterator[Expr]:
        return super().__iter__()
    
    def __repr__(self):
        return ",\n".join(repr(expr) for expr in self)
        
class Head(Enum):
    init    = auto()
    getattr = auto()
    setattr = auto()
    getitem = auto()
    setitem = auto()
    call    = auto()
    assign  = auto()
    value   = auto()
    comment = auto()

_QUOTE = "'"

def sy(arg):
    return str(arg).strip(_QUOTE)

class Expr:
    """
    Python expression class. Inspired by Julia (https://docs.julialang.org/en/v1/manual/metaprogramming/),
    this class enables efficient macro recording and macro operation.
    
    Expr objects are mainly composed of "head" and "args". "Head" denotes what kind of operation it is,
    and "args" denotes the arguments needed for the operation. Other attributes, such as "symbol", is not
    necessary as a Expr object but it is useful to create executable codes.
    """
    n:int = 0
    
    # a map of how to conver expression into string.
    _map: dict[Head, Callable[[Expr], str]] = {
        Head.init   : lambda e: f"{sy(e.args[0])} = {e.args[1]}({', '.join(map(str, e.args[2:]))})",
        Head.getattr: lambda e: f"{sy(e.args[0])}.{sy(e.args[1])}",
        Head.setattr: lambda e: f"{sy(e.args[0])}.{sy(e.args[1])} = {e.args[2]}",
        Head.getitem: lambda e: f"{sy(e.args[0])}[{e.args[1]}]",
        Head.setitem: lambda e: f"{sy(e.args[0])}[{e.args[1]}] = {e.args[2]}",
        Head.call   : lambda e: f"{sy(e.args[0])}({', '.join(map(str, e.args[1:]))})",
        Head.assign : lambda e: f"{sy(e.args[0])}={e.args[1]}",
        Head.value  : lambda e: str(e.args[0]),
        Head.comment: lambda e: f"# {e.args[0]}",
    }
    
    def __init__(self, head:Head, args:Iterable[Any]):
        self.head = head
        if head == Head.value:
            self.args = args
        else:
            self.args = list(map(self.__class__.parse, args))
            
        self.number = self.__class__.n
        self.__class__.n += 1
    
    def __repr__(self) -> str:
        return self._repr()
    
    def _repr(self, ind:int=0) -> str:
        """
        Recursively expand expressions until it reaches value/assign expression.
        """
        if self.head in (Head.value, Head.assign):
            return str(self)
        out = [f"head: {self.head.name}\n{' '*ind}args:\n"]
        for i, arg in enumerate(self.args):
            out.append(f"{i:>{ind+2}}: {arg._repr(ind+4)}\n")
        return "".join(out)
    
    def __str__(self) -> str:
        return self.__class__._map[self.head](self)
    
    def __eq__(self, expr:Expr) -> bool:
        if self.head != Head.value:
            raise TypeError(f"Expression must be value, got {self.head}")
        if isinstance(expr, str):
            return self.args[0] == expr
        elif isinstance(expr, self.__class__):
            return self.args[0] == expr.args[0]
        else:
            raise ValueError(f"'==' is not supported between Expr and {type(expr)}")
        
    @classmethod
    def parse_method(cls, func:Callable, args:tuple[Any], kwargs:dict[str, Any]) -> Expr:
        """
        Make a method call expression.
        """
        method = cls(head=Head.getattr, args=["{x}", func]) # ui.func
        inputs = [method] + cls.convert_args(args, kwargs)
        return cls(head=Head.call, args=inputs) # ui.func(a=0,b=2)

    @classmethod
    def parse_init(cls, init_cls:type, args:tuple[Any], kwargs:dict[str, Any]) -> Expr:
        """
        Make a construction (__init__) expression.
        """
        inputs = ["{x}", init_cls] + cls.convert_args(args, kwargs)
        return cls(head=Head.init, args=inputs)
    
    @classmethod
    def convert_args(cls, args:tuple, kwargs:dict) -> list:
        inputs = []
        for a in args:
            inputs.append(a)
                
        for k, v in kwargs.items():
            inputs.append(cls(Head.assign, [k, v]))
        return inputs
    
    @classmethod
    def parse(cls, a: Any) -> Expr:
        return a if isinstance(a, cls) else cls(Head.value, [Identifier(a)])
    
    def iter_args(self) -> Iterator[Identifier]:
        """
        Recursively iterate along all the arguments.
        """
        for arg in self.args:
            if isinstance(arg, self.__class__):
                yield from arg.iter_args()
            else:
                yield arg
    
    def iter_expr(self) -> Iterator[Expr]:
        """
        Recursively iterate over all the nested Expr, until it reached to non-nested Expr.
        """        
        yielded = False
        for arg in self.args:
            if isinstance(arg, self.__class__):
                yield from arg.iter_expr()
                yielded = True
        
        if not yielded:
            yield self

class MacroMixin:
    def __init__(self):
        self._recorded_macro: Macro[Expr] = Macro()
        self._parameter_history: dict[str, dict[str, Any]] = {}
    
    def create_macro(self, symbol:str="ui") -> str:
        """
        Create executable Python scripts from the recorded macro object.

        Parameters
        ----------
        symbol : str, default is "ui"
            Symbol of the instance.
        """
        # Recursively build macro from nested magic-classes
        macro = [(0, self._recorded_macro[0])] + self._collect_macro()

        # Sort by the recorded order
        sorted_macro = map(lambda x: str(x[1]), sorted(macro, key=lambda x: x[0]))
        script = "\n".join(sorted_macro)
        
        # type annotation for the hard-to-record types
        annot = []
        idt_list = []
        for expr in self._recorded_macro:
            for idt in expr.iter_args():
                if idt.valid or idt in idt_list:
                    continue
                idt_list.append(idt)
                annot.append(idt.as_annotation())
        
        out = "\n".join(annot) + "\n" + script
        out = out.format(x=symbol)
        
        return out
    
    def _collect_macro(self, myname:str=None) -> list[tuple[int, Expr]]:
        out = []
        macro = deepcopy(self._recorded_macro)
        
        for expr in macro:
            if expr.head == Head.init:
                # nested magic-class construction is always invisible from the parent.
                # We should not record something like 'ui.A = A()'.
                continue
            
            if myname is not None:
                for _expr in expr.iter_expr():
                    # if _expr.head in (Head.value, Head.getattr, Head.getitem):
                    if _expr.args[0] == "{x}":
                        _expr.args[0] = Expr(Head.getattr, args=["{x}", myname])
                
            out.append((expr.number, expr))
        
        for name, attr in filter(lambda x: not x[0].startswith("__"), self.__dict__.items()):
            # Collect all the macro from child magic-classes recursively
            if not isinstance(attr, MacroMixin):
                continue
            out += attr._collect_macro(myname=name)
        
        return out
    
    def _record_macro(self, func:Callable, args:tuple, kwargs:dict[str, Any]) -> None:
        """
        Record a function call as a line of macro.

        Parameters
        ----------
        func : str
            Name of function.
        args : tuple
            Arguments.
        kwargs : dict[str, Any]
            Keyword arguments.
        """        
        macro = Expr.parse_method(func, args, kwargs)
        self._recorded_macro.append(macro)
        return None
    
    def _record_parameter_history(self, func:str, kwargs:dict[str, Any]) -> None:
        """
        Record parameter inputs to history for next call.

        Parameters
        ----------
        func : str
            Name of function.
        kwargs : dict[str, Any]
            Parameter inputs.
        """        
        kwargs = {k: v for k, v in kwargs.items() if not isinstance(v, np.ndarray)}
        self._parameter_history.update({func: kwargs})
        return None