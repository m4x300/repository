"""
Script Name: rgb_sampling_distances
Description: This script is designed to work with QGIS, leveraging the PyQGIS library to create sampling points for RGB values inside polygons in order to classify these by euclidean distance by a given set of reference values (map legend)

Requirements:
- QGIS 3.36 or later
- geopandas
- os

Usage:
scroll to

Author: Maximilian Wonaschütz
Date: 2023-02-14
License: GNU General Public License v2.0

"""

from qgis.core import QgsVectorLayer, QgsField, QgsFeature, QgsProject, QgsFields, NULL, processing, QVariant, QgsVectorFileWriter, QgsVectorLayerJoinInfo, QgsProperty
from qgis.utils import iface
import geopandas as gpd
import pandas as pd
import numpy as np
import time
import os

start = time.time()

def duration(start, stop, text='Execution TIme'):
    duration = stop-start
    hours, remainder = divmod(duration, 3600)
    minutes, seconds = divmod(remainder, 60)
    formatted_duration = "{:02}h:{:02}m:{:02}s".format(int(hours), int(minutes), int(seconds))
    print(f"{text}:", formatted_duration)

def sel_bystr(gpx_str): #returns layer from TOC by searchstring
    mapcanvas = iface.mapCanvas()
    layers = mapcanvas.layers()
    pot_layers = [l for l in layers if gpx_str in l.name()]
    if len(pot_layers) == 0:
        print(f'{gpx_str} not found')
    elif len(pot_layers) == 1:
        return pot_layers[0]
    else:
        print(f'{gpx_str} matches {[l.name() for l in pot_layers]}')
  
def addFields(fieldNameList,layer, type = QVariant.Double): #double % is standard type
    for i in fieldNameList:
        fieldName = QgsField(i,type)
        if layer.dataProvider().addAttributes([fieldName]) == True:
            #print('adding field "{}"'.format(i))
            layer.updateFields()
    #else:
        #print('exists: "{}"'.format(i))

def getFIdx(fieldname, layer):
    fieldnames = layer.dataProvider().fields().names()
    if fieldname in fieldnames:
        return fieldnames.index(fieldname)
    else:
        raise Exception("{} not in fieldnames of {}".format(fieldname,layer.name()))

def euclidean_distance(p1, p2):
    return sum((a - b) ** 2 for a, b in zip(p1, p2)) ** 0.5
    
def addVlayer(query, layername, add=True):
    vlayer = QgsVectorLayer(query, layername, "virtual" )
    if add:
        QgsProject.instance().addMapLayer(vlayer)
    return vlayer

def query_calc(id, fn, ln, virtual_layer = False): #join id, fieldname, layername
    query = f'select\
    {id}, geometry,\
    c_{fn}*100/c_total as max_point_pr_{fn}, (c_{fn}*100/c_total)-min_{fn} as prop_{fn} from (\
    select {id}, st_union(geometry) as geometry, cast(count({id}) as real) as c_total,\
    count({fn}) c_{fn}, min({fn}) min_{fn}, avg({fn}) avg_{fn} from {ln} group by {id}\
    )'
    if not virtual_layer:
        return query
    else:
        return f'?query={query}'
  
def merge(list):
    result = processing.run("native:mergevectorlayers", 
    {
        'LAYERS': list, 
        'CRS': 'ProjectCrs', 
        'OUTPUT': 'memory:'
    })
    return result['OUTPUT']

def qgsvectorlayer_to_dataframe(layer, replace = True):
    attributes = [feature.attributes() for feature in layer.getFeatures()]
    column_names = [field.name() for field in layer.fields()]
    df = pd.DataFrame(attributes, columns=column_names)
    if replace:
        df.replace({NULL: np.nan}, inplace = True)
        return df
    else:
        return df


def qgsvectorlayer_to_geodataframe(layer, replace=True):
    gdf = gpd.read_file(layer.source())

    if replace:
        gdf.replace({NULL: np.nan}, inplace=True)

    return gdf

        
