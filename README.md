# RGB-Sampling

This repository contains a few tools based on PyQGS that help classififying polygon layers (buildings, parcels, buildingblocks) according to a reference table of RGB-values.

## Background

The tools were developed for ['urban_geodata'](https://urban-geodata.at) - a project dealing with digitizing old thematic map stock on the institute for urban and regional research (ISR) on the Austrian academy of sciences (ÖAW) and was funded by [Internet Privatstiftung Austria](https://www.internetstiftung.at/).
The categories of these maps that are rendered as monochromatic signatures can be classified using euclidean distance calculation in the RGB colorspace and propabilities based on sampling points - hence the name.

## Preconditions

In order to make good use of the scripts here the following prerequisites are necessary:
* a georeferenced thematic map, using monochromatic area fills
* a suitable polygon layer that fits the map's areas
* QGIS 3.16 or later

## How-To

The area signatures of a map's legend are digitized, then using the 
`sampling_points.model3` or its python equivalent is applied and sampling points are beeing generated that contain the RGB values of the signature's icons. The average/median rgb values are grouped by the digitized icon geometry and serve as reference value for the classification of a polygon layer.
The same model can be used to generate the sampling points for the poygon layer, however it's functionality is also incorporated into `rgb_sampling_distances.py` This file also contains an overview of the filterparameters such as point density, distance threshold etc.
A more detailed description (in german) can be found [here](https://www.netidee.at/urbangeodata/euklidische-distanz).
![flowchart of rgb_sampling_distances.py](https://www.netidee.at/sites/default/files/styles/inline_image/public/inline-images/flowchart.jpg)



