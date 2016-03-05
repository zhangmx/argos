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

""" Repository Tree Items (RTIs) for netCDF data.

    It uses the netCDF4 package to open netCDF files.
    See http://unidata.github.io/netcdf4-python/
"""

import logging, os
from netCDF4 import Dataset, Variable, Dimension

from libargos.qt import QtGui
from libargos.utils.cls import check_class
from libargos.repo.baserti import BaseRti
from libargos.repo.iconfactory import RtiIconFactory

logger = logging.getLogger(__name__)

ICON_COLOR_NCDF4 = '#0088FF'


    
class NcdfDimensionRti(BaseRti):
    """ Repository Tree Item (RTI) that contains a NCDF group. 
    """     
    _defaultIconGlyph = RtiIconFactory.DIMENSION
    _defaultIconColor = ICON_COLOR_NCDF4
    
    def __init__(self, ncDim, nodeName, fileName=''):
        """ Constructor
        """
        super(NcdfDimensionRti, self).__init__(nodeName, fileName=fileName)
        check_class(ncDim, Dimension)

        self._ncDim = ncDim
        
    def hasChildren(self):
        """ Returns False. Dimension items never have children. 
        """
        return False

    @property
    def attributes(self):
        """ The attributes dictionary.
        """
        return {'unlimited': str(self._ncDim.isunlimited())}
        #size = self._ncDim.size
        #return {'size': 'unlimited' if size is None else str(size)}
    
    


class NcdfFieldRti(BaseRti):
    """ Repository Tree Item (RTI) that contains a field in a compound NCDF variable.
    """
    _defaultIconGlyph = RtiIconFactory.FIELD
    _defaultIconColor = ICON_COLOR_NCDF4

    def __init__(self, ncVar, nodeName, fileName=''):
        """ Constructor.
            The name of the field must be given to the nodeName parameter.
        """
        super(NcdfFieldRti, self).__init__(nodeName, fileName=fileName)
        check_class(ncVar, Variable)

        self._ncVar = ncVar

    def hasChildren(self):
        """ Returns False. Field items never have children.
        """
        return False


    @property
    def isSliceable(self):
        """ Returns True because the underlying data can be sliced.
        """
        return True


    def __getitem__(self, index):
        """ Called when using the RTI with an index (e.g. rti[0]).
            Applies the index on the NCDF variable that contain this field and then selects the
            current field. In pseudo-code, it returns: self.h5Dataset[index][self.nodeName].

            If the field itself contains a sub-array it returns:
                self.h5Dataset[mainArrayIndex][self.nodeName][subArrayIndex]
        """
        mainArrayNumDims = self._ncVar.ndim
        mainIndex = index[:mainArrayNumDims]
        mainArray = self._ncVar.__getitem__(mainIndex)
        fieldArray = mainArray[self.nodeName]
        subIndex = tuple([Ellipsis]) + index[mainArrayNumDims:]
        slicedArray = fieldArray[subIndex]
        return slicedArray


    @property
    def nDims(self):
        """ The number of dimensions of the underlying array
        """
        return self._ncVar.ndim + len(self._subArrayShape)


    @property
    def _subArrayShape(self):
        """ Returns the shape of the sub-array
            An empty tuple is returned for regular fields, which have no sub array.
        """
        if self._ncVar.dtype.fields is None:
            return tuple() # regular field # TODO: does this occur?
        else:
            fieldName = self.nodeName
            fieldDtype = self._ncVar.dtype.fields[fieldName][0]
            return fieldDtype.shape


    @property
    def arrayShape(self):
        """ Returns the shape of the underlying array.
            If the field contains a subarray the shape may be longer than 1.
        """
        return self._ncVar.shape + self._subArrayShape


    @property
    def elementTypeName(self):
        """ String representation of the element type.
        """
        fieldName = self.nodeName
        return str(self._ncVar.dtype.fields[fieldName][0])


    @property
    def attributes(self):
        """ The attributes dictionary.
            Returns the attributes of the variable that contains this field.
        """
        ncVar = self._ncVar
        try:
            return ncVar.__dict__
        except Exception as ex:
            # Due to some internal error netCDF4 may raise an AttributeError or KeyError,
            # depending on its version.
            logger.warn("Unable to read the attributes from {}. Reason: {}"
                        .format(self.nodeName, ex))
            return {}


    @property
    def dimensionNames(self):
        """ Returns a list with the dimension names of the underlying NCDF variable
        """
        nSubDims = len(self._subArrayShape)
        subArrayDims = ['SubDim{}'.format(dimNr) for dimNr in range(nSubDims)]
        return list(self._ncVar.dimensions + tuple(subArrayDims))



