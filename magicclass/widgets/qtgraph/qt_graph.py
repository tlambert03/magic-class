from __future__ import annotations
import pyqtgraph as pg
from pyqtgraph import colormap as cmap
from typing import Sequence, overload
import numpy as np
from .components import Region, ScaleBar, TextOverlay
from .graph_items import BarPlot, PlotDataItem, Scatter, Curve, Histogram
from .mouse_event import MouseClickEvent
from ..utils import FreeWidget

BOTTOM = "bottom"
LEFT = "left"

class LayerList:
    def __init__(self, parent: HasPlotItem):
        self.parent = parent
    
    def __getitem__(self, key: int | str) -> PlotDataItem:
        if isinstance(key, int):
            return self.parent._items[key]
        elif isinstance(key, str):
            for item in self.parent._items:
                if item.name == key:
                    return item
            else:
                raise ValueError(f"Item '{key}' not found.")
        else:
            raise TypeError(f"Cannot use type {type(key)} as a key.")
        
    def __delitem__(self, key: int | str):
        return self.parent.remove_item(key)
    
    def append(self, item: PlotDataItem):
        if isinstance(item, PlotDataItem):
            self.parent._add_item(item)
        else:
            raise TypeError(f"Cannot append type {type(item)}.")
    
    def __len__(self):
        return len(self.parent._items)
    
    def clear(self):
        for _ in range(len(self)):
            self.parent.remove_item(-1)


class HasPlotItem:
    _items: list[PlotDataItem]
    
    @property
    def _graphics(self):
        """Target widget to add graphics items."""
        raise NotImplementedError()

    @property
    def layers(self) -> LayerList:
        return LayerList(self)
    
    @overload
    def add_curve(self, x: Sequence[float], **kwargs): ...
    
    @overload
    def add_curve(self, x: Sequence[float], y: Sequence[float], **kwargs): ...
    
    def add_curve(self, 
                  x=None,
                  y=None, 
                  face_color = None,
                  edge_color = "white",
                  name: str | None = None,
                  lw: float = 1,
                  ls: str = "-"):
        """
        Add line plot like ``plt.plot(x, y)``

        Parameters
        ----------
        x : array-like, optional
            X data.
        y : array-like, optional
            Y data.
        """        
        if y is None:
            if x is None:
                x = []
                y = []
            else:
                y = x
                x = np.arange(len(y))
        item = Curve(x, y, face_color=face_color, edge_color=edge_color, 
                     name=name, lw=lw, ls=ls)
        self._add_item(item)
        return item
    
    @overload
    def add_scatter(self, x: Sequence[float], **kwargs): ...
    
    @overload
    def add_scatter(self, x: Sequence[float], y: Sequence[float], **kwargs): ...
      
    def add_scatter(self, 
                    x=None, 
                    y=None,
                    face_color = "white",
                    edge_color = None,
                    size: float = 7,
                    name: str | None = None,
                    lw: float = 1,
                    ls: str = "-",
                    symbol="o"):
        """
        Add scatter plot like ``plt.scatter(x, y)``

        Parameters
        ----------
        x : array-like, optional
            X data.
        y : array-like, optional
            Y data.
        kwargs :
            color, lw (line width), ls (linestyle) is supported now.
        """        
        if y is None:
            if x is None:
                x = []
                y = []
            else:
                y = x
                x = np.arange(len(y))
        item = Scatter(x, y, face_color=face_color, edge_color=edge_color, 
                       size=size, name=name, lw=lw, ls=ls, symbol=symbol)
        self._add_item(item)
        return item
    
    def add_hist(self, data: Sequence[float],
                 bins: int | Sequence | str = 10,
                 range=None,
                 density: bool = False,
                 face_color = "white",
                 edge_color = None,
                 name: str | None = None,
                 lw: float = 1,
                 ls: str = "-",
                 ):
        """
        Add histogram like ``plt.hist(data)``

        Parameters
        ----------
        data : array-like
            Data for histogram constrction.
        """        
        item = Histogram(data, bins=bins, range=range, density=density, 
                         face_color=face_color, edge_color=edge_color,
                         name=name, lw=lw, ls=ls)
        self._add_item(item)
        return item
    
    @overload
    def add_bar(self, x: Sequence[float], **kwargs): ...
    
    @overload
    def add_bar(self, x: Sequence[float], y: Sequence[float], **kwargs): ...
    
    def add_bar(self, 
                x=None,
                y=None, 
                face_color = None,
                edge_color = "white",
                name: str | None = None,
                lw: float = 1,
                ls: str = "-"):
        if y is None:
            if x is None:
                x = []
                y = []
            else:
                y = x
                x = np.arange(len(y))
                
        item = BarPlot(x, y, face_color=face_color, edge_color=edge_color, 
                       name=name, lw=lw, ls=ls)
        self._add_item(item)
        return item
    
    def _add_item(self, item: PlotDataItem):
        self._items.append(item)
        self._graphics.addItem(item.native)
    
    def remove_item(self, item: PlotDataItem | int | str):
        if isinstance(item, PlotDataItem):
            i = self._items.index(item)
        elif isinstance(item, int):
            if item < 0:
                item += len(self._items)
            i = item
        elif isinstance(item, str):
            for i, each in enumerate(self._items):
                if each.name == item:
                    break
            else:
                raise ValueError(f"No item named {item}")
            
        if i < 0:
            raise ValueError(f"Item {item} not found")
        item = self._items.pop(i)
        self._graphics.removeItem(item.native)



