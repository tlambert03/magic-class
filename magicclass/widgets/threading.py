from __future__ import annotations
from functools import partial, wraps
import time
import threading
from typing import Callable, Iterable, TypeVar

from magicgui.widgets import Container, Label, ProgressBar

T = TypeVar("T")

class ProgressWidget(Container):
    def __init__(self, text: str = None, visible: bool = False):
        if text is None:
            text = "Running ..."
        self._description = Label(value=text)
        self._pbar = ProgressBar()
        super().__init__(widgets=[self._description, self._pbar], 
                         labels=False, 
                         visible=visible)
    
    def __call__(self, iterable: Iterable[T]) -> Iterable[T]:
        if hasattr(iterable, "__len__"):
            dt = self._pbar.max/len(iterable)
        else:
            dt = 0
            
        with self.run() as p:
            for it in iterable:
                yield it
                p._pbar.increment(dt)
    
    def range(self, n: int):
        return self(range(n))
    
    def run(self) -> progress:
        """
        Build a context that progress bar will be displayed.

        Returns
        -------
        progress
            Context manager for progress bar.
        """        
        return progress(progress=self)
    
    def show_progress(self, f: Callable = None) -> Callable:
        @wraps(f)
        def function_with_progressbar(*args, **kwargs):
            with self.run():
                out = f(*args, **kwargs)
            return out
        return function_with_progressbar
    
    def _show_all(self):
        self.visible = True
        self._pbar.visible = True
        self._description.visible = True
            
    @property
    def text(self) -> str:
        return self._description.value
    
    @text.setter
    def text(self, value: str):
        self._description.value = value
    
    @property
    def value(self) -> int:
        return self._pbar.value
    
    @value.setter
    def value(self, v: int):
        self._pbar.value = min(v, self._pbar.max)

_progress_widget = ProgressWidget()
_progress_widget.visible = False

class progress:
    def __init__(self, obj: Callable = None, *, progress: ProgressWidget = None):
        if progress is None:
            self.close_on_finish = True
            progress = _progress_widget
        else:
            self.close_on_finish = False
        
        self.progress = progress
        self.thread = None
        self.running = False
        
        self.function = None
        if isinstance(obj, Callable):
            self.function = self._wrap_function(obj)
        
    
    @property
    def function(self):
        return self._function
    
    @function.setter
    def function(self, f: Callable):
        self._function = f
        if callable(f):
            self.__name__ = f.__name__
            self.__qualname__ = f.__qualname__
        
    @property
    def __signature__(self):
        return self.function.__signature__
        
    def __call__(self, *args, **kwargs):
        if self.function is None:
            if len(args) != 1 or not callable(args[0]):
                raise TypeError("Cannot call progress before setting a function.")
            self.function = self._wrap_function(args[0])
            return self.function
        else:
            return self.function(*args, **kwargs)
    
    def __get__(self, obj, objtype=None):
        f = partial(self.function, obj)
        return self.__class__(f, progress=self.progress)
        
    def _wrap_function(self, function: Callable):
        @wraps(function)
        def _func(*args, **kwargs):
            with self:
                out = function(*args, **kwargs)
            return out
        return _func
    
    def _run(self):
        self.running = True
        
        while self.running:
            time.sleep(0.01)
        
        # Show 100%
        self.progress.value = self.progress._pbar.max
        time.sleep(0.1)
    
    def __enter__(self) -> ProgressWidget:
        self.pbar_was_visible = self.progress.visible
        self.progress._show_all()
        self.progress.value = 0
        self.thread = threading.Thread(target=self._run)
        self.thread.start()
        
        return self.progress

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.running = False
        if self.thread is not None:
            self.thread.join()
        
        self.progress._pbar.min = 0
        self.progress._pbar.max = 1000
        self.progress._pbar.value = 1000
        self.progress.visible = self.pbar_was_visible