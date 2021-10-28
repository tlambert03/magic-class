from __future__ import annotations
import pyqtgraph as pg
from typing import Sequence, overload
import numpy as np
from .graph_items import PlotDataItem, Scatter, Curve
from ..widgets import FrozenContainer

BOTTOM = "bottom"
LEFT = "left"
        
class Canvas(FrozenContainer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.plotwidget = pg.PlotWidget()
        self._items: list[PlotDataItem] = []
        self.set_widget(self.plotwidget)
               
    @property
    def xlabel(self):
        return self.plotwidget.plotItem.getLabel(BOTTOM).text
    
    @xlabel.setter
    def xlabel(self, label: str):
        self.plotwidget.plotItem.getLabel(BOTTOM).setText(label)
    
    @property
    def xlim(self):
        return self.plotwidget.plotItem.getAxis(BOTTOM).range
    
    @xlim.setter
    def xlim(self, value: tuple[float, float]):
        self.plotwidget.setXRange(value)
        
    @property
    def ylabel(self):
        return self.plotwidget.plotItem.getAxis(LEFT).text
        
    @ylabel.setter
    def ylabel(self, label: str):
        self.plotwidget.plotItem.getAxis(LEFT).setText(label)
       
    @property
    def ylim(self):
        return self.plotwidget.plotItem.getAxis(LEFT).range
    
    @ylim.setter
    def ylim(self, value: tuple[float, float]):
        self.plotwidget.setYRange(value)
         
    @property
    def title(self):
        return self.plotwidget.titleLabel.text
    
    @title.setter
    def title(self, value: str):
        self.plotwidget.titleLabel.setText(value)
    
    @overload
    def add_curve(self, x: Sequence[float], **kwargs): ...
    
    @overload
    def add_curve(self, x: Sequence[float], y: Sequence[float], **kwargs): ...
    
    def add_curve(self, x, y=None, **kwargs):
        if y is None:
            y = x
            x = np.arange(len(y))
        item = Curve(x, y, **kwargs)
        self._items.append(item)
        self.plotwidget.addItem(item.native)
    
    @overload
    def add_scatter(self, x: Sequence[float], **kwargs): ...
    
    @overload
    def add_scatter(self, x: Sequence[float], y: Sequence[float], **kwargs): ...
      
    def add_scatter(self, x, y=None, **kwargs):
        if y is None:
            y = x
            x = np.arange(len(y))
        item = Scatter(x, y, **kwargs)
        self._items.append(item)
        self.plotwidget.addItem(item.native)


class ImageCanvas(FrozenContainer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.imageview = pg.ImageView()
        self.set_widget(self.imageview)
    
    def set_image(self, image, **kwargs):
        self.imageview.setImage(image, **kwargs)
    
    