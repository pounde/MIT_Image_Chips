from itertools import product

import rasterio
from tqdm import tqdm
import rasterio as rio
from rasterio import windows
import numpy as np
from pathlib import Path
from osgeo import gdal

# Configs
#####################################
RESOLUTION = 10  # In base units of CRS set below
OUT_CRS = ''  # Output CRS
SAR_IN = ''  # SAR dataset
MS_IN = ''  # Multi-spectral dataset
EO_IN = ''  # EO dataset
IMAGE_CALLS = [SAR_IN, MS_IN, EO_IN]  # List of datasets to include in image group
LOCATIONS = [('lat', 'long', 'buffer')]  # Placeholder for real data that we want images of


def reproject(in_file, dest_file, in_crs, dest_crs=OUT_CRS):

    """
    Re-project images
    :param in_file: path to file to be reprojected
    :param dest_file: path to write re-projected image
    :param in_crs: crs of input file -- only valid if image does not contain crs in metadata
    :param dest_crs: destination crs
    :return: path to re-projected image
    """

    input_raster = gdal.Open(str(in_file))

    if input_raster.GetSpatialRef() is not None:
        in_crs = input_raster.GetSpatialRef()

    if in_crs is None:
        raise ValueError('No CRS set')

    # TODO: Change the resolution based on the lowest resolution in the inputs
    gdal.Warp(str(dest_file), input_raster, dstSRS=dest_crs, srcSRS=in_crs, xRes=6e-06, yRes=6e-06)

    return Path(dest_file).resolve()


def check_dims(arr, w, h):
    """
    Check dimensions of output tiles and pad if necessary
    :param arr: numpy array
    :param w: tile width
    :param h: tile height
    :return: array of same dimensions specified
    """

    dims = arr.shape
    if dims[1] != w or dims[2] != h:
        result = np.zeros((arr.shape[0],w,h)).astype(arr.dtype)
        result[:arr.shape[0],:arr.shape[1],:arr.shape[2]] = arr
    else:
        result = arr

    return result


def get_intersect(rasters):

    """
    Computes intersect of input rasters.
    :param rasters: iterable of rasters to compute intersect
    :return: tuple of intersect (left, bottom, right, top)
    """

    bounds = None

    for r in rasters:
        with rio.open(r) as src:
            win = windows.Window(0, 0, src.width, src.height)
            if bounds:
                passed_win = src.window(*bounds)
                assert windows.intersect(win, passed_win)
                int = windows.intersection([win, passed_win])
                bounds = src.window_bounds(int)
            else:
                bounds = src.window_bounds(win)

    return bounds


def create_chips(in_raster, out_dir, intersect, tile_width=1024, tile_height=1024):

    """
    Creates chips from mosaic that fall inside the intersect
    :param in_raster: mosaic to create chips from
    :param out_dir: path to write chips
    :param intersect: bounds of chips to create
    :param tile_width: width of tiles to chip
    :param tile_height: height of tiles to chip
    :return: list of path to chips
    """

    def get_intersect_win(rio_obj):

        """
        Calculate rio window from intersect
        :param rio_obj: rio dataset
        :return: window of intersect
        """

        xy_ul = rio.transform.rowcol(rio_obj.transform, intersect[0], intersect[3])
        xy_lr = rio.transform.rowcol(rio_obj.transform, intersect[2], intersect[1])

        int_window = rio.windows.Window(xy_ul[1], xy_ul[0],
                                             abs(xy_ul[1] - xy_lr[1]),
                                             abs(xy_ul[0] - xy_lr[0]))

        return int_window

    def get_tiles(ds, width, height):

        """
        Create chip tiles generator
        :param ds: rio dataset
        :param width: tile width
        :param height: tile height
        :return: generator of rio windows and transforms for each tile to be created
        """

        intersect_window = get_intersect_win(ds)
        offsets = product(range(intersect_window.col_off, intersect_window.width + intersect_window.col_off, width),
                          range(intersect_window.row_off, intersect_window.height + intersect_window.row_off, height))
        for col_off, row_off in offsets:
            window = windows.Window(col_off=col_off, row_off=row_off, width=width, height=height).intersection(intersect_window)
            transform = windows.transform(window, ds.transform)
            yield window, transform

    chips = []

    with rio.open(in_raster) as inds:

        meta = inds.meta.copy()

        for idx, (window, transform) in enumerate(tqdm(get_tiles(inds, tile_width, tile_height))):
            meta['transform'] = transform
            meta['width'], meta['height'] = tile_width, tile_height
            output_filename = f'{idx}_{out_dir.parts[-1]}.tif'
            outpath = out_dir.joinpath(output_filename)

            with rio.open(outpath, 'w', **meta) as outds:
                chip_arr = inds.read(window=window)
                out_arr = check_dims(chip_arr, tile_width, tile_height)
                assert(out_arr.shape[1] == tile_width)
                assert(out_arr.shape[2] == tile_height)

                outds.write(out_arr)

            chips.append(outpath.resolve())

    return chips


def get_base_images(lat, long, buffer):
    # Todo: Potentially API calls to cull base rasters. I don't know how this is gonig to work
    #  from a workflow perspective. Need data sets and input from MIT folks.
    imgs = []
    for i in IMAGE_CALLS:
        pass  # API calls to get image here
        imgs.append(i)  # Append path to image
    return tuple(imgs)


def main():
    # Todo: This is all placeholder code. We need to flesh out the workflow for this.
    # Get base images -> re-project -> chip out -> discard edges??? -> return tuple of image groups
    base_images = [get_base_images(*x) for x in LOCATIONS]
    for grp in base_images:
        int = get_intersect(*grp)
        chips = tuple([create_chips(x) for x in grp])
    # re-project
    # chip
    pass


if __name__ == '__main__':
    main()