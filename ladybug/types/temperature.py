# coding=utf-8
"""Temperature data type."""
from __future__ import division

from ._base import DataTypeBase


class Temperature(DataTypeBase):
    """Temperature"""
    _units = ('C', 'F', 'K')
    _si_units = ('C', 'K')
    _ip_units = ('F')
    _min = -273.15
    _abbreviation = 'T'

    def _C_to_F(self, value):
        return value * 9. / 5. + 32.

    def _C_to_K(self, value):
        return value + 273.15

    def _F_to_C(self, value):
        return (value - 32.) * 5. / 9.

    def _K_to_C(self, value):
        return value - 273.15

    def to_unit(self, values, unit, from_unit):
        """Return values in a given unit given the input from_unit."""
        return self._to_unit_base('C', values, unit, from_unit)

    def to_ip(self, values, from_unit):
        """Return values in IP given the input from_unit."""
        if from_unit == 'F':
            return values, from_unit
        else:
            return self.to_unit(values, 'F', from_unit), 'F'

    def to_si(self, values, from_unit):
        """Return values in SI given the input from_unit."""
        if from_unit == 'C' or from_unit == 'K':
            return values, from_unit
        else:
            return self.to_unit(values, 'C', from_unit), 'C'

    @property
    def isTemperature(self):
        """Return True."""
        return True


class DryBulbTemperature(Temperature):
    _abbreviation = 'DBT'
    _min_epw = -70
    _max_epw = 70
    _missing_epw = 99.9


class DewPointTemperature(Temperature):
    _abbreviation = 'DPT'
    _min_epw = -70
    _max_epw = 70
    _missing_epw = 99.9


class SkyTemperature(Temperature):
    _abbreviation = 'Tsky'


class AirTemperature(Temperature):
    _abbreviation = 'Tair'


class RadiantTemperature(Temperature):
    _abbreviation = 'Trad'


class OperativeTemperature(Temperature):
    _abbreviation = 'To'


class MeanRadiantTemperature(Temperature):
    _abbreviation = 'MRT'


class StandardEffectiveTemperature(Temperature):
    _abbreviation = 'SET'


class UniversalThermalClimateIndex(Temperature):
    _abbreviation = 'UTCI'
