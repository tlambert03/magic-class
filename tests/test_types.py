from magicclass import magicclass, set_options
from magicclass.types import Optional, Tuple, List
from magicclass import widgets

def test_basics():
    @magicclass
    class A:
        def f(self, x: Optional[int]):
            pass
        def g(self, y: List[int]):
            pass
        def h(self, z: Tuple[str, int]):
            pass
    ui = A()
    ui["f"].changed()
    opt = ui["f"].mgui[0]
    ui["g"].changed()
    list_edit = ui["g"].mgui[0]
    ui["h"].changed()
    tuple_edit = ui["h"].mgui[0]

    assert isinstance(opt, widgets.OptionalWidget)
    assert opt.value is None
    assert isinstance(list_edit, widgets.ListEdit)
    assert list_edit.value == []
    assert isinstance(tuple_edit, widgets.TupleEdit)
    assert tuple_edit.value == ("", 0)

def test_nested_types():
    @magicclass
    class A:
        def f(self, x: Optional[Tuple[int, bool]]):
            pass
        def g(self, y: List[Optional[float]]):
            pass
        def h(self, z: Tuple[str, Optional[float]]):
            pass

    ui = A()
    ui["f"].changed()
    opt = ui["f"].mgui[0]
    ui["g"].changed()
    list_edit = ui["g"].mgui[0]
    ui["h"].changed()
    tuple_edit = ui["h"].mgui[0]

    assert isinstance(opt, widgets.OptionalWidget)
    assert isinstance(opt._inner_value_widget, widgets.TupleEdit)
    assert opt._inner_value_widget[0].value == 0
    assert opt._inner_value_widget[1].value == False

    assert isinstance(list_edit, widgets.ListEdit)
    list_edit[-2].changed()
    assert isinstance(list_edit[0], widgets.OptionalWidget)
    assert list_edit[0][1].value == 0.0

    assert isinstance(tuple_edit, widgets.TupleEdit)
    assert tuple_edit[0].value == ""
    assert tuple_edit[1].value == None
