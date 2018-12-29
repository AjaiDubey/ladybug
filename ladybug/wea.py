# coding=utf-8
from __future__ import division
"""Wea weather file."""
from .epw import EPW
from .stat import STAT
from .location import Location
from .dt import DateTime
from .header import Header
from .datacollection import DataCollection
from .datatype import DataPoint
from .analysisperiod import AnalysisPeriod
from .sunpath import Sunpath
from .euclid import Vector3
from .futil import write_to_file

from .skymodel import ashrae_revised_clear_sky
from .skymodel import ashrae_clear_sky
from .skymodel import zhang_huang_solar_split

import math
import os

try:
    from itertools import izip as zip
    readmode = 'rb'
    writemode = 'wb'
except ImportError:
    # python 3
    xrange = range
    readmode = 'r'
    writemode = 'w'
    xrange = range


class Wea(object):
    """An annual WEA object containing solar irradiance.

    Attributes:
        location: Ladybug location object.
        direct_normal_irradiance: An annual DataCollection of direct normal irradiance
            values.
        diffuse_horizontal_irradiance: An annual DataCollection of diffuse horizontal
            irradiance values for every hourly timestep of the year.
        timestep: An optional integer to set the number of time steps per hour.
            Default is 1 for one value per hour.
        is_leap_year: A boolean to indicate if values are representing a leap year.
            Default is False.
    """

    def __init__(self, location, direct_normal_irradiance,
                 diffuse_horizontal_irradiance, timestep=1, is_leap_year=False):
        """Create a wea object."""
        timestep = timestep or 1
        self._timestep = timestep
        self._is_leap_year = is_leap_year
        assert isinstance(timestep, int), 'timestep must be an' \
            ' integer. Got {}'.format(type(timestep))

        self.location = location
        self.direct_normal_irradiance = direct_normal_irradiance
        self.diffuse_horizontal_irradiance = diffuse_horizontal_irradiance

    @classmethod
    def from_values(cls, location, direct_normal_irradiance,
                    diffuse_horizontal_irradiance, timestep=1, is_leap_year=False):
        """Create wea from a list of irradiance values.

        This method converts input lists to DataCollection.
        """
        err_message = 'For timestep %d, %d number of data for %s is expected. ' \
            '%d is provided.'
        if len(direct_normal_irradiance) % cls.hr_count(is_leap_year) == 0:
            # add extra information to err_message
            err_message = err_message + ' Did you forget to set the timestep to %d?' \
                % (len(direct_normal_irradiance) / cls.hr_count(is_leap_year))

        assert len(direct_normal_irradiance) / timestep == cls.hr_count(is_leap_year), \
            err_message % (timestep, timestep * cls.hr_count(is_leap_year),
                           'direct normal irradiance', len(
                               direct_normal_irradiance))

        assert len(diffuse_horizontal_irradiance) / timestep == \
            cls.hr_count(is_leap_year), \
            err_message % (timestep, timestep * cls.hr_count(is_leap_year),
                           'diffuse_horizontal_irradiance', len(
                               direct_normal_irradiance))

        dnr, dhr = cls._get_empty_data_collections(location, timestep, is_leap_year)
        dts = cls._get_datetimes(timestep, is_leap_year)
        for dir_norm, diff_horiz, dt in zip(direct_normal_irradiance,
                                            diffuse_horizontal_irradiance, dts):
            dnr.append(DataPoint(dir_norm, dt, 'SI', 'Direct Normal Irradiance'))
            dhr.append(DataPoint(diff_horiz, dt, 'SI', 'Diffuse Horizontal Irradiance'))
        return cls(location, dnr, dhr, timestep, is_leap_year)

    @classmethod
    def from_json(cls, data):
        """ Create Wea from json file
            {
            "location": {} , // ladybug location schema
            "direct_normal_irradiance": [], // List of hourly direct normal
                irradiance data points
            "diffuse_horizontal_irradiance": [], // List of hourly diffuse
                horizontal irradiance data points
            "timestep": float //timestep between measurements, default is 1
            }
        """
        required_keys = ('location', 'direct_normal_irradiance',
                         'diffuse_horizontal_irradiance')
        optional_keys = ('timestep', 'is_leap_year')

        for key in required_keys:
            assert key in data, 'Required key "{}" is missing!'.format(key)

        for key in optional_keys:
            if key not in data:
                data[key] = None

        location = Location.from_json(data['location'])
        direct_normal_irradiance = \
            DataCollection.from_json(data['direct_normal_irradiance'])
        diffuse_horizontal_irradiance = \
            DataCollection.from_json(data['diffuse_horizontal_irradiance'])
        timestep = data['timestep']
        is_leap_year = data['is_leap_year']

        return cls(location, direct_normal_irradiance,
                   diffuse_horizontal_irradiance, timestep, is_leap_year)

    # TOD(mostapha): If decided that this is a good idea, also parse datetime from wea
    # file. It is currently auto-generated based on timestep to ensure it will be
    # consistent with other studies.
    @classmethod
    def from_file(cls, weafile, timestep=1, is_leap_year=False):
        """Create wea object from a wea file.

        Args:
            weafile:Full path to wea file.
            timestep: An optional integer to set the number of time steps per hour.
                Default is 1 for one value per hour. If the wea file has a time step
                smaller than an hour adjust this input accordingly.
            is_leap_year: A boolean to indicate if values are representing a leap year.
                Default is False.
        """
        assert os.path.isfile(weafile), 'Failed to find {}'.format(weafile)
        location = Location()
        with open(weafile, readmode) as weaf:
            first_line = weaf.readline()
            assert first_line.startswith('place'), \
                'Failed to find place in header. ' \
                '{} is not a valid wea file.'.format(weafile)
            location.city = ' '.join(first_line.split()[1:])
            # parse header
            location.latitude = float(weaf.readline().split()[-1])
            location.longitude = -float(weaf.readline().split()[-1])
            location.time_zone = -int(weaf.readline().split()[-1]) / 15
            location.elevation = float(weaf.readline().split()[-1])
            weaf.readline()  # pass line for weather data units

            # parse irradiance values
            direct_normal_irradiance = []
            diffuse_horizontal_irradiance = []
            for line in weaf:
                dirn, difh = [int(v) for v in line.split()[-2:]]
                direct_normal_irradiance.append(dirn)
                diffuse_horizontal_irradiance.append(difh)

        return cls.from_values(location, direct_normal_irradiance,
                               diffuse_horizontal_irradiance, timestep, is_leap_year)

    @classmethod
    def from_epw_file(cls, epwfile, timestep=1):
        """Create a wea object using the solar irradiance values in an epw file.

        Args:
            epwfile: Full path to epw weather file.
            timestep: An optional integer to set the number of time steps per hour.
                Default is 1 for one value per hour. Note that this input
                will only do a linear interpolation over the data in the EPW
                file.  While such linear interpolations are suitable for most
                thermal simulations, where thermal lag "smooths over" the effect
                of momentary increases in solar energy, it is not recommended
                for daylight simulations, where momentary increases in solar
                energy can mean the difference between glare and visual comfort.
        """
        epw = EPW(epwfile)
        direct_normal = epw.direct_normal_radiation
        diffuse_horizontal = epw.diffuse_horizontal_radiation
        direct_normal.header.set_data_type_and_unit(
            'Direct Normal Irradiance', 'W/m2')
        diffuse_horizontal.header.set_data_type_and_unit(
            'Diffuse Horizontal Irradiance', 'W/m2')
        if timestep != 1:
            print ("Note: timesteps greater than 1 on epw-generated Wea's \n" +
                   "are suitable for thermal models but are not recommended \n" +
                   "for daylight models.")
            # interpolate the data
            direct_norm_values = direct_normal.interpolate_data(timestep)
            diffuse_horiz_values = diffuse_horizontal.interpolate_data(timestep)
            # build empty dta collections
            direct_normal, diffuse_horizontal = \
                cls._get_empty_data_collections(epw.location, timestep, False)
            # create sunpath to check if the sun is up at a given timestep
            sp = Sunpath.from_location(epw.location)
            # add correct values to the emply data collection
            for e_beam, e_diff in zip(direct_norm_values, diffuse_horiz_values):
                # set irradiance values to 0 when the sun is not up
                sun = sp.calculate_sun_from_date_time(e_beam.datetime)
                if sun.altitude > 0:
                    direct_normal.append(e_beam)
                    diffuse_horizontal.append(e_diff)
                else:
                    direct_normal.append(DataPoint(
                        0, e_beam.datetime, 'SI', 'Direct Normal Irradiance'))
                    diffuse_horizontal.append(DataPoint(
                        0, e_diff.datetime, 'SI', 'Diffuse Horizontal Irradiance'))
        else:
            # add half an hour to datetime to put sun in the middle of the hour
            for dnr in direct_normal:
                dnr.datetime = dnr.datetime.add_minute(30)
            for dhr in diffuse_horizontal:
                dhr.datetime = dhr.datetime.add_minute(30)

        # epw file is always for 8760 hours
        is_leap_year = False
        return cls(epw.location, direct_normal, diffuse_horizontal,
                   timestep, is_leap_year)

    @classmethod
    def from_stat_file(cls, statfile, timestep=1, is_leap_year=False):
        """Create an ASHRAE Revised Clear Sky wea object from the monthly sky
        optical depths in a .stat file.

        Args:
            statfile: Full path to the .stat file.
            timestep: An optional integer to set the number of time steps per
                hour. Default is 1 for one value per hour.
            is_leap_year: A boolean to indicate if values are representing a leap year.
                Default is False.
        """
        stat = STAT(statfile)

        # check to be sure the stat file does not have missing tau values
        def check_missing(opt_data, data_name):
            if opt_data == []:
                raise ValueError('Stat file contains no optical data.')
            for i, x in enumerate(opt_data):
                if x is None:
                    raise ValueError(
                        'Missing optical depth data for {} at month {}'.format(
                            data_name, i)
                    )
        check_missing(stat.monthly_tau_beam, 'monthly_tau_beam')
        check_missing(stat.monthly_tau_diffuse, 'monthly_tau_diffuse')

        return cls.from_ashrae_revised_clear_sky(stat.location, stat.monthly_tau_beam,
                                                 stat.monthly_tau_diffuse, timestep,
                                                 is_leap_year)

    @classmethod
    def from_ashrae_revised_clear_sky(cls, location, monthly_tau_beam,
                                      monthly_tau_diffuse, timestep=1,
                                      is_leap_year=False):
        """Create a wea object representing an ASHRAE Revised Clear Sky ("Tau Model")

        ASHRAE Revised Clear Skies are intended to determine peak solar load
        and sizing parmeters for HVAC systems.  The revised clear sky is
        currently the default recommended sky model used to autosize HVAC
        systems in EnergyPlus. For more information on the ASHRAE Revised Clear
        Sky model, see the EnergyPlus Engineering Reference:
        https://bigladdersoftware.com/epx/docs/8-9/engineering-reference/climate-calculations.html

        Args:
            location: Ladybug location object.
            monthly_tau_beam: A list of 12 float values indicating the beam
                optical depth of the sky at each month of the year.
            monthly_tau_diffuse: A list of 12 float values indicating the
                diffuse optical depth of the sky at each month of the year.
            timestep: An optional integer to set the number of time steps per
                hour. Default is 1 for one value per hour.
            is_leap_year: A boolean to indicate if values are representing a leap year.
                Default is False.
        """
        # build empty dta collections
        direct_norm_rad, diffuse_horiz_rad = \
            cls._get_empty_data_collections(location, timestep, is_leap_year)

        # create sunpath and get altitude at every timestep of the year
        sp = Sunpath.from_location(location)
        sp.is_leap_year = is_leap_year
        altitudes = [[] for i in range(12)]
        dates = cls._get_datetimes(timestep, is_leap_year)
        for t_date in dates:
            sun = sp.calculate_sun_from_date_time(t_date)
            altitudes[sun.datetime.month - 1].append(sun.altitude)

        # run all of the months through the ashrae_revised_clear_sky model
        i_dt = 0
        for i_mon, alt_list in enumerate(altitudes):
            dir_norm_rad, dif_horiz_rad = ashrae_revised_clear_sky(
                alt_list, monthly_tau_beam[i_mon], monthly_tau_diffuse[i_mon])
            for e_beam, e_diff in zip(dir_norm_rad, dif_horiz_rad):
                direct_norm_rad.append(DataPoint(
                    e_beam, dates[i_dt], 'SI', 'Direct Normal Irradiance'))
                diffuse_horiz_rad.append(DataPoint(
                    e_diff, dates[i_dt], 'SI', 'Diffuse Horizontal Irradiance'))
                i_dt += 1

        return cls(location, direct_norm_rad, diffuse_horiz_rad, timestep, is_leap_year)

    @classmethod
    def from_ashrae_clear_sky(cls, location, sky_clearness=1, timestep=1,
                              is_leap_year=False):
        """Create a wea object representing an original ASHRAE Clear Sky.

        The original ASHRAE Clear Sky is intended to determine peak solar load
        and sizing parmeters for HVAC systems.  It is not the sky model
        currently recommended by ASHRAE since it usually overestimates the
        amount of solar irradiance in comparison to the newer ASHRAE Revised
        Clear Sky ("Tau Model"). However, the original model here is still
        useful for cases where monthly optical depth values are not known. For
        more information on the ASHRAE Clear Sky model, see the EnergyPlus
        Engineering Reference:
        https://bigladdersoftware.com/epx/docs/8-9/engineering-reference/climate-calculations.html

        Args:
            location: Ladybug location object.
            sky_clearness: A factor that will be multiplied by the output of
                the model. This is to help account for locations where clear,
                dry skies predominate (e.g., at high elevations) or,
                conversely, where hazy and humid conditions are frequent. See
                Threlkeld and Jordan (1958) for recommended values. Typical
                values range from 0.95 to 1.05 and are usually never more
                than 1.2. Default is set to 1.0.
            timestep: An optional integer to set the number of time steps per
                hour. Default is 1 for one value per hour.
            is_leap_year: A boolean to indicate if values are representing a leap year.
                Default is False.
        """
        # build empty dta collections
        direct_norm_rad, diffuse_horiz_rad = \
            cls._get_empty_data_collections(location, timestep, is_leap_year)

        # create sunpath and get altitude at every timestep of the year
        sp = Sunpath.from_location(location)
        sp.is_leap_year = is_leap_year
        altitudes = [[] for i in range(12)]
        dates = cls._get_datetimes(timestep, is_leap_year)
        for t_date in dates:
            sun = sp.calculate_sun_from_date_time(t_date)
            altitudes[sun.datetime.month - 1].append(sun.altitude)

        # compute hourly direct normal and diffuse horizontal irradiance
        i_dt = 0
        for i_mon, alt_list in enumerate(altitudes):
            dir_norm_rad, dif_horiz_rad = ashrae_clear_sky(
                alt_list, i_mon + 1, sky_clearness)
            for e_beam, e_diff in zip(dir_norm_rad, dif_horiz_rad):
                direct_norm_rad.append(DataPoint(
                    e_beam, dates[i_dt], 'SI', 'Direct Normal Irradiance'))
                diffuse_horiz_rad.append(DataPoint(
                    e_diff, dates[i_dt], 'SI', 'Diffuse Horizontal Irradiance'))
                i_dt += 1

        return cls(location, direct_norm_rad, diffuse_horiz_rad, timestep, is_leap_year)

    @classmethod
    def from_zhang_huang_solar(cls, location, cloud_cover,
                               relative_humidity, dry_bulb_temperature,
                               wind_speed, atmospheric_pressure=None,
                               timestep=1, is_leap_year=False, use_disc=False):
        """Create a wea object from climate data using the Zhang-Huang model.

        The Zhang-Huang solar model was developed to estimate solar
        irradiance for weather stations that lack such values, which are
        typically colleted with a pyranometer. Using total cloud cover,
        dry-bulb temperature, relative humidity, and wind speed as
        inputs the Zhang-Huang estimates global horizontal irradiance
        by means of a regression model across these variables.
        For more information on the Zhang-Huang model, see the
        EnergyPlus Engineering Reference:
        https://bigladdersoftware.com/epx/docs/8-7/engineering-reference/climate-calculations.html#zhang-huang-solar-model

        Args:
            location: Ladybug location object.
            cloud_cover: A list of annual float values between 0 and 1
                that represent the fraction of the sky dome covered
                in clouds (0 = clear; 1 = completely overcast)
            relative_humidity: A list of annual float values between
                0 and 100 that represent the relative humidity in percent.
            dry_bulb_temperature: A list of annual float values that
                represent the dry bulb temperature in degrees Celcius.
            wind_speed: A list of annual float values that
                represent the wind speed in meters per second.
            atmospheric_pressure: An optional list of float values that
                represent the atmospheric pressure in Pa.  If None or
                left blank, pressure at sea level will be used (101325 Pa).
            timestep: An optional integer to set the number of time steps per
                hour. Default is 1 for one value per hour.
            is_leap_year: A boolean to indicate if values are representing a leap year.
                Default is False.
            use_disc: Set to True to use the original DISC model as opposed to the
                newer and more accurate DIRINT model. Default is False.
        """
        # check input data
        assert len(cloud_cover) == len(relative_humidity) == \
            len(dry_bulb_temperature) == len(wind_speed), \
            'lengths of input climate data must match.'
        assert len(cloud_cover) / timestep == cls.hr_count(is_leap_year), \
            'input climate data must be annual.'
        assert isinstance(timestep, int), 'timestep must be an' \
            ' integer. Got {}'.format(type(timestep))
        if atmospheric_pressure is not None:
            assert len(atmospheric_pressure) == len(cloud_cover), \
                'length pf atmospheric_pressure must match the other input lists.'
        else:
            atmospheric_pressure = [101325] * cls.hr_count(is_leap_year) * timestep

        # initiate sunpath based on location
        sp = Sunpath.from_location(location)
        sp.is_leap_year = is_leap_year

        # calculate parameters needed for zhang-huang irradiance
        date_times = []
        altitudes = []
        doys = []
        dry_bulb_t3_hrs = []
        for count, t_date in enumerate(cls._get_datetimes(timestep, is_leap_year)):
            date_times.append(t_date)
            sun = sp.calculate_sun_from_date_time(t_date)
            altitudes.append(sun.altitude)
            doys.append(sun.datetime.doy)
            dry_bulb_t3_hrs.append(dry_bulb_temperature[count - (3 * timestep)])

        # calculate zhang-huang irradiance
        dir_ir, diff_ir = zhang_huang_solar_split(altitudes, doys, cloud_cover,
                                                  relative_humidity,
                                                  dry_bulb_temperature,
                                                  dry_bulb_t3_hrs, wind_speed,
                                                  atmospheric_pressure, use_disc)

        # assemble the results into DataCollections
        direct_norm_rad, diffuse_horiz_rad = \
            cls._get_empty_data_collections(location, timestep, is_leap_year)
        for dni, dhi, t_date in zip(dir_ir, diff_ir, date_times):
            direct_norm_rad.append(DataPoint(
                dni, t_date, 'SI', 'Direct Normal Irradiance'))
            diffuse_horiz_rad.append(DataPoint(
                dhi, t_date, 'SI', 'Diffuse Horizontal Irradiance'))

        return cls(location, direct_norm_rad, diffuse_horiz_rad, timestep, is_leap_year)

    @property
    def isWea(self):
        """Return True."""
        return True

    @property
    def hoys(self):
        """Hours of the year in wea file."""
        return tuple(data.datetime.hoy for data in self.direct_normal_irradiance)

    @property
    def datetimes(self):
        """Datetimes in wea file."""
        return tuple(data.datetime for data in self.direct_normal_irradiance)

    @property
    def timestep(self):
        """Return the timestep."""
        return self._timestep

    @property
    def direct_normal_irradiance(self):
        """Get or set the direct normal irradiance."""
        return self._direct_normal_irradiance

    @direct_normal_irradiance.setter
    def direct_normal_irradiance(self, data):
        assert isinstance(data, DataCollection), 'direct_normal_irradiance data' \
            ' must be a data collection. Got {}'.format(type(data))
        assert len(data) / self.timestep == self.hr_count(self.is_leap_year), \
            'direct_normal_irradiance data must be annual.'
        self._direct_normal_irradiance = data

    @property
    def diffuse_horizontal_irradiance(self):
        """Get or set the diffuse horizontal irradiance."""
        return self._diffuse_horizontal_irradiance

    @diffuse_horizontal_irradiance.setter
    def diffuse_horizontal_irradiance(self, data):
        assert isinstance(data, DataCollection), 'diffuse_horizontal_irradiance data' \
            ' must be a data collection. Got {}'.format(type(data))
        assert len(data) / self.timestep == self.hr_count(self.is_leap_year), \
            'diffuse_horizontal_irradiance data must be annual.'
        self._diffuse_horizontal_irradiance = data

    @property
    def global_horizontal_irradiance(self):
        """Returns the global horizontal irradiance at each timestep."""
        analysis_period = AnalysisPeriod(timestep=self.timestep,
                                         is_leap_year=self.is_leap_year)
        header_ghr = Header(analysis_period=analysis_period,
                            data_type='Global Horizontal Irradiance',
                            unit='W/m2',
                            location=self.location)
        global_horizontal_rad = DataCollection(header=header_ghr)
        is_leap_year = self.is_leap_year
        sp = Sunpath.from_location(self.location)
        sp.is_leap_year = is_leap_year
        for dnr, dhr in zip(self.direct_normal_irradiance,
                            self.diffuse_horizontal_irradiance):
            sun = sp.calculate_sun_from_date_time(dnr.datetime)
            glob_h = dhr + dnr * math.sin(math.radians(sun.altitude))
            global_horizontal_rad.append(
                DataPoint(glob_h, dnr.datetime, 'SI', 'Global Horizontal Irradiance'))
        return global_horizontal_rad

    @property
    def direct_horizontal_irradiance(self):
        """Returns the direct irradiance on a horizontal surface at each timestep.

        Note that this is different from the direct_normal_irradiance needed
        to construct a Wea, which is NORMAL and not HORIZONTAL."""
        analysis_period = AnalysisPeriod(timestep=self.timestep,
                                         is_leap_year=self.is_leap_year)
        header_dhr = Header(analysis_period=analysis_period,
                            data_type='Direct Horizontal Irradiance',
                            unit='W/m2',
                            location=self.location)
        direct_horizontal_rad = DataCollection(header=header_dhr)
        is_leap_year = self.is_leap_year
        sp = Sunpath.from_location(self.location)
        sp.is_leap_year = is_leap_year
        for dnr in self.direct_normal_irradiance:
            sun = sp.calculate_sun_from_date_time(dnr.datetime)
            dir_h = dnr * math.sin(math.radians(sun.altitude))
            direct_horizontal_rad.append(
                DataPoint(dir_h, dnr.datetime, 'SI', 'Direct Horizontal Irradiance'))
        return direct_horizontal_rad

    @property
    def is_leap_year(self):
        """Return the timestep."""
        return self._is_leap_year

    @staticmethod
    def hr_count(is_leap_year):
        """Number of hours in this Wea file.

        Keep in mind that wea file is an annual file but this value will be different
        for a leap year
        """
        return 8760 + 24 if is_leap_year else 8760

    @staticmethod
    def _get_datetimes(timestep, is_leap_year):
        """List of datetimes based on timestep.

        This method should only be used for classmethods. For datetimes use datetiems or
        hoys methods.
        """
        hr_count = 8760 + 24 if is_leap_year else 8760
        adjust_time = 30 if timestep == 1 else 0
        return tuple(
            DateTime.from_moy(60.0 * count / timestep + adjust_time, is_leap_year)
            for count in xrange(hr_count * timestep)
        )

    @staticmethod
    def _get_empty_data_collections(location, timestep, is_leap_year):
        """Return two empty data collection.

        Direct Normal Irradiance, Diffuse Horizontal Irradiance
        """
        analysis_period = AnalysisPeriod(timestep=timestep, is_leap_year=is_leap_year)
        header_dnr = Header(analysis_period=analysis_period,
                            data_type='Direct Normal Irradiance',
                            unit='W/m2',
                            location=location)
        direct_norm_rad = DataCollection(header=header_dnr)
        header_dhr = Header(analysis_period=analysis_period,
                            data_type='Diffuse Horizontal Irradiance',
                            unit='W/m2',
                            location=location)
        diffuse_horiz_rad = DataCollection(header=header_dhr)

        return direct_norm_rad, diffuse_horiz_rad

    def get_irradiance_values(self, month, day, hour):
        """Get direct and diffuse irradiance values for a point in time."""
        dt = DateTime(month, day, hour, leap_year=self.is_leap_year)
        count = int(dt.hoy * self.timestep)
        return self.direct_normal_irradiance[count], \
            self.diffuse_horizontal_irradiance[count]

    def get_irradiance_values_for_hoy(self, hoy):
        """Get direct and diffuse irradiance values for an hoy."""
        count = int(hoy * self.timestep)
        return self.direct_normal_irradiance[count], \
            self.diffuse_horizontal_irradiance[count]

    def directional_irradiance(self, altitude=90, azimuth=180,
                               ground_reflectance=0.2, isotrophic=True):
        """Returns the irradiance components facing a given altitude and azimuth.

        This method computes unobstructed solar flux facing a given
        altitude and azimuth. The default is set to return the golbal horizontal
        irradiance, assuming an altitude facing straight up (90 degrees).

        Args:
            altitude: A number between -90 and 90 that represents the
                altitude at which irradiance is being evaluated in degrees.
            azimuth: A number between 0 and 360 that represents the
                azimuth at wich irradiance is being evaluated in degrees.
            ground_reflectance: A number between 0 and 1 that represents the
                reflectance of the ground. Default is set to 0.2.
                Altermatively, this can be one of the following text inputs:
                urban, grass, fresh grass, soil, sand, snow, fresh snow,
                asphalt, concrete, sea
            isotrophic: A boolean value that sets whether an istotrophic sky is
                used (as opposed to an anisotrophic sky). An isotrophic sky
                assummes an even distribution of diffuse irradiance across the
                sky while an anisotrophic sky places more diffuse irradiance
                near the solar disc. Default is set to True for isotrophic

        Returns:
            total_irradiance: A list of total solar irradiance at each timestep.
            direct_irradiance: A list of direct solar irradiance at each timestep.
            diffuse_irradiance: A list of diffuse sky solar irradiance
                at each timestep.
            reflected_irradiance: A list of ground reflected solar irradiance
                at each timestep.
        """
        # Acceptable text inputs for ground_reflectance
        albedos = {'urban': 0.18,
                   'grass': 0.20,
                   'fresh grass': 0.26,
                   'soil': 0.17,
                   'sand': 0.40,
                   'snow': 0.65,
                   'fresh snow': 0.75,
                   'asphalt': 0.12,
                   'concrete': 0.30,
                   'sea': 0.06}
        if isinstance(ground_reflectance, str) and ground_reflectance in albedos.keys():
            ground_reflectance = albedos[ground_reflectance]
        else:
            ground_reflectance = float(ground_reflectance)

        # function to convert polar coordinates to xyz.
        def pol2cart(phi, theta):
            mult = math.cos(theta)
            x = math.sin(phi) * mult
            y = math.cos(phi) * mult
            z = math.sin(theta)
            return Vector3(x, y, z)

        # convert the altitude and azimuth to a normal vector
        normal = pol2cart(math.radians(azimuth), math.radians(altitude))

        # create sunpath and get altitude at every timestep of the year
        direct_irradiance = []
        diffuse_irradiance = []
        reflected_irradiance = []
        total_irradiance = []
        sp = Sunpath.from_location(self.location)
        sp.is_leap_year = self.is_leap_year
        for dnr, dhr in zip(self.direct_normal_irradiance,
                            self.diffuse_horizontal_irradiance):
            dt = dnr.datetime
            sun = sp.calculate_sun_from_date_time(dt)
            sun_vec = pol2cart(math.radians(sun.azimuth),
                               math.radians(sun.altitude))
            vec_angle = sun_vec.angle(normal)

            # direct irradiance on surface
            srf_dir = 0
            if sun.altitude > 0 and vec_angle < math.pi / 2:
                srf_dir = dnr * math.cos(vec_angle)

            # diffuse irradiance on surface
            if isotrophic is True:
                srf_dif = dhr * ((math.sin(math.radians(altitude)) / 2) + 0.5)
            else:
                y = max(0.45, 0.55 + (0.437 * math.cos(vec_angle)) + 0.313 *
                        math.cos(vec_angle) * 0.313 * math.cos(vec_angle))
                srf_dif = self.dhr * (y * (
                    math.sin(math.radians(abs(90 - altitude)))) +
                    math.cos(math.radians(abs(90 - altitude))))

            # reflected irradiance on surface.
            e_glob = dhr + dnr * math.cos(math.radians(90 - sun.altitude))
            srf_ref = e_glob * ground_reflectance * (0.5 - (math.sin(
                math.radians(altitude)) / 2))

            # add it all together
            direct_irradiance.append(
                DataPoint(srf_dir, dt, 'SI', 'Irradiance'))
            diffuse_irradiance.append(
                DataPoint(srf_dif, dt, 'SI', 'Irradiance'))
            reflected_irradiance.append(
                DataPoint(srf_ref, dt, 'SI', 'Irradiance'))
            total_irradiance.append(
                DataPoint(srf_dir + srf_dif + srf_ref, dt, 'SI', 'Irradiance'))

        return total_irradiance, direct_irradiance, \
            diffuse_irradiance, reflected_irradiance

    @property
    def header(self):
        """Wea header."""
        return "place %s\n" % self.location.city + \
            "latitude %.2f\n" % self.location.latitude + \
            "longitude %.2f\n" % -self.location.longitude + \
            "time_zone %d\n" % (-self.location.time_zone * 15) + \
            "site_elevation %.1f\n" % self.location.elevation + \
            "weather_data_file_units 1\n"

    def to_json(self):
        """Write Wea to json file
            {
            "location": {} , // ladybug location schema
            "direct_normal_irradiance": (), // Tuple of hourly direct normal
                irradiance
            "diffuse_horizontal_irradiance": (), // Tuple of hourly diffuse
                horizontal irradiance
            "timestep": float //timestep between measurements, default is 1
            }
        """
        return {
            'location': self.location.to_json(),
            'direct_normal_irradiance':
                self.direct_normal_irradiance.to_json(),
            'diffuse_horizontal_irradiance':
                self.diffuse_horizontal_irradiance.to_json(),
            'timestep': self.timestep,
            'is_leap_year': self.is_leap_year
        }

    def write(self, file_path, hoys=None, write_hours=False):
        """Write the wea file.

        WEA carries irradiance values from epw and is what gendaymtx uses to
        generate the sky.
        """
        if not file_path.lower().endswith('.wea'):
            file_path += '.wea'

        # generate hoys in wea file based on timestep
        full_wea = False
        if not hoys:
            hoys = self.hoys
            full_wea = True

        # write header
        lines = [self.header]
        if full_wea:
            # there is no input user for hoys, write it for all the hours
            # write values
            for dir_rad, dif_rad in zip(self.direct_normal_irradiance,
                                        self.diffuse_horizontal_irradiance):
                dt = dir_rad.datetime
                line = "%d %d %.3f %d %d\n" \
                    % (dt.month, dt.day, dt.float_hour, dir_rad, dif_rad)
                lines.append(line)
        else:
            # output wea based on user request
            for hoy in hoys:
                try:
                    dir_rad, dif_rad = self.get_irradiance_values_for_hoy(hoy)
                except IndexError:
                    print('Warn: Wea data for {} is not available!'.format(dt))
                    continue

                dt = dir_rad.datetime
                line = "%d %d %.3f %d %d\n" \
                    % (dt.month, dt.day, dt.float_hour, dir_rad, dif_rad)

                lines.append(line)
        file_data = ''.join(lines)
        write_to_file(file_path, file_data, True)

        if write_hours:
            hrs_file_path = file_path[:-4] + '.hrs'
            hrs_data = ','.join(str(h) for h in hoys) + '\n'
            write_to_file(hrs_file_path, hrs_data, True)

        return file_path

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        """epw file representation."""
        return "WEA [%s]" % self.location.city
