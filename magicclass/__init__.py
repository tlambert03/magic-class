__version__ = "0.6.3.dev1"

from .core import (
    magicclass,
    magicmenu,
    magiccontext,
    magictoolbar,
    Parameters,
    build_help,
    get_function_gui,
    redo,
)

from .wrappers import (
    set_options,
    click,
    set_design,
    do_not_record,
    bind_key,
    confirm,
    nogui,
    mark_preview,
)

from .fields import field, vfield
from ._gui._base import wraps, defaults, MagicTemplate, PopUpMode
from ._gui.keybinding import Key
from . import widgets, utils, types

from magicgui import *

__all__ = [
    "magicclass",
    "magicmenu",
    "magiccontext",
    "magictoolbar",
    "Parameters",
    "build_help",
    "get_function_gui",
    "redo",
    "update_widget",
    "set_options",
    "click",
    "set_design",
    "do_not_record",
    "bind_key",
    "confirm",
    "nogui",
    "mark_preview",
    "field",
    "vfield",
    "wraps",
    "defaults",
    "MagicTemplate",
    "PopUpMode",
    "Key",
]
