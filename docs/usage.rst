Usage
=====

Command line
------------

The package provides command line tools to handle a PSD document::

    psd-tools2 export <input_file> <output_file> [options]
    psd-tools2 show <input_file> [options]
    psd-tools2 debug <input_file> [options]
    psd-tools2 -h | --help
    psd-tools2 --version

Example::

    psd-tools2 show example.psd  # Show the file content
    psd-tools2 export example.psd example.png  # Export as PNG
    psd-tools2 export example.psd[0] example-0.png  # Export layer as PNG

Working with PSD document
-------------------------

:py:mod:`psd_tools2.api` package provides the user-friendly API to work
with PSD files.
:py:class:`~psd_tools2.PSDImage` represents a PSD file.

Open an image::

    from psd_tools2 import PSDImage
    psd = PSDImage.open('my_image.psd')

Most of the data structure in the :py:mod:`psd-tools2` suppports pretty
printing in IPython environment::

    In [1]: PSDImage.open('example.psd')
    Out[1]:
    PSDImage(mode=RGB size=101x55 depth=8 channels=3)
      [0] PixelLayer('Background' size=101x55)
      [1] PixelLayer('Layer 1' size=85x46)

Internal layers are accessible by iterator or indexing::

    for layer in psd:
        print(layer)
        if layer.is_group():
            for child in layer:
                print(child)

    child = psd[0][0]

The opened file can be saved::

    psd.save('output.psd')


Working with Layers
-------------------

There are various layer kinds in Photoshop.

The most basic layer type is :py:class:`~psd_tools2.api.layers.PixelLayer`::

    print(layer.name)
    layer.kind == 'pixel'

Some of the layer attributes are editable, such as a layer name::

    layer.name = 'Updated layer 1'

.. note:: Currently, the package does not support adding or removing of
    a layer.

:py:class:`~psd_tools2.api.layers.Group` has internal layers::

    for layer in group:
        print(layer)

    first_layer = group[0]

:py:class:`~psd_tools2.api.layers.TypeLayer` is a layer with texts::

    print(layer.text)

:py:class:`~psd_tools2.api.layers.ShapeLayer` draws a vector shape, and the
shape information is stored in `vector_mask` and `origination` property.
Other layers can also have shape information as a mask::

    print(layer.vector_mask)
    for shape in layer.origination:
        print(shape)

:py:class:`~psd_tools2.api.adjustments.SolidColorFill`,
:py:class:`~psd_tools2.api.adjustments.PatternFill`, and
:py:class:`~psd_tools2.api.adjustments.GradientFill` are fill layers that
paint the entire region if there is no associated mask. Sub-classes of
:py:class:`~psd_tools2.api.layers.AdjustmentLayer` represents layer
adjustment applied to the composed image. See :ref:`adjustment-layers`.

Exporting data to PIL
---------------------

Export the entire document as :py:class:`PIL.Image`::

    image = psd.compose()
    image.save('exported.png')

Note that above :py:meth:`~psd_tools2.PSDImage.compose` might return `None`
if the PSD document has no visible pixel.

Export a single layer including masks and clipping layers::

    image = layer.compose()

Export layer, mask, or clipping layers separately without composition::

    image = layer.topil()
    mask = layer.mask.topil()

    from psd_tools2 import compose
    clip_image = compose(layer.clip_layers)