def df_to_memory_layer(df, layer_name='New Table'):
    layer = QgsVectorLayer(f"None?crs=EPSG:4326", layer_name, "memory")
    provider = layer.dataProvider()
    # Add fields to the layer based on the DataFrame columns
    fields = QgsFields()
    for col in df.columns:
        dtype = df[col].dtype
        if dtype == "int64":
            fields.append(QgsField(col, QVariant.Int))
        elif dtype == "float64":
            fields.append(QgsField(col, QVariant.Double))
        else:  # Handle other datatypes as string. You can add more data type conversions as needed
            fields.append(QgsField(col, QVariant.String))
    provider.addAttributes(fields)
    layer.updateFields()
    
    # Add rows to the memory layer from the DataFrame
    for _, row in df.iterrows():
        feat = QgsFeature()
        values = [row[col] for col in df.columns]
        feat.setAttributes(values)
        provider.addFeature(feat)

    layer.updateExtents()
    return layer

def geodf_to_qgsvectorlayer(gdf, filepath, layer_name='New Layer'):
    # Save GeoDataFrame to a temporary file
    temp_file = f"{filepath}{layer_name}.gpkg"
    gdf.to_file(temp_file, layer=layer_name, driver="GPKG", mode='w')

    # Load the temporary file as a QgsVectorLayer
    layer = QgsVectorLayer(temp_file, layer_name, "ogr")
    return layer

     
def sampling_points(i, o, n, raster):
    r =  processing.run('native:randompointsinpolygons', {
            'INPUT': i,
            'POINTS_NUMBER': n,
            'MIN_DISTANCE' : 0,
            'SEED': None,
            'INCLUDE_POLYGON_ATTRIBUTES': True,
            'OUTPUT': 'memory:output'})
    s = processing.run('native:rastersampling', {
            'INPUT': r['OUTPUT'],
            'COLUMN_PREFIX': 'band_',
            'RASTERCOPY': raster,
            'OUTPUT': f"memory:sampled_points{i.featureCount()}_{r['OUTPUT'].featureCount()}"
            })
    return s['OUTPUT']

def create_join(base_layer, join_layer, prop_field, cat_field):
    join_info = QgsVectorLayerJoinInfo()
    join_info.setJoinLayer(legend)
    join_info.setJoinFieldName(cat_field)
    join_info.setTargetFieldName(prop_field)
    join_info.setPrefix('')
    join_info.setUsingMemoryCache(True)
    base_layer.addJoin(join_info)
    
def makePermanent(layer, filename, layerOptions):
    transformContext = QgsProject.instance().transformContext()  # required for V3
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.layerOptions = layerOptions
    options.layerName = layer.name()
    if not os.path.exists(filename): # if the ouput file doesn't already exist
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
    else:
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
    # Write the layer to the GeoPackage
    writer = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer,
        filename,
        transformContext,
        options)
    error_code, error_message, new_file_path, new_layer_name = writer
    if error_code == QgsVectorFileWriter.NoError:
        print(f'{new_layer_name} saved successfully')
        del layer
        new_layer = QgsVectorLayer(new_file_path, new_layer_name, "ogr")
        if new_layer.isValid():
            print(f'new layer {new_layer.name()} retruned')
            return new_layer
        else:
            print("Failed to create the layer from the saved GeoPackage.")
            return None

start = time.time()

###parameters
point_density = 0.5 #per m²
ed_threshold = 65 #threshold of euclidean distance
n = QgsProperty.fromExpression(f'round($area*{point_density},0)')
sampled_points = sel_bystr("name_of_layer_sampling_points")
sampling_pts_count = sampled_points.featureCount() #for creating meaningful layer name
buildings = sel_bystr("name_of_layer_reference_geometries")
id = 'unique_id_column_of_reference_geometries'
raster = sel_bystr("name_of_rasterlayer")
####legend
legend = sel_bystr("reference_legend")
leg_rgb = ['r','g','b'] #fieldnames of rgb
category_id = 'fid' #field index for category name in legend
type_description = 'txt' #fieldname that describes the legend layers
###get field indices
leg_rgb_idx = [getFIdx(i, legend) for i in leg_rgb]
cat_id = getFIdx(category_id, legend)
###manage file handling
filebase = f'{QgsProject.instance().readPath("./")}/'

