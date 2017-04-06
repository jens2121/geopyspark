import os
import unittest
import rasterio
import numpy as np

from shapely.geometry import Point
from geopyspark.geotrellis.tile_layer import costdistance
from geopyspark.tests.base_test_class import BaseTestClass
from geopyspark.geotrellis.constants import SPATIAL


class CostDistanceTest(BaseTestClass):
    geopysc = BaseTestClass.geopysc

    data = np.array([[
        [1.0, 1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0, 0.0]]])

    layer = [({'row': 0, 'col': 0}, {'no_data_value': -1.0, 'data': data}),
             ({'row': 1, 'col': 0}, {'no_data_value': -1.0, 'data': data}),
             ({'row': 0, 'col': 1}, {'no_data_value': -1.0, 'data': data}),
             ({'row': 1, 'col': 1}, {'no_data_value': -1.0, 'data': data})]
    rdd = geopysc.pysc.parallelize(layer)

    extent = {'xmin': 0.0, 'ymin': 0.0, 'xmax': 33.0, 'ymax': 33.0}
    layout = {'layoutCols': 2, 'layoutRows': 2, 'tileCols': 5, 'tileRows': 5}
    metadata = {'cellType': 'float32ud-1.0',
                'extent': extent,
                'crs': '+proj=longlat +datum=WGS84 +no_defs ',
                'bounds': {
                    'minKey': {'col': 0, 'row': 0},
                    'maxKey': {'col': 1, 'row': 1}},
                'layoutDefinition': {
                    'extent': extent,
                    'tileLayout': {'tileCols': 5, 'tileRows': 5, 'layoutCols': 2, 'layoutRows': 2}}}

    def test_costdistance_finite(self):
        def zero_one(kv):
            k = kv[0]
            return (k['col'] == 0 and k['row'] == 1)

        result = costdistance(geopysc=self.geopysc,
                              rdd_type=SPATIAL,
                              keyed_rdd=self.rdd,
                              metadata=self.metadata,
                              geometries=[Point(13, 13)],
                              max_distance=144000.0)

        tile = result.filter(zero_one).first()[1]
        point_distance = tile['data'][0][1][3]
        self.assertEqual(point_distance, 0.0)

    def test_costdistance_infinite(self):
        def zero_one(kv):
            k = kv[0]
            return (k['col'] == 0 and k['row'] == 1)

        result = costdistance(geopysc=self.geopysc,
                              rdd_type=SPATIAL,
                              keyed_rdd=self.rdd,
                              metadata=self.metadata,
                              geometries=[Point(13, 13)],
                              max_distance=float('inf'))

        tile = result.filter(zero_one).first()[1]
        point_distance = tile['data'][0][0][0]
        self.assertTrue(point_distance > 1250000)

if __name__ == "__main__":
    unittest.main()