class QtPlotCanvas(FreeWidget, HasPlotItem):
    """
    A 1-D data viewer that have similar API as napari Viewer.
    """
    def __init__(self, region_visible=False, **kwargs):
        
        
        # prepare widget
        self.plotwidget = pg.PlotWidget()
        self.plotwidget.setMinimumSize(100, 60)
        self._items: list[PlotDataItem] = []
        
        self._enabled = True
        
        # prepare region item
        self._region = Region()
        self._region.visible = region_visible
        self.plotwidget.addItem(self._region.native, ignoreBounds=True)
        
        # prepare mouse event
        self.mouse_click_callbacks = []
        self.plotwidget.scene().sigMouseClicked.connect(self._mouse_clicked)
        
        super().__init__(**kwargs)
        self.set_widget(self.plotwidget)
    
    def _mouse_clicked(self, e):
        if len(self._items) == 0:
            return
        e = MouseClickEvent(e, self._items[0].native)
        for callback in self.mouse_click_callbacks:
            callback(e)
    
    @property
    def region(self) -> Region:
        return self._region
    
    @property
    def _graphics(self):
        return self.plotwidget
    
    @property
    def xlabel(self):
        """
        Label of X-axis.
        """        
        return self.plotwidget.plotItem.getLabel(BOTTOM).text or ""
    
    @xlabel.setter
    def xlabel(self, label: str) -> str:
        self.plotwidget.plotItem.setLabel(BOTTOM, label)
    
    @property
    def xlim(self):
        """
        Range limits of X-axis.
        """        
        return self.plotwidget.plotItem.getAxis(BOTTOM).range
    
    @xlim.setter
    def xlim(self, value: tuple[float, float]):
        self.plotwidget.setXRange(*value)
        
    @property
    def ylabel(self) -> str:
        """
        Label of Y-axis.
        """        
        return self.plotwidget.plotItem.getLabel(LEFT).text or ""
        
    @ylabel.setter
    def ylabel(self, label: str):
        self.plotwidget.plotItem.setLabel(LEFT, label)
       
    @property
    def ylim(self):
        """
        Range limits of Y-axis.
        """        
        return self.plotwidget.plotItem.getAxis(LEFT).range
    
    @ylim.setter
    def ylim(self, value: tuple[float, float]):
        self.plotwidget.setYRange(*value)
    
    @property
    def enabled(self) -> bool:
        """Mouse interactivity"""        
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        self.plotwidget.setMouseEnabled(value, value)
        self._enabled = value
    
    interactive = enabled

       
