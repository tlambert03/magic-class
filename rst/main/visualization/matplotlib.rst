=================
Matplotlib Figure
=================

.. contents:: Contents
    :local:
    :depth: 3

``matplotlib`` is one of the most widely used data visualization libraries. I
guess most of the Python users know the basics of the library.

For data visualization of simple data set, your can use the ``Figure`` widget.

.. code-block:: python

    from magicclass.widgets import Figure

It has very simple API inherited from the original functions, such as
``plt.plot(x, y)`` or ``plt.xlim(0, 100)``. It also support interactive plot.

Basic Usage
-----------

If you are using ``Figure`` widget independent of ``magic-class``, it's just
like the usual ``matplotlib`` way.

.. code-block:: python

    # run "%gui qt" if needed
    plt = Figure()
    plt.plot(np.random.random(100))
    plt.show()

Many functions defined in ``matplotlib.pyplot`` are also supported.

.. code-block:: python

    plt.xlim(-5, 5)  # change x-limits
    plt.hist(np.random.normal(size=100), color="r")  # histogram
    plt.imshow(np.random.random((64, 64)), cmap="gray")  # 2D image
    plt.xlabel("X label")  # change x-label
    plt.title("title")  # change title
    plt.xticks([0, 1], ["start", "end"])  # change x-tick labels

If you want to clear the contents, call ``cla()`` method.

.. code-block:: python

    plt.cla()

Use Figure Widget in Magic Class
--------------------------------

In most cases, you'll use ``field`` to create a ``matplotlib`` figure widget
in your GUI.

.. code-block:: python

    from magicclass import magicclass, field

    @magicclass
    class Main:
        plt = field(Figure)

        def plot(self):
            self.plt.plot(np.random.random(100))

Use Multiple Axes
-----------------

Sometimes we have to prepare multiple axes and plot different sets of data
separately by using ``fig, ax = plt.subplots(2, 1)`` or other similar methods.
The ``Figure`` widget also support multi-axes plotting. You can create a
multi-axes widget by passing ``nrows`` and ``ncols`` arguments to it, like
``plt.subplots``, and all the axes are accessible via ``axes`` attribute.
However, since ``axes`` are the ``matplotlib``'s ``Axes`` object itself,
you'll have to call ``draw`` method to update the figure.

.. code-block:: python

    plt = Figure(nrows=1, ncols=2)
    plt.axes[0].plot([1, 2, 3])  # the first axis
    plt.axes[1].plot([1, 4, 2])  # the second axis
    plt.draw()  # update

.. code-block:: python

    @magicclass
    class Main:
        plt = field(Figure, options={"nrows": 1, "ncols": 2})

Plot API
--------

For the simplest usage, you can use ``plot_api`` submodule. Its API is almost
identical to those in ``matplotlib.pyplot``.

.. code-block:: python

    # instead of import matplotlib.pyplot as plt
    import magicclass.plot_api as plt

    plt.figure()
    plt.plot([0, 1, 2, 3], [4, 2, 3, 1], color="red")
    plt.show()

The current figure widget is available with ``gcw()`` function. It returns the
``magicclass.widgets.Figure`` widget.

.. code-block:: python

    # add figure to a widget.
    from magicgui.widgets import Container

    fig = plt.gcw()
    cnt = Container(widgets=[fig])
    cnt.show()
