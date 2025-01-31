from __future__ import annotations
import numpy as np

from typing import TYPE_CHECKING, Callable
import weakref

from vispy import scene
from vispy.scene import ViewBox, transforms
from vispy.app import MouseEvent

from ...widgets import FreeWidget
from ..._app import get_app


if TYPE_CHECKING:
    from vispy.visuals import Visual


class LayerItem:
    _visual: Visual
    _name: str

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.name}>"

    @property
    def visible(self) -> bool:
        """Layer visibility."""
        return self._visual.visible

    @visible.setter
    def visible(self, v: bool) -> None:
        """Set layer visibility."""
        self._visual.visible = v

    def _get_transform(self) -> transforms.MatrixTransform:
        return self._visual.transform

    def affine_transform(self, mtx: np.ndarray):
        """Apply affine transformation to the layer."""
        self._visual.transform = transforms.MatrixTransform(mtx)

    @property
    def translate(self) -> np.ndarray:
        mtx = self._get_transform().matrix
        return mtx[:3, 4]

    def _get_bbox(self) -> tuple[np.ndarray, np.ndarray]:
        raise NotImplementedError

    @property
    def name(self) -> str:
        return self._name


class HasViewBox:
    """The base class for all the vispy based visual objects."""

    def __init__(self, viewbox: ViewBox):
        from .layerlist import LayerList

        viewbox.unfreeze()
        self._viewbox = viewbox
        self._layerlist = LayerList()
        self._mouse_click_callbacks = []
        viewbox._parent_widget_ref = weakref.ref(self)

    @property
    def mouse_click_callbacks(self) -> list[Callable]:
        """List of mouse-click callbacks."""
        return self._mouse_click_callbacks

    @property
    def enabled(self) -> bool:
        return self._viewbox.interactive

    @enabled.setter
    def enabled(self, value) -> bool:
        self._viewbox.interactive = value

    @property
    def layers(self):
        return self._layerlist


class MultiPlot(FreeWidget):
    _base_class: type[HasViewBox]

    def __init__(self, nrows: int = 1, ncols: int = 1):
        app = get_app()
        super().__init__()
        self._canvas: list[HasViewBox] = []
        self._scene = SceneCanvas(keys="interactive")
        grid = self._scene.central_widget.add_grid()
        for r in range(nrows):
            for c in range(ncols):
                viewbox = grid.add_view(row=r, col=c)
                canvas = self._base_class(viewbox)
                self._canvas.append(canvas)

        self._scene.create_native()
        self.set_widget(self._scene.native)
        self._shape = (nrows, ncols)

    def __getitem__(self, key: int | tuple[int, int]):
        if isinstance(key, tuple):
            r, c = key
            nr, nc = self.shape
            if r >= nr or c >= nc:
                raise IndexError(f"Index out of range: {key}")
            return self._canvas[r * nc + c]
        else:
            key = int(key)
        return self._canvas[key]

    @property
    def shape(self) -> tuple[int, int]:
        return self._shape

    @property
    def size(self) -> int:
        r, c = self.shape
        return r * c


class SceneCanvas(scene.SceneCanvas):
    def on_mouse_press(self, event: MouseEvent):
        visual = self.visual_at(event.pos)
        if isinstance(visual, ViewBox) and hasattr(visual, "_parent_widget_ref"):
            vb: HasViewBox = visual._parent_widget_ref()
            tr = self.scene.node_transform(visual.scene)
            pos = tr.map(event.pos)[:2] - 0.5
            ev = MouseEvent(
                event.type,
                pos=pos,
                button=event.button,
                buttons=event.buttons,
                modifiers=event.modifiers,
                delta=event.delta,
                last_event=event.last_event,
                press_event=event.press_event,
            )

            for callback in vb._mouse_click_callbacks:
                callback(ev)
