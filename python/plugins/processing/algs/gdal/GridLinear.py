# -*- coding: utf-8 -*-

"""
***************************************************************************
    GridLinear.py
    ---------------------
    Date                 : September 2017
    Copyright            : (C) 2017 by Alexander Bruy
    Email                : alexander dot bruy at gmail dot com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Alexander Bruy'
__date__ = 'September 2017'
__copyright__ = '(C) 2017, Alexander Bruy'

import os

from qgis.PyQt.QtGui import QIcon

from qgis.core import (QgsRasterFileWriter,
                       QgsProcessing,
                       QgsProcessingParameterDefinition,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterExtent,
                       QgsProcessingParameterField,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterString,
                       QgsProcessingParameterRasterDestination)
from processing.algs.gdal.GdalAlgorithm import GdalAlgorithm
from processing.algs.gdal.GdalUtils import GdalUtils

pluginPath = os.path.split(os.path.split(os.path.dirname(__file__))[0])[0]


class GridLinear(GdalAlgorithm):

    INPUT = 'INPUT'
    Z_FIELD = 'Z_FIELD'
    WIDTH = 'WIDTH'
    HEIGHT = 'HEIGHT'
    UNITS = 'UNITS'
    EXTENT = 'EXTENT'
    RADIUS = 'RADIUS'
    NODATA = 'NODATA'
    OPTIONS = 'OPTIONS'
    EXTRA = 'EXTRA'
    DATA_TYPE = 'DATA_TYPE'
    OUTPUT = 'OUTPUT'

    TYPES = ['Byte', 'Int16', 'UInt16', 'UInt32', 'Int32', 'Float32', 'Float64', 'CInt16', 'CInt32', 'CFloat32', 'CFloat64']

    def __init__(self):
        super().__init__()

    def initAlgorithm(self, config=None):
        self.units = [self.tr("Pixels"),
                self.tr("Georeferenced units")]
        self.addParameter(QgsProcessingParameterFeatureSource(self.INPUT,
                                                              self.tr('Point layer'),
                                                              [QgsProcessing.TypeVectorPoint]))

        z_field_param = QgsProcessingParameterField(self.Z_FIELD,
                                                    self.tr('Z value from field'),
                                                    None,
                                                    self.INPUT,
                                                    QgsProcessingParameterField.Numeric,
                                                    optional=True)
        z_field_param.setFlags(z_field_param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(z_field_param)

        self.addParameter(QgsProcessingParameterEnum(self.UNITS,
                                                     self.tr('Output raster size units'),
                                                     self.units,
                                                     optional=True))
        self.addParameter(QgsProcessingParameterNumber(self.WIDTH,
                                                       self.tr('Width/Horizontal resolution'),
                                                       type=QgsProcessingParameterNumber.Double,
                                                       minValue=0.0,
                                                       defaultValue=0.0,
                                                       optional=True))
        self.addParameter(QgsProcessingParameterNumber(self.HEIGHT,
                                                       self.tr('Height/Vertical resolution'),
                                                       type=QgsProcessingParameterNumber.Double,
                                                       minValue=0.0,
                                                       defaultValue=0.0,
                                                       optional=True))
        self.addParameter(QgsProcessingParameterExtent(self.EXTENT,
                                                       self.tr('Output extent'),
                                                       optional=True))

        self.addParameter(QgsProcessingParameterNumber(self.RADIUS,
                                                       self.tr('Search distance '),
                                                       type=QgsProcessingParameterNumber.Double,
                                                       minValue=-1.0,
                                                       defaultValue=-1.0))
        self.addParameter(QgsProcessingParameterNumber(self.NODATA,
                                                       self.tr('NODATA marker to fill empty points'),
                                                       type=QgsProcessingParameterNumber.Double,
                                                       defaultValue=0.0))

        options_param = QgsProcessingParameterString(self.OPTIONS,
                                                     self.tr('Additional creation options'),
                                                     defaultValue='',
                                                     optional=True)
        options_param.setFlags(options_param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        options_param.setMetadata({
            'widget_wrapper': {
                'class': 'processing.algs.gdal.ui.RasterOptionsWidget.RasterOptionsWidgetWrapper'}})
        self.addParameter(options_param)

        extra_param = QgsProcessingParameterString(self.EXTRA,
                                                   self.tr('Additional command-line parameters'),
                                                   defaultValue=None,
                                                   optional=True)
        extra_param.setFlags(extra_param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(extra_param)

        dataType_param = QgsProcessingParameterEnum(self.DATA_TYPE,
                                                    self.tr('Output data type'),
                                                    self.TYPES,
                                                    allowMultiple=False,
                                                    defaultValue=5)
        dataType_param.setFlags(dataType_param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(dataType_param)

        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT,
                                                                  self.tr('Interpolated (Linear)')))

    def name(self):
        return 'gridlinear'

    def displayName(self):
        return self.tr('Grid (Linear)')

    def group(self):
        return self.tr('Raster analysis')

    def groupId(self):
        return 'rasteranalysis'

    def icon(self):
        return QIcon(os.path.join(pluginPath, 'images', 'gdaltools', 'grid.png'))

    def commandName(self):
        return 'gdal_grid'

    def getConsoleCommands(self, parameters, context, feedback, executing=True):
        ogrLayer, layerName = self.getOgrCompatibleSource(self.INPUT, parameters, context, feedback, executing)

        arguments = [
            '-l',
            layerName
        ]
        fieldName = self.parameterAsString(parameters, self.Z_FIELD, context)
        if fieldName:
            arguments.append('-zfield')
            arguments.append(fieldName)

        units = self.parameterAsEnum(parameters, self.UNITS, context)
        if units == 0:
            arguments.append('-outsize')
        else:
            arguments.append('-tr')
        arguments.append(self.parameterAsDouble(parameters, self.WIDTH, context))
        arguments.append(self.parameterAsDouble(parameters, self.HEIGHT, context))

        extent = self.parameterAsExtent(parameters, self.EXTENT, context)
        if not extent.isNull():
            arguments.append('-txe')
            arguments.append(extent.xMinimum())
            arguments.append(extent.xMaximum())
            arguments.append('-tye')
            arguments.append(extent.yMinimum())
            arguments.append(extent.yMaximum())

        params = 'linear'
        params += ':radius={}'.format(self.parameterAsDouble(parameters, self.RADIUS, context))
        params += ':nodata={}'.format(self.parameterAsDouble(parameters, self.NODATA, context))

        arguments.append('-a')
        arguments.append(params)
        arguments.append('-ot')
        arguments.append(self.TYPES[self.parameterAsEnum(parameters, self.DATA_TYPE, context)])

        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
        self.setOutputValue(self.OUTPUT, out)
        arguments.append('-of')
        arguments.append(QgsRasterFileWriter.driverForExtension(os.path.splitext(out)[1]))

        options = self.parameterAsString(parameters, self.OPTIONS, context)
        if options:
            arguments.extend(GdalUtils.parseCreationOptions(options))

        if self.EXTRA in parameters and parameters[self.EXTRA] not in (None, ''):
            extra = self.parameterAsString(parameters, self.EXTRA, context)
            arguments.append(extra)

        arguments.append(ogrLayer)
        arguments.append(out)

        return [self.commandName(), GdalUtils.escapeAndJoin(arguments)]