###distance calculation
leg_d = {}
sampled_points.startEditing()
for h in legend.getFeatures(): #iterating rgb values from legend
    fieldname = f'dist_{h[cat_id]}'
    leg_d[fieldname] = h[type_description] #creates a dict
    addFields([fieldname], sampled_points)
    ref_rgb = [h[g] for g in leg_rgb_idx]
    for i in sampled_points.getFeatures():
        rgb = ['band_1', 'band_2','band_3'] #default prefix qgis randompointsinpolygons
        rgb_idx = [getFIdx(i, sampled_points) for i in rgb]
        ed = euclidean_distance([i[j] for j in rgb_idx], ref_rgb)
        #ed = euclidean_distance([255 if not isinstance(i[j], int) else i[j] for j in rgb_idx], ref_rgb)
        if ed < ed_threshold:
            i.setAttribute(fieldname,ed)
        sampled_points.updateFeature(i)
sampled_points.commitChanges()
QgsProject.instance().addMapLayer(sampled_points) # required: all sampling_points w distances < ed_threshold
duration(start, time.time(), text='Distance Calculation for points')

###group sampling points by reference id 
####count/avg/min and shares are calculated in sql in query_calc
q = f'?query=select * from {buildings.name()} ' #take building layer and join:
q += " ".join([f'join({query_calc(id,k, sampled_points.name())})using({id})' for k, v in leg_d.items()])
distances = QgsVectorLayer(q, 'distances', "virtual" )
filename = f'{filebase}{distances.name()}_{distances.featureCount()}.gpkg'
distances_new = makePermanent(distances, filename, [])
duration(start, time.time(),text='Virtual layer creation')
#df = df_to_memory_layer(distances_new)
gdf = qgsvectorlayer_to_geodataframe(distances_new)
"""
####
dist_columns = [col for col in df.columns if col.startswith('min_dist_')]
dist_avg_columns = [col for col in df.columns if col.startswith('avg_dist_')]
points_columns = [col for col in df.columns if col.startswith('c_dist_')]
min_dist_category = df[dist_columns].idxmin(axis=1).str.replace("min_dist_", "")
avg_dist_category = df[dist_avg_columns].idxmin(axis=1).str.replace("avg_dist_", "")
max_points_category = df[points_columns].idxmax(axis=1).str.replace("c_dist_", "")
"""
#prop_columns = [col for col in df.columns if col.startswith('prop_dist_')]
#max_prop_category = df[prop_columns].idxmax(axis=1).str.replace("prop_dist_", "")
# Combine the results into a category string
prop_columns = [col for col in gdf.columns if col.startswith('prop_dist_')]
max_prop_category = gdf[prop_columns].astype(float).idxmax(axis=1).str.replace("prop_dist_", "")
"""
df['category_min_distance'] = min_dist_category
df['category_avg_distance'] = avg_dist_category
df['category_max_points'] = max_points_category
"""
#df['category_prop'] = max_prop_category
gdf['category_prop'] = max_prop_category.fillna(-999).astype(int)
###df reduction (nongeometrylayer)
###df = df[["osm_id", "category_prop"]]
gdf = gdf[[col for col in gdf.columns if col not in prop_columns]]
layer_name=f'prop_{buildings.name()}_{sampling_pts_count}'
prop_layer = geodf_to_qgsvectorlayer(gdf, filebase, layer_name)
#QgsProject.instance().addMapLayer(distance_layer)
QgsProject.instance().addMapLayer(prop_layer)

###adding fields for postprocessing
fields_to_add = ['cat', 'control']
addFields(fields_to_add,prop_layer, type = QVariant.Int)
"""
###take probability as granted
cat_idx = getFIdx('cat', prop_layer)
category_prop_idx = getFIdx('cat', prop_layer)
for f in prop_layer.getFeatures():
    prop_layer.changeAttributeValue(f.id(),cat_idx,f[category_prop])
prop_layer.commitChanges()
"""
create_join(prop_layer, legend, 'category_prop',category_id)
#"r"||','||"g"||','||"b"||',255' #expression for symbology

stop = time.time()
duration(start, stop)
