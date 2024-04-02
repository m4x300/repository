"""
Model exported as python.
Name : sampling_points
Group : 
With QGIS : 33402
"""

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterFeatureSink
import processing


class Sampling_points(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('input_polys', 'input_polys', types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))
        self.addParameter(QgsProcessingParameterRasterLayer('input_raster', 'input_raster', defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber('negativ_buffer', 'negativ_buffer', type=QgsProcessingParameterNumber.Double, minValue=-999, maxValue=0, defaultValue=-1))
        self.addParameter(QgsProcessingParameterNumber('number_of_samplingpoints', 'number_of_samplingpoints', type=QgsProcessingParameterNumber.Integer, minValue=1, defaultValue=25))
        self.addParameter(QgsProcessingParameterFeatureSink('Sampled_points', 'sampled_points', type=QgsProcessing.TypeVectorPoint, createByDefault=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(4, model_feedback)
        results = {}
        outputs = {}

        # Extract selected features
        alg_params = {
            'INPUT': parameters['input_polys'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractSelectedFeatures'] = processing.run('native:saveselectedfeatures', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Buffer
        alg_params = {
            'DISSOLVE': False,
            'DISTANCE': parameters['negativ_buffer'],
            'END_CAP_STYLE': 0,  # Round
            'INPUT': outputs['ExtractSelectedFeatures']['OUTPUT'],
            'JOIN_STYLE': 0,  # Round
            'MITER_LIMIT': 2,
            'SEGMENTS': 5,
            'SEPARATE_DISJOINT': False,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Buffer'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Random points in polygons
        alg_params = {
            'INCLUDE_POLYGON_ATTRIBUTES': True,
            'INPUT': outputs['Buffer']['OUTPUT'],
            'MAX_TRIES_PER_POINT': 10,
            'MIN_DISTANCE': 0,
            'MIN_DISTANCE_GLOBAL': 0,
            'POINTS_NUMBER': parameters['number_of_samplingpoints'],
            'SEED': None,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['RandomPointsInPolygons'] = processing.run('native:randompointsinpolygons', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Sample raster values
        alg_params = {
            'COLUMN_PREFIX': 'band_',
            'INPUT': outputs['RandomPointsInPolygons']['OUTPUT'],
            'RASTERCOPY': parameters['input_raster'],
            'OUTPUT': parameters['Sampled_points']
        }
        outputs['SampleRasterValues'] = processing.run('native:rastersampling', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Sampled_points'] = outputs['SampleRasterValues']['OUTPUT']
        return results

    def name(self):
        return 'sampling_points'

    def displayName(self):
        return 'sampling_points'

    def group(self):
        return ''

    def groupId(self):
        return ''

    def shortHelpString(self):
        return """<html><body><p><!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
<html><head><meta name="qrichtext" content="1" /><style type="text/css">
p, li { white-space: pre-wrap; }
</style></head><body style=" font-family:'MS Shell Dlg 2'; font-size:8.3pt; font-weight:400; font-style:normal;">
<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">Creation of sampling points per input polygon.</p></body></html></p>
<h2>Input parameters</h2>
<h3>input_polys</h3>
<p>Input polygons to create the sample points on. Note that only selected features are beeing used</p>
<h3>input_raster</h3>
<p>Input Raster</p>
<h3>negativ_buffer</h3>
<p>Negaive buffer. Note that a high value can cause invalid geometries</p>
<h3>number_of_samplingpoints</h3>
<p>Number of sampling points per input polygon. Parameterizing this value is adviced (e.g. point density)</p>
<h2>Outputs</h2>
<h3>sampled_points</h3>
<p>Sampled points. Note that for the RGB columns the default suffix 'band_' is used.</p>
<br></body></html>"""

    def createInstance(self):
        return Sampling_points()
