import pytest
import rasterio
from pathlib import Path
import main


class TestCheckDims:

    def test_check_dims_full_size(self):
        with rasterio.open(Path('data/test_chip.tif')) as src:
            arr = src.read()
        result = main.check_dims(arr, 1024, 1024)
        assert result.shape[1] == 1024
        assert result.shape[1] == 1024

    def test_check_dims_with_pad(self):
        with rasterio.open(Path('data/test_chip.tif')) as src:
            arr = src.read()
        result = main.check_dims(arr, 1500, 1500)
        assert result.shape[1] == 1500
        assert result.shape[1] == 1500


class TestReproject:

    def test_reproject_crs_set(self, tmp_path):
        # Test file with input having CRS set

        in_file = Path('data/crs_set.tif')
        dest_file = tmp_path / 'resample.tif'
        result = main.reproject(in_file, dest_file, None, 'EPSG:4326')
        with rasterio.open(result) as src:
            test = src.crs
        assert test == 'EPSG:4326'


    def test_reproject_no_crs_set(self, tmp_path):
        # Test file with input file having no CRS set

        in_file = Path('data/no_crs/may24C350000e4102500n.jpg')
        dest_file = tmp_path / 'resample.tif'
        result = main.reproject(in_file, dest_file, 'EPSG:26915', 'EPSG:4326')
        with rasterio.open(result) as src:
            test = src.crs
        assert test == 'EPSG:4326'


    def test_reproject_no_crs(self, tmp_path):
        # Test file with no CRS set or passed

        in_file = Path('data/no_crs/may24C350000e4102500n.jpg')
        dest_file = tmp_path / 'resample.tif'
        with pytest.raises(ValueError):
            _ = main.reproject(in_file, dest_file, None, 'EPSG:4326')


class TestCreatChips:

    def test_create_chips(self, tmp_path):

        print(tmp_path)
        out_dir = tmp_path / 'chips'
        out_dir.mkdir()
        in_mosaic = Path('data/pre_mosaic.tif')
        intersect = (-94.49960529516346, 37.06631597942802, -94.48623559881267, 37.07511383680346)
        chips = main.create_chips(in_mosaic, out_dir, intersect)

        assert len(list(out_dir.iterdir())) == 6
        with rasterio.open(list(out_dir.iterdir())[0]) as src:
            assert src.height == 1024
            assert src.width == 1024


class TestGetIntersect:

    def test_arbitrary_num_rasters(self):
        one = Path('data/pre_mosaic.tif')
        two = Path('data/post_mosaic.tif')
        three = Path('data/no_intersect/tile_31500-5137.tif')
        assert main.get_intersect([one, two, three]) == (-94.49960529516346, 37.06896983680346, -94.49346129516346, 37.07511383680346)

    def test_single_raster(self):
        one = Path('data/no_intersect/tile_31500-5137.tif')
        assert main.get_intersect([one]) == (-94.49960529516346, 37.06896983680346, -94.49346129516346, 37.07511383680346)

    def test_dont_intersect(self):
        one = Path('data/no_intersect/tile_31500-5137.tif')
        two = Path('data/no_intersect/tile_31500-6161.tif')
        with pytest.raises(AssertionError):
            assert main.get_intersect([one, two])

