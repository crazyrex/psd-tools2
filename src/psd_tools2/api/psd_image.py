"""
PSD Image module.
"""
from __future__ import absolute_import, unicode_literals
import logging

from psd_tools2.constants import (
    Clipping, Compression, ColorMode, SectionDivider
)
from psd_tools2.psd import PSD, FileHeader, ImageData, ImageResources
from psd_tools2.api.layers import (
    Group, PixelLayer, ShapeLayer, SmartObjectLayer, TypeLayer, GroupMixin
)
from psd_tools2.api import adjustments
from psd_tools2.api import pil_io
from psd_tools2.api import deprecated


logger = logging.getLogger(__name__)


class PSDImage(GroupMixin):
    """
    Photoshop PSD/PSB file object.

    Example::

        from psd_tools2 import PSDImage

        psd = PSDImage.open('example.psd')
        image = psd.topil()

        for layer in psd:
            if layer.has_pixels():
                layer_image = layer.topil()
    """
    def __init__(self, psd):
        assert isinstance(psd, PSD)
        self._psd = psd
        self._layers = []
        self._tagged_blocks = None
        self._init()

    @classmethod
    def new(cls, mode, size, color=0, depth=8, **kwargs):
        """
        Create a new PSD document.

        :param mode: The color mode to use for the new image.
        :param size: A tuple containing (width, height) in pixels.
        :param color: What color to use for the image. Default is black.
        :return: A :py:class:`~psd_tools2.api.psd_image.PSDImage` object.
        """
        header = cls._make_header(mode, size, depth)
        image_data = ImageData.new(header, color=color, **kwargs)
        # TODO: Add default metadata.
        return cls(PSD(
            header=header,
            image_data=image_data,
            image_resources=ImageResources.new(),
        ))

    @classmethod
    def frompil(cls, image, compression=Compression.PACK_BITS):
        """
        Create a new PSD document from PIL Image.

        :param image: PIL Image object.
        :param compression: ImageData compression option. See
            :py:class:`~psd_tools2.constants.Compression`.
        :return: A :py:class:`~psd_tools2.api.psd_image.PSDImage` object.
        """
        header = cls._make_header(image.mode, image.size)
        # TODO: Add default metadata.
        # TODO: Perhaps make this smart object.
        image_data = ImageData(compression=compression)
        image_data.set_data([channel.tobytes() for channel in image.split()],
                            header)
        return cls(PSD(
            header=header,
            image_data=image_data,
            image_resources=ImageResources.new(),
        ))

    @classmethod
    def open(cls, fp):
        """
        Open a PSD document.

        :param fp: filename or file-like object.
        :return: A :py:class:`~psd_tools2.api.psd_image.PSDImage` object.
        """
        if hasattr(fp, 'read'):
            self = cls(PSD.read(fp))
        else:
            with open(fp, 'rb') as f:
                self = cls(PSD.read(f))
        return self

    def save(self, fp, mode='wb'):
        """
        Save the PSD file.

        :param fp: filename or file-like object.
        :param mode: file open mode, default 'wb'.
        """
        if hasattr(fp, 'write'):
            self._psd.write(fp)
        else:
            with open(fp, mode) as f:
                self._psd.write(f)

    def topil(self):
        """
        Get PIL Image.

        :return: :py:class:`PIL.Image`, or `None` if the composed image is not
            available.
        """
        if self.has_preview():
            return pil_io.convert_image_data_to_pil(self._psd)
        return None

    def compose(self, force=False, bbox=None, **kwargs):
        """
        Compose the PSD image.

        See :py:func:`~psd_tools2.compose` for available extra arguments.

        :param bbox: Viewport tuple (left, top, right, bottom).
        :return: :py:class:`PIL.Image`, or `None` if there is no pixel.
        """
        from psd_tools2.api.composer import compose
        image = self.topil() if (not force or len(self) == 0) else None
        if image is None:
            image = compose(self, bbox=bbox or self.viewbox, **kwargs)
        return image

    def is_visible(self):
        """
        Returns visibility of the element.

        :return: `True`
        """
        return True

    def has_preview(self):
        """
        Returns if the document has real merged data. When True, `topil()`
        returns pre-composed data.
        """
        version_info = self.image_resources.get_data('version_info')
        if version_info:
            return version_info.has_composite
        return True  # Assuming the image data is valid by default.

    @property
    def name(self):
        """
        Element name.

        :return: `'Root'`
        """
        return 'Root'

    @property
    def kind(self):
        """
        Kind.

        :return: `'psdimage'`
        """
        return self.__class__.__name__.lower()

    @property
    def visible(self):
        """
        Visibility.

        :return: `True`
        """
        return True

    @property
    def left(self):
        """
        Left coordinate.

        :return: `0`
        """
        return 0

    @property
    def top(self):
        """
        Top coordinate.

        :return: `0`
        """
        return 0

    @property
    def right(self):
        """
        Right coordinate.

        :return: `int`
        """
        return self.width

    @property
    def bottom(self):
        """
        Bottom coordinate.

        :return: `int`
        """
        return self.height

    @property
    def width(self):
        """
        Document width.

        :return: `int`
        """
        return self._psd.header.width

    @property
    def height(self):
        """
        Document height.

        :return: `int`
        """
        return self._psd.header.height

    @property
    def size(self):
        """
        (width, height) tuple.

        :return: `tuple`
        """
        return self.width, self.height

    @property
    def bbox(self):
        """
        Minimal bounding box that contains all the visible layers.

        Use :py:attr:`~psd_tools2.api.psd_image.PSDImage.viewbox` to get
        viewport bounding box. When the psd is empty, bbox is equal to the
        canvas bounding box.

        :return: (left, top, right, bottom) `tuple`.
        """
        bbox = super(PSDImage, self).bbox
        if bbox == (0, 0, 0, 0):
            bbox = self.viewbox
        return bbox

    @property
    def viewbox(self):
        """
        Return bounding box of the viewport.

        :return: (left, top, right, bottom) `tuple`.
        """
        return self.left, self.top, self.right, self.bottom

    @property
    def color_mode(self):
        """
        Document color mode, such as 'RGB' or 'GRAYSCALE'. See
        :py:class:`~psd_tools2.constants.ColorMode`.

        :return: `str`
        """
        return self._psd.header.color_mode.name

    @property
    def channels(self):
        """
        Number of color channels.

        :return: `int`
        """
        return self._psd.header.channels

    @property
    def depth(self):
        """
        Pixel depth bits.

        :return: `int`
        """
        return self._psd.header.depth

    @property
    def image_resources(self):
        """
        Document image resources.

        :return: :py:class:`~psd_tools2.psd.image_resouces.ImageResouces`.
        """
        return self._psd.image_resources

    @property
    def tagged_blocks(self):
        """
        Document tagged blocks.

        :return: :py:class:`~psd_tools2.psd.tagged_blocks.TaggedBlocks` or
            None.
        """
        return self._psd.layer_and_mask_information.tagged_blocks

    def has_thumbnail(self):
        """True if the PSDImage has a thumbnail resource."""
        return ('thumbnail_resource' in self.image_resources or
                'thumbnail_resource_ps4' in self.image_resources)

    @property
    def thumbnail(self):
        """
        Returns a thumbnail image in PIL.Image. When the file does not
        contain an embedded thumbnail image, returns None.
        """
        raise NotImplementedError
        if 'thumbnail_resource' in self.image_resources:
            return pil_io.extract_thumbnail(
                self.image_resources.get_data('thumbnail_resource')
            )
        elif 'thumbnail_resource_ps4' in self.image_resources:
            return pil_support.extract_thumbnail(
                self.image_resources.get_data('thumbnail_resource_ps4'), 'BGR'
            )
        return None

    def __repr__(self):
        return (
            '%s(mode=%s size=%dx%d depth=%d channels=%d)'
        ) % (
            self.__class__.__name__, self.color_mode,
            self.width, self.height, self._psd.header.depth,
            self._psd.header.channels,
        )

    def _repr_pretty_(self, p, cycle):
        if cycle:
            return self.__repr__()

        def _pretty(layer, p):
            p.text(layer.__repr__())
            if hasattr(layer, 'clip_layers'):
                for idx, layer in enumerate(layer.clip_layers or []):
                    p.break_()
                    p.text(' +  ')
                    p.pretty(layer)
            if hasattr(layer, '__iter__'):
                with p.indent(2):
                    for idx, layer in enumerate(layer):
                        p.break_()
                        p.text('[%d] ' % idx)
                        _pretty(layer, p)

        _pretty(self, p)

    @classmethod
    def _make_header(cls, mode, size, depth=8):
        assert depth in (8, 16, 32), 'Invalid depth: %d' % (depth)
        color_mode = pil_io.get_color_mode(mode)
        alpha = int(mode.upper().endswith('A'))
        channels = ColorMode.channels(color_mode, alpha)
        return FileHeader(
            width=size[0], height=size[1], depth=depth, channels=channels,
            color_mode=color_mode
        )

    def _init(self):
        """Initialize layer structure."""
        group_stack = [self]
        clip_stack = []
        last_layer = None

        for record, channels in self._psd._iter_layers():
            current_group = group_stack[-1]

            blocks = record.tagged_blocks
            end_of_group = False
            divider = blocks.get_data('SECTION_DIVIDER_SETTING', None)
            divider = blocks.get_data('NESTED_SECTION_DIVIDER_SETTING',
                                      divider)
            if divider is not None:
                if divider.kind == SectionDivider.BOUNDING_SECTION_DIVIDER:
                    layer = Group(self._psd, None, None, current_group)
                    group_stack.append(layer)
                elif divider.kind in (SectionDivider.OPEN_FOLDER,
                                      SectionDivider.CLOSED_FOLDER):
                    layer = group_stack.pop()
                    assert layer is not self
                    layer._record = record
                    layer._channels = channels
                    end_of_group = True
            elif (
                'TYPE_TOOL_OBJECT_SETTING' in blocks or
                'TYPE_TOOL_INFO' in blocks
            ):
                layer = TypeLayer(self._psd, record, channels, current_group)
            elif (
                record.flags.pixel_data_irrelevant and (
                    'VECTOR_ORIGINATION_DATA' in blocks or
                    'VECTOR_MASK_SETTING1' in blocks or
                    'VECTOR_MASK_SETTING2' in blocks or
                    'VECTOR_STROKE_DATA' in blocks or
                    'VECTOR_STROKE_CONTENT_DATA' in blocks
                )
            ):
                layer = ShapeLayer(self._psd, record, channels, current_group)
            elif (
                'SMART_OBJECT_LAYER_DATA1' in blocks or
                'SMART_OBJECT_LAYER_DATA2' in blocks or
                'PLACED_LAYER1' in blocks or
                'PLACED_LAYER2' in blocks
            ):
                layer = SmartObjectLayer(self._psd, record, channels,
                                         current_group)
            else:
                layer = None
                for key in adjustments.TYPES.keys():
                    if key in blocks:
                        layer = adjustments.TYPES[key](
                            self._psd, record, channels, current_group
                        )
                        break
                # If nothing applies, this is a pixel layer.
                if layer is None:
                    layer = PixelLayer(
                        self._psd, record, channels, current_group
                    )

            if record.clipping == Clipping.NON_BASE:
                clip_stack.append(layer)
            else:
                if clip_stack:
                    last_layer._clip_layers = clip_stack
                clip_stack = []
                if not end_of_group:
                    current_group._layers.append(layer)
                last_layer = layer

        if clip_stack and last_layer:
            last_layer._clip_layers = clip_stack

    @classmethod
    @deprecated
    def load(kls, *args, **kwargs):
        return kls.open(*args, **kwargs)

    @classmethod
    @deprecated
    def from_stream(kls, *args, **kwargs):
        return kls.open(*args, **kwargs)

    @property
    @deprecated
    def header(self):
        return self._psd.header

    @property
    @deprecated
    def patterns(self):
        raise NotImplementedError

    @property
    @deprecated
    def image_resource_blocks(self):
        return self.image_resources

    @deprecated
    def as_PIL(self, *args, **kwargs):
        return self.topil(*args, **kwargs)

    @deprecated
    def print_tree(self):
        try:
            from IPython.lib.pretty import pprint
        except ImportError:
            from pprint import pprint
        pprint(self)
