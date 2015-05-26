# -*- coding: utf-8 -*-
# This file is part of Argos.
# 
# Argos is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Argos is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Argos. If not, see <http://www.gnu.org/licenses/>.

""" Collector Widget. 
"""
from __future__ import print_function

import logging

from libargos.collect.collectortree import CollectorTree
from libargos.repo.baserti import BaseRti
from libargos.qt import QtGui, QtCore, QtSignal, QtSlot
from libargos.utils.cls import check_class, check_is_a_sequence
from libargos.widgets.constants import (TOP_DOCK_HEIGHT)

logger = logging.getLogger(__name__)

# Qt classes have many ancestors
#pylint: disable=R0901

class Collector(QtGui.QWidget): 
    """ Widget for collecting the selected data. 
        Consists of a tree to collect the VisItems, plus some buttons to add or remove then.
        
        The CollectorTree only stores the VisItems, the intelligence is located in the Collector 
        itself.
    """
    FAKE_DIM_NAME = '-' # The name of the fake dimension with length 1
    FAKE_DIM_IDX  = -999    

    contentsChanged = QtSignal()         
    
    def __init__(self):
        """ Constructor
        """
        super(Collector, self).__init__()
    
        self._rti = None
        
        self._signalsBlocked = False
        self.COL_FIRST_COMBO = 1  
        self._comboLabels = []  # Will be set in clearAndSetComboBoxes
        self._comboBoxes = []   # Will be set in clearAndSetComboBoxes
        self._spinBoxes = []    # Will be set in createSpinBoxes 
        
        self.layout = QtGui.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.buttonLayout = QtGui.QVBoxLayout()
        self.layout.setContentsMargins(2, 0, 2, 0)

        # Add tree
        self.tree = CollectorTree(self)
        self.layout.addWidget(self.tree)
        
        # Add buttons
        self.addVisItemButton = QtGui.QPushButton("Add")
        self.addVisItemButton.setEnabled(False) # not yet implemented
        self.buttonLayout.addWidget(self.addVisItemButton, stretch=0)
        self.removeVisItemButton = QtGui.QPushButton("Remove")
        self.removeVisItemButton.setEnabled(False) # not yet implemented
        self.buttonLayout.addWidget(self.removeVisItemButton, stretch=0)
        self.buttonLayout.addStretch(stretch=1)
        self.layout.addLayout(self.buttonLayout, stretch=0)
                
        self.clearAndSetComboBoxes(['X-Axis', 'Y-Axis'])
        
        
    def sizeHint(self):
        """ The recommended size for the widget."""
        return QtCore.QSize(300, TOP_DOCK_HEIGHT)
    
    @property
    def rti(self):
        """ The current repo tree item. Can be None.
            Do not store references to this as it may be removed by the user!
        """
        return self._rti


    @property
    def comboLabels(self):
        """ Returns a copy of the combobox labels (since they are read only) """
        return tuple(self._comboLabels)    


    @property
    def maxCombos(self):
        """ Returns the maximum number of combo boxes """
        return len(self._comboLabels)
    

    def dimensionNameByNumber(self, dimNr):
        """ Returns a dimension name (e.g. Dim0) to be used for unnamed dimensions.
        """
        return "dimension{}".format(dimNr)
    
    
    def blockChildrenSignals(self, block):
        """ If block equals True, the signals of the combo boxes and spin boxes are blocked
            Returns the old blocking state.
        """
        for spinBox in self._spinBoxes:
            spinBox.blockSignals(block)
        for comboBox in self._comboBoxes:
            comboBox.blockSignals(block)
        result = self._signalsBlocked
        self._signalsBlocked = block
        return result
            
            
    def clear(self):
        """ Removes all VisItems
        """
        model = self.tree.model()
        # Don't use model.clear(). it will delete the column sizes 
        model.removeRows(0, 1)
        model.setRowCount(1)
        #model.setColumnCount(6)
    
    
    def clearAndSetComboBoxes(self, comboLabels):
        """ Removes all VisItems before setting the new degree.
        """
        check_is_a_sequence(comboLabels)
        row = 0
        self._deleteComboBoxes(row)
        self.clear()
        self._setComboLabels(comboLabels)
        self._createComboBoxes(row)


    def _setComboLabels(self, comboLabels):
        """ Sets the comboLables and updates the headers. Removes old values first. 
        """
        for col, label in enumerate(self._comboLabels, self.COL_FIRST_COMBO):
            self._setHeaderLabel(col, '')
            
        self._comboLabels = comboLabels
        
        for col, label in enumerate(self._comboLabels, self.COL_FIRST_COMBO):
            self._setHeaderLabel(col, label)
            

    def _setHeaderLabel(self, col, text):
        """ Sets the header of column col to text.
            Will increase the number of columns if col is larger than the current number.
        """
        model = self.tree.model()
        item = model.horizontalHeaderItem(col)
        if item:
            item.setText(text)
        else:
            model.setHorizontalHeaderItem(col, QtGui.QStandardItem(text))
            

    @QtSlot(BaseRti)
    def setRti(self, rti):
        """ Updates the current VisItem from the contents of the repo tree item.
        
            Is a slot but the signal is usually connected to the Collector, which then call
            this function directly.
        """
        check_class(rti, BaseRti)
        #assert rti.asArray is not None, "rti must have array" # TODO: maybe later
        
        self._rti = rti
        
        row = 0
        model = self.tree.model()

        self._deleteSpinBoxes(row)
        
        # Create path label
        pathItem = QtGui.QStandardItem(rti.nodePath)
        pathItem.setEditable(False)
        model.setItem(row, 0, pathItem)
        
        self._populateComboBoxes(row)
        self._createSpinBoxes(row)
    
        logging.debug("Emitting contentsChanged signal (rti changed)")
        self.contentsChanged.emit()
        
                
    def _createComboBoxes(self, row):
        """ Creates a combo box for each of the comboLabels
        """  
        tree = self.tree
        model = self.tree.model()
        
        for col, _comboLabel in enumerate(self.comboLabels, self.COL_FIRST_COMBO):
            if col >= model.columnCount():
                model.setColumnCount(col + 1)
                
            logger.debug("Adding combobox at ({}, {})".format(row, col))
            comboBox = QtGui.QComboBox()
            comboBox.activated.connect(self._comboBoxActivated)
            self._comboBoxes.append(comboBox)
            
            #editor = LabeledWidget(QtGui.QLabel(comboLabel), comboBox)
            tree.setIndexWidget(model.index(row, col), comboBox) 
            

    def _deleteComboBoxes(self, row):
        """ Deletes all comboboxes of a row
        """
        tree = self.tree
        model = self.tree.model()
        
        for col in range(self.COL_FIRST_COMBO, self.maxCombos):
            logger.debug("Removing combobox at: {}, {}".format(row, col))
            tree.setIndexWidget(model.index(row, col), None)
                     
        self._comboBoxes = []
            

    def _populateComboBoxes(self, row):
        """ Populates the comboboxes with values of the repo tree item
        """
        logger.debug("_populateComboBoxes")
        for comboBox in self._comboBoxes:
            comboBox.clear()
            
        if self._rti is None or self._rti.asArray is None:
            return
        
        nDims = self._rti.asArray.ndim
        
        for comboBoxNr, comboBox in enumerate(self._comboBoxes):
            # Add a fake dimension of length 1
            comboBox.addItem(self.FAKE_DIM_NAME, userData = self.FAKE_DIM_IDX)
            
            for dimNr in range(nDims):
                comboBox.addItem(self.dimensionNameByNumber(dimNr), userData=dimNr)
                        
                # We set the nth combo-box index to the last item - n. This because the 
                # NetCDF-CF conventions have the preferred dimension order of T, Z, Y, X. 
                comboBox.setCurrentIndex(max(0, nDims - comboBoxNr))
            
            
    def _comboBoxDimensionIndex(self, comboBox):
        """ Returns the dimension index from the user data of the currently item of the combo box.
        """
        return comboBox.itemData(comboBox.currentIndex())  
    
                
    def _dimensionSelectedInComboBox(self, dimNr):
        """ Returns True if the dimension is selected in one of the combo boxes.
        """
        for combobox in self._comboBoxes:
            if self._comboBoxDimensionIndex(combobox) == dimNr:
                return True
        return False
            
            
    def _createSpinBoxes(self, row):
        """ Creates a spinBox for each dimension that is not selected in a combo box. 
        """
        assert len(self._spinBoxes) == 0, "Spinbox list not empty. Call _deleteSpinBoxes first"
        
        if self._rti is None or self._rti.asArray is None:
            return     

        logger.debug("_createSpinBoxes, array shape: {}".format(self._rti.asArray.shape))
        
        tree = self.tree
        model = self.tree.model()
        col = self.COL_FIRST_COMBO + self.maxCombos
                        
        for dimNr, dimSize in enumerate(self._rti.asArray.shape):
            
            if self._dimensionSelectedInComboBox(dimNr):
                continue
            
            spinBox = QtGui.QSpinBox()
            self._spinBoxes.append(spinBox)
            
            spinBox.setKeyboardTracking(False)
            spinBox.setCorrectionMode(QtGui.QAbstractSpinBox.CorrectToNearestValue)
            #spinBox.setMinimumWidth(...)
            spinBox.setMinimum(0)
            spinBox.setMaximum(dimSize - 1)
            spinBox.setSingleStep(1)
            spinBox.setValue(dimSize // 2) # select the middle of the slice
            spinBox.setPrefix("{}: ".format(self.dimensionNameByNumber(dimNr)))
            spinBox.setSuffix("/{}".format(spinBox.maximum()))
            
            # This must be done after setValue to prevent emitting too many signals
            spinBox.valueChanged[int].connect(self._SpinboxValueChanged)

            #spinboxLabel = QtGui.QLabel(self.dimensionNameByNumber(dimNr))
            #editor = LabeledWidget(spinboxLabel, spinBox)

            if col >= model.columnCount():
                model.setColumnCount(col + 1)
                self._setHeaderLabel(col, '')
                
            logger.debug("_createSpinBoxes, adding at ({}, {})".format(row, col))                
            tree.setIndexWidget(model.index(row, col), spinBox)
            col += 1                         
                    

    def _deleteSpinBoxes(self, row):
        """ Removes all spinboxes
        """
        tree = self.tree
        model = self.tree.model()
        
        for col, _spinBox in enumerate(self._spinBoxes, self.COL_FIRST_COMBO + self.maxCombos):
            # TODO: disconnect spinbox.
            tree.setIndexWidget(model.index(row, col), None)
        self._spinBoxes = [] 

            
    @QtSlot(int)
    def _comboBoxActivated(self, index, comboBox=None):
        """ Is called when a combo box value was changed by the user.
        
            Updates the spin boxes and sets other combo boxes having the same index to 
            the fake dimension of length 1.
        """
        if comboBox is None:
            comboBox = self.sender()
        assert comboBox, "comboBox not defined and not the sender"
        
        blocked = self.blockChildrenSignals(True)
        
        # If one of the other combo boxes has the same value, set it to the fake dimension
        curDimIdx = self._comboBoxDimensionIndex(comboBox)
        if curDimIdx != self.FAKE_DIM_IDX:
            otherComboBoxes = [cb for cb in self._comboBoxes if cb is not comboBox]
            for otherComboBox in otherComboBoxes:
                if otherComboBox.currentIndex() == comboBox.currentIndex():
                    newIdx = otherComboBox.findData(self.FAKE_DIM_IDX)
                    otherComboBox.setCurrentIndex(newIdx)
        
        # Show only spin boxes that are not selected
        row = 0       
        self._deleteSpinBoxes(row)
        self._createSpinBoxes(row)
                            
        self.blockChildrenSignals(blocked)
        
        logging.debug("Emitting contentsChanged signal (comboBox)")
        self.contentsChanged.emit()
        
        
    @QtSlot(int)
    def _SpinboxValueChanged(self, index, spinBox=None):
        """ Is called when a spin box value was changed.
        
            Updates the spin boxes and sets other combo boxes having the same index to 
            the fake dimension of length 1.
        """
        if spinBox is None:
            spinBox = self.sender()
        assert spinBox, "spinBox not defined and not the sender"

        logging.debug("Emitting contentsChanged signal (spinBox)")
        self.contentsChanged.emit()
        
