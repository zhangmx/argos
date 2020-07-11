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


""" Editable table for data store
"""

import logging

from argos.utils.cls import type_name, check_class

from argos.reg.tabmodel import BaseTableModel
from argos.qt import QtCore, QtGui, QtWidgets, Qt
from argos.qt.togglecolumn import ToggleColumnTableView


logger = logging.getLogger(__name__)


class BaseTableView(ToggleColumnTableView):
    """ Editable QTableView that shows the contents of a BaseTableModel.
    """
    def __init__(self, model=None, parent=None):
        """ Constructor

            :param model: a RegistryTableModel that maps the regItems
            :param parent: the parent widget
        """
        super(BaseTableView, self).__init__(parent)

        if model is not None:
            check_class(model, BaseTableModel)
            self.setModel(model)
        else:
            assert False, "not yet implemented"

        #self.setTextElideMode(QtCore.Qt.ElideMiddle) # Does not work nicely when editing cells.
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setSortingEnabled(False)
        self.setTabKeyNavigation(False)
        self.setWordWrap(False)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        Qiv = QtWidgets.QAbstractItemView
        self.setEditTriggers(Qiv.DoubleClicked | Qiv.SelectedClicked | Qiv.EditKeyPressed)
        self.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)

        verHeader = self.verticalHeader()
        verHeader.setSectionsMovable(False)
        verHeader.hide()

        horHeader = self.horizontalHeader()
        horHeader.setDefaultAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        horHeader.setSectionResizeMode(QtWidgets.QHeaderView.Interactive) # don't set to stretch
        horHeader.setStretchLastSection(True)
        horHeader.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

        # headerSizes = [200, 300, None]  # TODO: from model?
        # # assert len(headerSizes) == model.columnCount(), \
        # #   "Size mismatch {} != {}".format(len(headerSizes), model.columnCount())
        #
        # for col, headerSize in enumerate(headerSizes):
        #     if headerSize:
        #         horHeader.resizeSection(col, headerSize)


    # def resizeEvent(self, event):
    #     """ Called when the table is resized. Automicially resizes the headers.
    #
    #         :param QtGui.QResizeEvent event: the resize event.
    #     """
    #     horHeader = self.horizontalHeader()
    #     numCols = horHeader.count()
    #
    #     for col in range(numCols):
    #         self.setColumnWidth(col, int(round(self.width() / numCols)))
    #


    def getCurrentItem(self):
        """ Returns the item of the selected row, or None if none is selected
        """
        curIdx = self.currentIndex()
        return self.model().itemFromIndex(curIdx)


    def setCurrentCell(self, row, col=0):
        """ Sets the current row and column.
        """
        cellIdx = self.model().index(row, col)
        if not cellIdx.isValid():
            logger.warning("Can't set (row = {}, col = {}) in table".format(row, col))
        else:
            logger.debug("Setting cellIdx (row = {}, col = {}) in table".format(row, col))
        self.setCurrentIndex(cellIdx)



class TableEditWidget(QtWidgets.QWidget):
    """ Widget that contains a table plus buttons to update it

    """
    def __init__(self, tableModel=None, parent=None):
        """ Constructor.
        """
        super(TableEditWidget, self).__init__(parent=parent)

        self.mainLayout = QtWidgets.QHBoxLayout()
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.mainLayout)

        self.tableView = BaseTableView(tableModel)
        self.mainLayout.addWidget(self.tableView)

        buttonLayout = QtWidgets.QVBoxLayout()
        self.mainLayout.addLayout(buttonLayout)

        self.addButton = QtWidgets.QPushButton("Add")
        self.addButton.clicked.connect(self.addRow)
        buttonLayout.addWidget(self.addButton)

        self.removeButton = QtWidgets.QPushButton("Remove")
        self.removeButton.clicked.connect(self.removeRow)
        buttonLayout.addWidget(self.removeButton)
        buttonLayout.addSpacing(25)

        self.moveUpButton = QtWidgets.QPushButton("Move Up")
        self.moveUpButton.clicked.connect(lambda: self.moveRow(-1))
        buttonLayout.addWidget(self.moveUpButton)

        self.moveDownButton = QtWidgets.QPushButton("Move Down")
        self.moveDownButton.clicked.connect(lambda: self.moveRow(+1))
        buttonLayout.addWidget(self.moveDownButton)

        buttonLayout.addStretch()

        self.tableView.selectionModel().currentChanged.connect(self.onCurrentChanged)
        self.tableView.setFocus(Qt.NoFocusReason)
        self.updateWidgets()


    def addRow(self):
        """ Adds an empty row in the plugin table
        """
        model = self.tableView.model()
        # curIdx = self.tableView.getSectionCurrentIndex()
        curIdx = self.tableView.currentIndex()
        curRow, curCol = curIdx.row(), curIdx.column()
        curRow = model.rowCount() if curRow < 0 else curRow # append at the end if non selected
        curCol = 0 if curCol < 0 else curCol
        model.insertItem(model.createItem(), row=curRow)

        self.tableView.setCurrentCell(curRow, curCol)


    def removeRow(self):
        """ Removes the currently selected row
        """
        model = self.tableView.model()
        # curIdx = self.tableView.getSectionCurrentIndex()
        curIdx = self.tableView.currentIndex()
        curRow = curIdx.row()
        if curRow < 0:
            logger.warning("No row selected so no row removed.")
            return

        model.popItemAtRow(curRow)
        self.tableView.setCurrentCell(min(curRow, model.rowCount() - 1), curIdx.column())


    def moveRow(self, number):
        """ Moves the currently selected row a with a number of positions
        """
        #curIdx = self.tableView.getSectionCurrentIndex()
        model = self.tableView.model()
        curIdx = self.tableView.currentIndex()
        curRow = curIdx.row()
        if curRow < 0:
            logger.warning("No row selected so no row moved.")
            return

        model.moveItem(curRow, curRow + number)
        newRow = max(0, min(curRow + number, model.rowCount() - 1) ) # clip
        self.tableView.setCurrentCell(newRow, curIdx.column())


    def onCurrentChanged(self, _curIdx, _prefIdx):
        """ Called when the current table index changes
        """
        self.updateWidgets()


    def updateWidgets(self):
        """ Enables/disables widgets according to the selected row
        """
        row = self.tableView.currentIndex().row()
        numRows = self.tableView.model().rowCount()

        self.addButton.setEnabled(True)
        self.removeButton.setEnabled(0 <= row < numRows)
        self.moveUpButton.setEnabled(1 <= row < numRows)
        self.moveDownButton.setEnabled(0 <= row < numRows-1)



def main():
    """ Test classes
    """
    import sys
    from pprint import pprint

    from PyQt5 import QtWidgets

    from argos import info
    from argos.utils.misc import make_log_format
    from argos.qt.misc import handleException
    from argos.reg.tabmodel import BaseTableModel, BaseItemStore, BaseItem

    info.DEBUGGING = True
    sys.excepthook = handleException

    logging.basicConfig(level="DEBUG", format=make_log_format())


    app = QtWidgets.QApplication([])

    store = BaseItemStore()


    model = BaseTableModel(store)

    window = TableEditWidget(tableModel=model)
    window.show()

    exitCode = app.exec()

    print("edited store")
    pprint(store.marshall())





if __name__ == "__main__":
    main()
