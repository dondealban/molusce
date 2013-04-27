# -*- coding: utf-8 -*-

#******************************************************************************
#
# MOLUSCE
# ---------------------------------------------------------
# Modules for Land Use Change Simulations
#
# Copyright (C) 2012-2013 NextGIS (info@nextgis.org)
#
# This source is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 2 of the License, or (at your option)
# any later version.
#
# This code is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# A copy of the GNU General Public License is available on the World Wide Web
# at <http://www.gnu.org/licenses/>. You can also obtain it by writing
# to the Free Software Foundation, 51 Franklin Street, Suite 500 Boston,
# MA 02110-1335 USA.
#
#******************************************************************************

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *

from algorithms.models.area_analysis.manager import AreaAnalyst
from algorithms.models.woe.manager import WoeManager

from ui.ui_weightofevidencewidgetbase import Ui_Widget

import molusceutils as utils

MAX_CATEGORIES = 15

class WeightOfEvidenceWidget(QWidget, Ui_Widget):
  def __init__(self, plugin, parent=None):
    QWidget.__init__(self, parent)
    self.setupUi(self)

    self.plugin = plugin
    self.inputs = plugin.inputs

    self.settings = QSettings("NextGIS", "MOLUSCE")

    self.btnTrainModel.clicked.connect(self.trainModel)

    self.manageGui()

  def manageGui(self):
    if not utils.checkFactors(self.inputs):
      QMessageBox.warning(self.plugin,
                          self.tr("Missed input data"),
                          self.tr("Factors rasters is not set. Please specify them and try again")
                         )
      return

    self.tblReclass.clearContents()

    row = 0

    for k, v in self.inputs["factors"].iteritems():
      for b in xrange(v.getBandsCount()):
        if len(v.getBandStat(b)['gradation']) > MAX_CATEGORIES:
          self.tblReclass.insertRow(row)
          item = QTableWidgetItem(k + self.tr(" (band %1)").arg(b))
          item.setFlags(item.flags() ^ Qt.ItemIsEditable)
          self.tblReclass.setItem(row, 0, item)
          row += 1

    self.tblReclass.resizeRowsToContents()
    self.tblReclass.resizeColumnsToContents()

  def trainModel(self):
    if not utils.checkInputRasters(self.inputs):
      QMessageBox.warning(self.plugin,
                          self.tr("Missed input data"),
                          self.tr("Initial or final raster is not set. Please specify input data and try again")
                         )
      return

    if not utils.checkFactors(self.inputs):
      QMessageBox.warning(self.plugin,
                          self.tr("Missed input data"),
                          self.tr("Factors rasters is not set. Please specify them and try again")
                         )
      return

    analyst = AreaAnalyst(self.inputs["initial"], self.inputs["final"])

    myBins = self.__getBins()

    self.model = WoeManager(self.inputs["factors"].values(), analyst, bins=myBins)

    self.model.moveToThread(self.plugin.workThread)
    self.plugin.workThread.started.connect(self.model.train)
    self.model.updateProgress.connect(self.plugin.__showProgress)
    self.model.rangeChanged.connect(self.plugin.__setProgressRange)
    self.model.processFinished.connect(self.__trainFinished)
    self.model.processFinished.connect(self.plugin.workThread.quit)

    self.plugin.workThread.start()
    self.inputs["model"] = self.model

  def __trainFinished(self):
    self.plugin.workThread.started.disconnect(self.model.train)

  def __getBins(self):
    bins = dict()
    n = 0
    for k, v in self.inputs["factors"].iteritems():
      lst = []
      for b in xrange(v.getBandsCount()):
        lst.append(None)
        if len(v.getBandStat(b)['gradation']) > MAX_CATEGORIES:
          items = self.tblReclass.findItems(k + self.tr(" (band %1)").arg(b), Qt.MatchExactly)
          idx = self.tblReclass.indexFromItem(items[0])
          reclassList = self.tblReclass.item(idx.row(), 1).text()
          lst[b] = [int(j) for j in reclassList.split(" ")]
      bins[n] = lst
      n += 1

    return bins
