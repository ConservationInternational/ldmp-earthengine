"""
Code for calculating vegetation productivity trajectory.
"""
# Copyright 2017 Conservation International

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import random
import json

import ee

from landdegradation import stats
from landdegradation import util
from landdegradation import GEEIOError

from landdegradation.schemas import GEEResults, CloudDataset, CloudUrl, GEEResultsSchema
from landdegradation.productivity import ndvi_trend, p_restrend, s_restrend, ue_trend, productivity_trajectory

# Google cloud storage bucket for output
BUCKET = "ldmt"

def run(params, logger):
    """."""
    logger.debug("Loading parameters.")
    year_start = params.get('year_start', 2001)
    year_end = params.get('year_end', 2015)
    geojson = params.get('geojson', None)
    method = params.get('method', 'ndvi_trend')
    ndvi_gee_dataset = params.get('ndvi_gee_dataset', None)
    climate_gee_dataset = params.get('climate_gee_dataset', None)

    logger.debug("Loading geojson.")
    if geojson is None:
        raise GEEIOError("Must specify an input area")
    else:
        geojson = json.loads(geojson)

    if ndvi_gee_dataset is None:
        raise GEEIOError("Must specify an NDVI dataset")

    # Check the ENV. Are we running this locally or in prod?
    if params.get('ENV') == 'dev':
        EXECUTION_ID = str(random.randint(1000000, 99999999))
    else:
        EXECUTION_ID = params.get('EXECUTION_ID', None)

    logger.debug("Running main script.")
    output = productivity_trajectory(year_start, year_end, method, 
            ndvi_gee_dataset, climate_gee_dataset, logger)

    ndvi_projection = ee.Image(ndvi_gee_dataset).projection()
    export = {'image': output.int16(),
             'description': EXECUTION_ID,
             'fileNamePrefix': EXECUTION_ID,
             'bucket': BUCKET,
             'maxPixels': 10000000000,
             'scale': ee.Number(ndvi_projection.nominalScale()).getInfo(),
             'region': util.get_coords(geojson)}

    logger.debug("Setting up GEE task.")
    task = util.gee_task(ee.batch.Export.image.toCloudStorage(**export), 
            'productivity_trajectory', logger)
    task.join()

    logger.debug("Setting up results JSON.")
    url = "https://{}.storage.googleapis.com/{}.tif".format(BUCKET, EXECUTION_ID)
    results_url = CloudUrl(url)
    cloud_dataset = CloudDataset('geotiff', method, [results_url])
    gee_results = GEEResults('productivity_trajectory', [cloud_dataset])
    results_schema = GEEResultsSchema()
    json_result = results_schema.dump(gee_results)

    return json_result.data
