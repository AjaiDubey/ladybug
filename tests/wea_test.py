# coding=utf-8

import unittest
import pytest
import os
from ladybug.wea import Wea
from ladybug.location import Location
from ladybug.epw import EPW


class WeaTestCase(unittest.TestCase):
    """Test for (ladybug/epw.py)"""

    # preparing to test.
    def setUp(self):
        """set up."""
        pass

    def tearDown(self):
        """Nothing to tear down as nothing gets written to file."""
        pass

    def test_from_file(self):
        """Test import from wea file."""
        wea_file = './tests/wea/san_francisco_10min.wea'
        with pytest.raises(Exception):
            Wea.from_file(wea_file)  # wrong timestep

        wea = Wea.from_file(wea_file, 6)
        assert wea.direct_normal_irradiance[45] == 88
        assert wea.diffuse_horizontal_irradiance[45] == 1
        assert wea.direct_normal_irradiance[46] == 313
        assert wea.diffuse_horizontal_irradiance[46] == 3

    def test_from_epw(self):
        """Test import from epw"""
        epw_path = './tests/epw/chicago.epw'
        wea_from_epw = Wea.from_epw_file(epw_path)

        assert wea_from_epw.location.city == 'Chicago Ohare Intl Ap'
        assert wea_from_epw.timestep == 1
        assert wea_from_epw.direct_normal_irradiance[7] == 22
        assert wea_from_epw.direct_normal_irradiance[7].datetime.hour == 7
        assert wea_from_epw.direct_normal_irradiance[7].datetime.minute == 30
        assert wea_from_epw.direct_normal_irradiance[8] == 397
        assert wea_from_epw.direct_normal_irradiance[8].datetime.hour == 8
        assert wea_from_epw.direct_normal_irradiance[8].datetime.minute == 30
        # diffuse horizontal irradiance
        assert wea_from_epw.diffuse_horizontal_irradiance[7] == 10
        assert wea_from_epw.diffuse_horizontal_irradiance[7].datetime.hour == 7
        assert wea_from_epw.diffuse_horizontal_irradiance[7].datetime.minute == 30
        assert wea_from_epw.diffuse_horizontal_irradiance[8] == 47
        assert wea_from_epw.diffuse_horizontal_irradiance[8].datetime.hour == 8
        assert wea_from_epw.diffuse_horizontal_irradiance[8].datetime.minute == 30

    def test_from_stat(self):
        """Test import from stat"""
        stat_path = './tests/stat/chicago.stat'
        wea_from_stat = Wea.from_stat_file(stat_path)

        assert wea_from_stat.location.city == 'Chicago Ohare Intl Ap'
        assert wea_from_stat.timestep == 1
        assert wea_from_stat.diffuse_horizontal_irradiance[0].value == \
            pytest.approx(0, rel=1e-3)
        assert wea_from_stat.direct_normal_irradiance[0].value == \
            pytest.approx(0, rel=1e-3)
        assert wea_from_stat.diffuse_horizontal_irradiance[12].value == \
            pytest.approx(87.44171, rel=1e-3)
        assert wea_from_stat.direct_normal_irradiance[12].value == \
            pytest.approx(810.693919, rel=1e-3)

    def test_from_stat_missing_optical(self):
        """Test import from a stat file that is missing optical data"""
        stat_path = './tests/stat/santamonica.stat'
        with pytest.raises(ValueError,
                           match='Stat file contains no optical data.'):
            Wea.from_stat_file(stat_path)

    def test_from_clear_sky(self):
        """Test from original clear sky"""
        location = Location(
            'Chicago Ohare Intl Ap', 'USA', 41.98, -87.92, -6.0, 201.0)
        wea_from_clear_sky = Wea.from_ashrae_clear_sky(location)

        assert wea_from_clear_sky.location.city == 'Chicago Ohare Intl Ap'
        assert wea_from_clear_sky.timestep == 1
        assert wea_from_clear_sky.diffuse_horizontal_irradiance[0].value == \
            pytest.approx(0, rel=1e-3)
        assert wea_from_clear_sky.direct_normal_irradiance[0].value == \
            pytest.approx(0, rel=1e-3)
        assert wea_from_clear_sky.diffuse_horizontal_irradiance[12].value == \
            pytest.approx(60.72258, rel=1e-3)
        assert wea_from_clear_sky.direct_normal_irradiance[12].value == \
            pytest.approx(857.00439, rel=1e-3)

    def test_from_zhang_huang(self):
        """Test from zhang huang solar model"""
        path = './tests/epw/chicago.epw'
        epw = EPW(path)

        wea_from_zh = Wea.from_zhang_huang_solar(epw.location,
                                                 epw.total_sky_cover.values,
                                                 epw.relative_humidity.values,
                                                 epw.dry_bulb_temperature.values,
                                                 epw.wind_speed.values,
                                                 epw.atmospheric_station_pressure.values)

        assert wea_from_zh.location.city == 'Chicago Ohare Intl Ap'
        assert wea_from_zh.timestep == 1
        assert wea_from_zh.global_horizontal_irradiance.values[0] == \
            pytest.approx(0, rel=1e-1)
        assert wea_from_zh.global_horizontal_irradiance.values[12] == \
            pytest.approx(417.312, rel=1e-1)
        assert wea_from_zh.direct_normal_irradiance.values[12] == \
            pytest.approx(654.52, rel=1e-1)
        assert wea_from_zh.diffuse_horizontal_irradiance[12].value == \
            pytest.approx(144.51, rel=1e-1)

    def test_json_methods(self):
        """Test JSON serialization methods"""
        epw_path = './tests/epw/chicago.epw'
        wea = Wea.from_epw_file(epw_path)

        assert wea.to_json() == Wea.from_json(wea.to_json()).to_json()

    def test_import_epw(self):
        """Test to compare import from epw with its json version."""
        epw_path = './tests/epw/chicago.epw'

        wea_from_epw = Wea.from_epw_file(epw_path)

        wea_json = wea_from_epw.to_json()
        wea_from_json = Wea.from_json(wea_json)
        assert wea_from_json.direct_normal_irradiance.values == \
            wea_from_epw.direct_normal_irradiance.values
        assert wea_from_json.diffuse_horizontal_irradiance.values == \
            wea_from_epw.diffuse_horizontal_irradiance.values

    def test_import_stat(self):
        """Test to compare import from stat with its json version."""
        stat_path = './tests/stat/chicago.stat'
        wea_from_stat = Wea.from_stat_file(stat_path)

        wea_json = wea_from_stat.to_json()
        wea_from_json = Wea.from_json(wea_json)
        assert wea_from_json.direct_normal_irradiance.values == \
            wea_from_stat.direct_normal_irradiance.values
        assert wea_from_json.diffuse_horizontal_irradiance.values == \
            wea_from_stat.diffuse_horizontal_irradiance.values

    def test_write_wea(self):
        """Test the write Wea file capability."""
        stat_path = './tests/stat/chicago.stat'
        wea_from_stat = Wea.from_stat_file(stat_path)

        wea_path = './tests/wea/chicago_stat.wea'
        hrs_path = './tests/wea/chicago_stat.hrs'
        hoys = range(8760)
        wea_from_stat.write(wea_path, hoys, True)

        assert os.path.isfile(wea_path)
        assert os.stat(wea_path).st_size > 1
        assert os.path.isfile(hrs_path)
        assert os.stat(hrs_path).st_size > 1

        # check the order of the data in the file
        with open(wea_path) as wea_f:
            lines = wea_f.readlines()
            assert float(lines[6].split(' ')[-2]) == \
                pytest.approx(
                    wea_from_stat.direct_normal_irradiance[0].value, rel=1e-1)
            assert int(lines[6].split(' ')[-1]) == \
                wea_from_stat.diffuse_horizontal_irradiance[0].value
            assert float(lines[17].split(' ')[-2]) == \
                pytest.approx(
                    wea_from_stat.direct_normal_irradiance[11].value, rel=1e-1)
            assert float(lines[17].split(' ')[-1]) == \
                pytest.approx(
                    wea_from_stat.diffuse_horizontal_irradiance[11].value, rel=1e-1)

        os.remove(wea_path)
        os.remove(hrs_path)

    def test_global_and_direct_horizontal(self):
        """Test the global horizontal irradiance on method."""
        stat_path = './tests/stat/chicago.stat'
        wea_from_stat = Wea.from_stat_file(stat_path)

        diffuse_horiz_rad = wea_from_stat.diffuse_horizontal_irradiance
        direct_horiz_rad = wea_from_stat.direct_horizontal_irradiance
        glob_horiz_rad = wea_from_stat.global_horizontal_irradiance

        assert [x.value for x in glob_horiz_rad] == pytest.approx(
            [x + y for x, y in zip(diffuse_horiz_rad, direct_horiz_rad)], rel=1e-3)

    def test_directional_irradiance(self):
        """Test the directinal irradiance method."""
        stat_path = './tests/stat/chicago.stat'
        wea_from_stat = Wea.from_stat_file(stat_path)

        srf_total, srf_direct, srf_diffuse, srf_reflect = \
            wea_from_stat.directional_irradiance(90)
        diffuse_horiz_rad = wea_from_stat.diffuse_horizontal_irradiance
        direct_horiz_rad = wea_from_stat.direct_horizontal_irradiance
        glob_horiz_rad = wea_from_stat.global_horizontal_irradiance

        assert [x.value for x in srf_total] == pytest.approx(
            [x.value for x in glob_horiz_rad], rel=1e-3)
        assert [x.value for x in srf_direct] == pytest.approx(
            [x.value for x in direct_horiz_rad], rel=1e-3)
        assert [x.value for x in srf_diffuse] == pytest.approx(
            [x.value for x in diffuse_horiz_rad], rel=1e-3)
        assert [x.value for x in srf_reflect] == pytest.approx(
            [0] * 8760, rel=1e-3)

    def test_leap_year(self):
        """Test clear sky with leap year."""
        location = Location(
            'Chicago Ohare Intl Ap', 'USA', 41.98, -87.92, -6.0, 201.0)
        wea = Wea.from_ashrae_clear_sky(location, is_leap_year=True)

        assert wea.diffuse_horizontal_irradiance[1416].datetime.month == 2
        assert wea.diffuse_horizontal_irradiance[1416].datetime.day == 29
        assert wea.diffuse_horizontal_irradiance[1416].datetime.hour == 0
        assert wea.diffuse_horizontal_irradiance[1416].datetime.minute == 30

        assert wea.diffuse_horizontal_irradiance[1416 + 12].datetime.month == 2
        assert wea.diffuse_horizontal_irradiance[1416 + 12].datetime.day == 29
        assert wea.diffuse_horizontal_irradiance[1416 + 12].datetime.hour == 12
        assert wea.diffuse_horizontal_irradiance[1416 + 12].datetime.minute == 30


if __name__ == "__main__":
    unittest.main()