class QtImageCanvas(FreeWidget, HasPlotItem):
    def __init__(self, 
                 image: np.ndarray = None, 
                 cmap=None, 
                 contrast_limits: tuple[float, float] = None,
                 show_hist: bool = True,
                 show_button: bool = True,
                 **kwargs):
        
        self.imageview = pg.ImageView(name=kwargs.get("name", "ImageView"))
        self.imageview.view.setMinimumSize(100, 60)
        self._interactive = True
        self._items: list[PlotDataItem] = []
        self.show_hist(show_hist)
        self.show_button(show_button)
        
        # set properties
        if image is not None:
            self.image = image
        if cmap is not None:
            self.cmap = cmap
        if contrast_limits is not None:
            self.contrast_limits = contrast_limits
        
        # prepare text overlay
        self._text_overlay = TextOverlay(text="", color="gray")
        self.imageview.scene.addItem(self._text_overlay.native)
        
        # prepare scale bar
        self._scale_bar = ScaleBar()
        self.imageview.scene.addItem(self._scale_bar.native)
        self._scale_bar.visible = False
        self._scale_bar.native.setParentItem(self.imageview.view)
        self._scale_bar.native.anchor((1, 1), (1, 1), offset=(-20, -20))
        
        # prepare mouse event
        self.mouse_click_callbacks = []
        self.imageview.scene.sigMouseClicked.connect(self._mouse_clicked)
        
        super().__init__(**kwargs)
        self.set_widget(self.imageview)
        
    
    def _mouse_clicked(self, e):
        items = self.imageview.view.addedItems
        if len(items) == 0:
            return
        e = MouseClickEvent(e, items[0])
        for callback in self.mouse_click_callbacks:
            callback(e)
    
    @property
    def _graphics(self):
        return self.imageview.view
    
    @property
    def text_overlay(self) -> TextOverlay:
        """Text overlay on the image."""        
        return self._text_overlay
    
    @property
    def scale_bar(self) -> ScaleBar:
        """Scale bar on the image."""
        return self._scale_bar
    
    @property
    def image(self) -> np.ndarray | None:
        """Image data"""
        if self.imageview.image is None:
            return None
        else:
            return self.imageview.image.T
        
    @image.setter
    def image(self, image):
        self.imageview.setImage(np.asarray(image).T, pos=(-0.5, -0.5), autoRange=False)
        
    @image.deleter
    def image(self):
        self.imageview.clear()
    
    @property
    def contrast_limits(self) -> tuple[float, float]:
        """Contrast limits of image"""        
        return self.imageview.levelMin, self.imageview.levelMax
    
    @contrast_limits.setter
    def contrast_limits(self, value: tuple[float, float]):
        self.imageview.setLevels(*value)
    
    @property
    def view_range(self) -> list[list[float, float]]:
        """Range of image (edge coordinates of canvas)"""
        return self.imageview.view.viewRange()
    
    @view_range.setter
    def view_range(self, value: tuple[tuple[float, float], tuple[float, float]]):
        yrange, xrange = value
        self.imageview.view.setRange(xRange=xrange, yRange=yrange)

    @property
    def enabled(self) -> bool:
        """Mouse interactivity"""        
        return self._interactive
    
    @enabled.setter
    def enabled(self, value: bool):
        self.imageview.view.setMouseEnabled(value, value)
        self._interactive = value
    
    interactive = enabled
    
    @property
    def cmap(self):
        """Color map"""
        return self._cmap
    
    @cmap.setter
    def cmap(self, value):
        if isinstance(value, str):
            _cmap = cmap.get(value, source="matplotlib")
        else:
            _cmap = value
        self.imageview.setColorMap(_cmap)
        self._cmap = value
            
    def show_hist(self, visible: bool = True):
        """
        Set visibility of intensity histogram.

        Parameters
        ----------
        visible : bool
            Visibility of histogram
        """        
        if visible:
            self.imageview.ui.histogram.show()
        else:
            self.imageview.ui.histogram.hide()
        
    def show_button(self, visible: bool = True):
        """
        Set visibility of ROI/Norm buttons.

        Parameters
        ----------
        visible : bool
            Visibility of ROI/Norm buttons
        """        
        if visible:
            self.imageview.ui.menuBtn.show()
            self.imageview.ui.roiBtn.show()
        else:
            self.imageview.ui.menuBtn.hide()
            self.imageview.ui.roiBtn.hide()
    