import pandas as pd
import rasterio
from rasterio import warp
from pathlib import Path
from PIL import Image
import numpy as np
import requests
from io import BytesIO
from time import sleep
import timeit

###############################################
# Set parameters here
###############################################
DATA_DIR = Path('data_sample/AOI_11_Rotterdam')  # Base directory of data directory
IN_IMG_DIR = 'SAR-Intensity'  # Path from DATA_DIR to directory of images to match new maps images with
MAP_DIR = 'Map'  # Path from DATA_DIR to directory where new map images will live
MAPBOX_API_KEY = ''  # Mapbox API key
STYLE_USER = 'epound'  # Along with STYLE_ID, don't change unless you want to change the map style
STYLE_ID = 'ckpb8wcyx03rh17mttq4zoza8'  # This style contains no labels
###############################################

# Concat our output directory and create if it doesn't exist
OUT_DIR = Path(DATA_DIR / MAP_DIR)
OUT_DIR.mkdir(exist_ok=True)

# Start our timer
t0 = timeit.default_timer()

df = pd.read_csv(DATA_DIR / 'SummaryData/SN6_TrainSample_AOI_11_Rotterdam_Buildings.csv')
imgs = list(df.ImageId.unique())

for img in imgs:

    print(f'Gathering map for image {img}')
    new_file = OUT_DIR / f'{img}.tif'

    # Get our bounds to build the URL
    with rasterio.open(f'{DATA_DIR}/{IN_IMG_DIR}/SN6_Train_AOI_11_Rotterdam_{IN_IMG_DIR}_{img}.tif') as src:
        im_bounds = list(warp.transform_bounds(src.crs, 'EPSG:4326', *src.bounds))

        # Get meta to pass to input data
        meta = src.meta.copy()
        meta['transform'] = src.transform

        # Reset meta for our outputs
        meta['count'] = 3
        meta['dtype'] = 'uint8'

        # Build API call and request our image
        url = f'https://api.mapbox.com/styles/v1/{STYLE_USER}/{STYLE_ID}/static/{im_bounds}/{src.width}x{src.height}?access_token={MAPBOX_API_KEY}&attribution=false&logo=false'
        r = requests.get(url)

        # Read in our data and convert it to RGB
        map_im = Image.open(BytesIO(r.content))
        map_conv = map_im.convert(mode='RGB')

        # Get our image as an np array and set axes for rio
        a = np.asarray(map_conv)
        move = np.moveaxis(np.asarray(a), [0, 1, 2], [1, 2, 0])

        # Add geospatial data and write
        with rasterio.open(new_file, 'w', **meta) as outds:
            outds.write(move)

        # Sleep to prevent getting rate limited (1,250/hr)
        sleep(.05)

elapsed = timeit.default_timer() - t0
print(f'Run complete in {elapsed / 60:.3f} min')