class NcdfVariableRti(BaseRti):
    """ Repository Tree Item (RTI) that contains a NCDF variable. 
    """ 
    _defaultIconGlyph = RtiIconFactory.ARRAY
    _defaultIconColor = ICON_COLOR_NCDF4
    
    def __init__(self, ncVar, nodeName, fileName=''):
        """ Constructor
        """
        super(NcdfVariableRti, self).__init__(nodeName, fileName=fileName)
        check_class(ncVar, Variable)
        self._ncVar = ncVar

        try:
            self._isCompound = bool(self._ncVar.dtype.names)
        except (AttributeError, KeyError): 
            # If dtype is a string instead of an numpy dtype, netCDF4 raises a KeyError 
            # or AttributeError, depending on its version.
            self._isCompound = False
            
    def hasChildren(self):
        """ Returns True if the variable has a compound type, otherwise returns False.
        """
        return self._isCompound


    @property
    def isSliceable(self):
        """ Returns True because the underlying data can be sliced.
        """
        return True


    def __getitem__(self, index):
        """ Called when using the RTI with an index (e.g. rti[0]).
            Passes the index through to the underlying array.
        """
        return self._ncVar.__getitem__(index)


    @property
    def nDims(self):
        """ The number of dimensions of the underlying array
        """
        return self._ncVar.ndim


    @property
    def arrayShape(self):
        """ Returns the shape of the underlying array.
        """
        return self._ncVar.shape


    @property
    def attributes(self):
        """ The attributes dictionary.
            Returns the attributes of the variable that contains this field.
        """
        ncVar = self._ncVar
        try:
            return ncVar.__dict__
        except Exception as ex:
            # Due to some internal error netCDF4 may raise an AttributeError or KeyError,
            # depending on its version.
            logger.warn("Unable to read the attributes from {}. Reason: {}"
                        .format(self.nodeName, ex))
            return {}

    
    @property
    def elementTypeName(self):
        """ String representation of the element type.
        """        
        dtype =  self._ncVar.dtype 
        return '<compound>' if dtype.names else str(dtype) # TODO: what if dtype.names does not exist
    
               
    @property
    def dimensionNames(self):
        """ Returns a list with the dimension names of the underlying NCDF variable
        """
        return self._ncVar.dimensions
    
#    TODO: how to get this?
#    @property
#    def dimensionGroupPaths(self):
#        """ Returns a list with, for every dimension, the path of the group that contains it.
#        """
#        return [dim.group().path for dim in self._ncVar.dimensions.values()] # TODO: cache?
#    
                   
    def _fetchAllChildren(self):
        """ Fetches all fields that this variable contains. 
            Only variables with a compound data type can have fields.
        """        
        assert self.canFetchChildren(), "canFetchChildren must be True"

        childItems = []

        # Add fields
        if self._isCompound:
            for fieldName in self._ncVar.dtype.names:
                childItems.append(NcdfFieldRti(self._ncVar, nodeName=fieldName, fileName=self.fileName))
                        
        self._childrenFetched = True
        return childItems
    
    
    
class NcdfGroupRti(BaseRti):
    """ Repository Tree Item (RTI) that contains a NCDF group. 
    """     
    _defaultIconGlyph = RtiIconFactory.FOLDER
    _defaultIconColor = ICON_COLOR_NCDF4
    
    def __init__(self, ncGroup, nodeName, fileName=''):
        """ Constructor
        """
        super(NcdfGroupRti, self).__init__(nodeName, fileName=fileName)
        check_class(ncGroup, Dataset, allow_none=True)

        self._ncGroup = ncGroup
        self._childrenFetched = False
        
    @property
    def attributes(self):
        """ The attributes dictionary.
        """
        return self._ncGroup.__dict__ if self._ncGroup else {}
        
                   
    def _fetchAllChildren(self):
        """ Fetches all sub groups and variables that this group contains.
        """
        assert self._ncGroup is not None, "dataset undefined (file not opened?)"
        assert self.canFetchChildren(), "canFetchChildren must be True"
        
        childItems = []

        # Add dimensions
        for dimName, ncDim in self._ncGroup.dimensions.items():
            childItems.append(NcdfDimensionRti(ncDim, nodeName=dimName, fileName=self.fileName))
        
        # Add groups
        for groupName, ncGroup in self._ncGroup.groups.items():
            childItems.append(NcdfGroupRti(ncGroup, nodeName=groupName, fileName=self.fileName))
            
        # Add variables
        for varName, ncVar in self._ncGroup.variables.items():
            childItems.append(NcdfVariableRti(ncVar, nodeName=varName, fileName=self.fileName))
                        
        self._childrenFetched = True
        return childItems
    


class NcdfFileRti(NcdfGroupRti):
    """ Repository tree item that contains a netCDF file.
    """
    _defaultIconGlyph = RtiIconFactory.FILE
    _defaultIconColor = ICON_COLOR_NCDF4
        
    def __init__(self, nodeName, fileName=''):
        """ Constructor
        """
        super(NcdfFileRti, self).__init__(None, nodeName, fileName=fileName)
        self._checkFileExists()
    
    def _openResources(self):
        """ Opens the root Dataset.
        """
        logger.info("Opening: {}".format(self._fileName))
        self._ncGroup = Dataset(self._fileName)
    
    def _closeResources(self):
        """ Closes the root Dataset.
        """
        logger.info("Closing: {}".format(self._fileName))
        self._ncGroup.close()
        self._ncGroup = None
