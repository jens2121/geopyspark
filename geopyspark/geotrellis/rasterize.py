from shapely.wkb import dumps
from geopyspark import get_spark_context
from geopyspark.geotrellis.constants import LayerType, CellType, Partitioner
from geopyspark.geotrellis.layer import TiledRasterLayer
from geopyspark.geotrellis.protobufserializer import ProtoBufSerializer

from geopyspark.vector_pipe.vector_pipe_protobufcodecs import (feature_cellvalue_decoder,
                                                               feature_cellvalue_encoder)


__all__ = ['rasterize', 'rasterize_features']


def rasterize(geoms,
              crs,
              zoom,
              fill_value,
              cell_type=CellType.FLOAT64,
              options=None,
              num_partitions=None,
              partitioner=Partitioner.HASH_PARTITIONER):
    """Rasterizes a Shapely geometries.

    Args:
        geoms ([shapely.geometry] or (shapely.geometry) or pyspark.RDD[shapely.geometry]): Either
            a list, tuple, or a Python RDD of shapely geometries to rasterize.
        crs (str or int): The CRS of the input geometry.
        zoom (int): The zoom level of the output raster.
        fill_value (int or float): Value to burn into pixels intersectiong geometry
        cell_type (str or :class:`~geopyspark.geotrellis.constants.CellType`): Which data type the
            cells should be when created. Defaults to ``CellType.FLOAT64``.
        options (:class:`~geopyspark.geotrellis.RasterizerOptions`, optional): Pixel intersection options.
        num_partitions (int, optional): The number of repartitions Spark will make when the data is
            repartitioned. If ``None``, then the data will not be repartitioned.
        partitioner (str or :class:`~geopyspark.geotrellis.constants.Partitioner, optional): The partitioner
            that will be used to partition the resulting layer. Defaults to ``Partitioner.HASH_PARTITIONER``.

    Returns:
        :class:`~geopyspark.geotrellis.layer.TiledRasterLayer`
    """

    if isinstance(crs, int):
        crs = str(crs)

    pysc = get_spark_context()
    rasterizer = pysc._gateway.jvm.geopyspark.geotrellis.SpatialTiledRasterLayer.rasterizeGeometry
    partitioner = Partitioner(partitioner).value

    if isinstance(geoms, (list, tuple)):
        wkb_geoms = [dumps(g) for g in geoms]

        srdd = rasterizer(pysc._jsc.sc(),
                          wkb_geoms,
                          crs,
                          zoom,
                          float(fill_value),
                          CellType(cell_type).value,
                          options,
                          num_partitions,
                          partitioner)

    else:
        wkb_rdd = geoms.map(lambda geom: dumps(geom))

        # If this is False then the WKBs will be serialized
        # when going to Scala resulting in garbage
        wkb_rdd._bypass_serializer = True

        srdd = rasterizer(wkb_rdd._jrdd.rdd(),
                          crs,
                          zoom,
                          float(fill_value),
                          CellType(cell_type).value,
                          options,
                          num_partitions,
                          partitioner)

    return TiledRasterLayer(LayerType.SPATIAL, srdd)


def rasterize_features(features,
                       crs,
                       zoom,
                       cell_type=CellType.FLOAT64,
                       options=None,
                       num_partitions=None,
                       zindex_cell_type=CellType.INT8,
                       partitioner=Partitioner.HASH_PARTITIONER):
    """Rasterizes a collection of :class:`~geopyspark.vector_pipe.Feature`\s.

    Args:
        features (pyspark.RDD[Feature]): A Python ``RDD`` that
            contains :class:`~geopyspark.vector_pipe.Feature`\s.

            Note:
                The ``properties`` of each ``Feature`` must be an instance of
                :class:`~geopyspark.vector_pipe.CellValue`.
        crs (str or int): The CRS of the input geometry.
        zoom (int): The zoom level of the output raster.

            Note:
                Not all rasterized ``Feature``\s may be present in the resulting layer
                if the ``zoom`` is not high enough.
        cell_type (str or :class:`~geopyspark.geotrellis.constants.CellType`): Which data type the
            cells should be when created. Defaults to ``CellType.FLOAT64``.
        options (:class:`~geopyspark.geotrellis.RasterizerOptions`, optional): Pixel intersection options.
        num_partitions (int, optional): The number of repartitions Spark will make when the data is
            repartitioned. If ``None``, then the data will not be repartitioned.
        zindex_cell_type (str or :class:`~geopyspark.geotrellis.constants.CellType`): Which data type
            the ``Z-Index`` cells are. Defaults to ``CellType.INT8``.
        partitioner (str or :class:`~geopyspark.geotrellis.constants.Partitioner, optional): The partitioner
            that will be used to partition the resulting layer. Defaults to ``Partitioner.HASH_PARTITIONER``.


    Returns:
        :class:`~geopyspark.geotrellis.layer.TiledRasterLayer`
    """

    if isinstance(crs, int):
        crs = str(crs)

    partitioner = Partitioner(partitioner).value

    pysc = get_spark_context()
    rasterizer = pysc._gateway.jvm.geopyspark.geotrellis.SpatialTiledRasterLayer.rasterizeFeaturesWithZIndex

    ser = ProtoBufSerializer(feature_cellvalue_decoder, feature_cellvalue_encoder)
    reserialized_rdd = features._reserialize(ser)

    srdd = rasterizer(reserialized_rdd._jrdd.rdd(),
                      crs,
                      zoom,
                      CellType(cell_type).value,
                      options,
                      num_partitions,
                      CellType(zindex_cell_type).value,
                      partitioner)

    return TiledRasterLayer(LayerType.SPATIAL, srdd)
