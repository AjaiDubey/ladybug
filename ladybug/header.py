# coding=utf-8
"""Ladybug Header"""
from __future__ import division

from copy import deepcopy

from .analysisperiod import AnalysisPeriod
from .datatype import DataTypes


class Header(object):
    """DataCollection header.

    Header carries meatdata for DataCollections including data type, unit
    and analysis period.

    Attributes:
        data_type: A DataType object. (e.g. Temperature)
        unit: data_type unit (Default: None).
        analysis_period: A Ladybug analysis period (Defualt: None)
        metadata: Optional dictionary of additional metadata,
            containing information such as 'city', 'building' or 'zone'.
    """

    __slots__ = ('_data_type', '_unit', '_analysis_period', '_metadata')

    def __init__(self, data_type, unit=None,
                 analysis_period=None, metadata=None):
        """Initiate Ladybug header for lists.

        Args:
            data_type: A DataType object. (e.g. Temperature)
            unit: data_type unit (Default: None)
            analysis_period: A Ladybug analysis period (Defualt: None)
            metadata: Optional dictionary of additional metadata,
                containing information such as 'city', 'building' or 'zone'.
        """
        assert hasattr(data_type, 'isDataType'), \
            'data_type must be a Ladybug DataType. Got {}'.format(type(data_type))

        data_type = data_type
        self.set_data_type_and_unit(data_type, unit)
        self._analysis_period = AnalysisPeriod.from_analysis_period(analysis_period)
        self._metadata = metadata or {}

    @classmethod
    def from_json(cls, data):
        """Create a header from a dictionary.

        Args:
            data: {
                "data_type": {}, //Type of data (e.g. Temperature)
                "unit": string,
                "analysis_period": {} // A Ladybug AnalysisPeriod
                "metadata": {}, // A dictionary of metadata
            }
        """
        # assign default values
        keys = ('data_type', 'unit', 'analysis_period', 'metadata')
        for key in keys:
            if key not in data:
                data[key] = None

        data_type = DataTypes.type_by_name_and_unit(data['data_type'], data['unit'])
        ap = AnalysisPeriod.from_json(data['analysis_period'])
        metadata = data['metadata']
        return cls(data_type, data['unit'], ap, metadata)

    @classmethod
    def from_header(cls, header):
        """Try to generate a header from a header or a header string."""
        if hasattr(header, 'isHeader'):
            return header

        # "%s(%s)|%s|%s"
        try:
            _h = header.replace("|", "**").replace("(", "**").replace(")", "")
            return cls(*_h.split("**"))
        except Exception as e:
            raise ValueError(
                "Failed to create a Header from %s!\n%s" % (header, e))

    @property
    def data_type(self):
        """A DataType object."""
        return self._data_type

    @data_type.setter
    def data_type(self, d_typ):
        if hasattr(d_typ, 'isDataType'):
            d_typ.is_unit_acceptable(self._unit, raise_exception=True)
            self._data_type = d_typ
        else:
            d_typ_check = DataTypes.type_by_name(d_typ)
            if d_typ_check is not None:
                d_typ_check.is_unit_acceptable(self._unit, raise_exception=True)
                self._data_type = d_typ_check
            else:
                self._data_type.name = d_typ

    @property
    def unit(self):
        """A text string representing an abbreviated unit."""
        return self._unit

    @unit.setter
    def unit(self, u):
        assert self._data_type.is_unit_acceptable(u, raise_exception=True)
        self._unit = u

    @property
    def analysis_period(self):
        """A AnalysisPeriod object."""
        return self._analysis_period

    @analysis_period.setter
    def analysis_period(self, ap):
        self._analysis_period = AnalysisPeriod.from_analysis_period(ap)

    @property
    def metadata(self):
        """Metadata associated with the Header."""
        return self._metadata

    @property
    def isHeader(self):
        """Return True."""
        return True

    def set_data_type_and_unit(self, data_type, unit):
        """Set data_type and unit. This method should NOT be used for unit conversions.

        For unit conversions, the to_unit() method should be used on the data collection.
        """
        if hasattr(data_type, 'isDataType'):
            data_type.is_unit_acceptable(unit)
            self._data_type = data_type
        else:
            self._data_type = DataTypes.type_by_name_and_unit(data_type, unit)
        self._unit = unit if unit else None

    def duplicate(self):
        """Return a copy of the header."""
        return self.__class__(deepcopy(self.data_type), self.unit,
                              AnalysisPeriod.from_string(str(self.analysis_period)),
                              deepcopy(self.metadata))

    def to_tuple(self):
        """Return Ladybug header as a list."""
        return (
            self.data_type,
            self.unit,
            self.analysis_period,
            self.metadata
        )

    def __iter__(self):
        """Return data as tuple."""
        return self.to_tuple()

    def to_json(self):
        """Return a header as a dictionary."""
        return {'data_type': self.data_type.to_json(),
                'unit': self.unit,
                'analysis_period': self.analysis_period.to_json(),
                'metadata': self.metadata}

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        """Return Ladybug header as a string."""
        return "%s(%s)|%s|%s" % (
            repr(self.data_type), self.unit,
            self.analysis_period, repr(self.metadata))
