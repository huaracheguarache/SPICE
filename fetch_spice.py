import requests
import json
from json.decoder import JSONDecodeError
import numpy as np
import xarray as xr
import datetime
import argparse
import sys


def main(spice, start_ts, end_ts, filename):
    response = requests.get(f'https://publikacje.inoz.us.edu.pl/SPICE/metno.php?spice={spice}&startTs={start_ts}&'
                            f'endTs={end_ts}&meta=yes&spiceID=yes&time=no')

    try:
        json_data = json.loads(response.text)
    except JSONDecodeError:
        if response.text == '0 results':
            print(f'{spice} does not have any data for the provided date range {start_ts}-{end_ts}!')
            sys.exit(0)
        else:
            raise

    variables = ('surface_snow_thickness', 'air_temperature', 'relative_humidity', 'air_pressure')
    long_names = {'surface_snow_thickness': 'snow thickness measured at station',
                  'air_temperature': 'air temperature measured at station',
                  'relative_humidity': 'relative humidity measured at station',
                  'air_pressure': 'air pressure measured at station'}
    data_arrays = {}

    for variable in variables:
        # Must read time in second precision to get correct values, and then convert to nanosecond precision to
        # silence xarray warning about non-nanosecond precision.
        time = np.array([item['t'] for item in json_data[variable]], dtype='datetime64[s]').astype('datetime64[ns]')
        data = np.array([item['v'] for item in json_data[variable]], dtype=float)

        data_arrays[variable] = xr.DataArray(data=data,
                                             dims=['time'],
                                             coords=dict(time=time),
                                             attrs=dict(long_name=long_names[variable],
                                                        standard_name=variable,
                                                        units=json_data['metadata'][variable]['v']['units'],
                                                        coverage_content_type='physicalMeasurement'))

        _FillValue = json_data['metadata'][variable]['v']['_FillValue']
        data_arrays[variable].attrs['_FillValue'] = _FillValue

    ds = xr.Dataset(data_vars=data_arrays)
    ds['time'].attrs = {'standard_name': 'time', 'long_name': 'time of observation'}

    # Positions of the stations. SPICE37 is currently not set up, so it has -999 as a placeholder for lat, lon.
    stored_positions = {'SPICE34': (77.08636, 15.62725),
                        'SPICE35': (77.06198, 15.20614),
                        'SPICE36': (78.6765, 12.0399),
                        'SPICE37': (-999, -999),
                        'SPICE38': (77.51715, 14.39992)}

    lat = stored_positions[spice][0]
    lon = stored_positions[spice][1]

    ds = ds.assign(lat=lat)
    ds['lat'].attrs = {'units': 'degree_north', 'standard_name': 'latitude'}

    ds = ds.assign(lon=lon)
    ds['lon'].attrs = {'units': 'degree_east', 'standard_name': 'longitude'}

    # TODO: check whether attributes are OK.
    ds.attrs = {'title': f'Measurement data from {spice} station',
                'summary': ('Data from SPICE stations includes snow depth measurements, surface temperature, '
                            'relative humidity, and atmospheric pressure. These stations and their data are a part of '
                            'the CRIOS project.'),
                'keywords': 'EARTH SCIENCE > CRYOSPHERE > SNOW/ICE > SNOW DEPTH,'
                            'EARTH SCIENCE > ATMOSPHERE > ATMOSPHERIC TEMPERATURE > SURFACE TEMPERATURE > '
                            'AIR TEMPERATURE,'
                            'EARTH SCIENCE > ATMOSPHERE > ATMOSPHERIC WATER VAPOR > WATER VAPOR INDICATORS > HUMIDITY >'
                            ' RELATIVE HUMIDITY,'
                            'EARTH SCIENCE > ATMOSPHERE > ATMOSPHERIC PRESSURE > ATMOSPHERIC PRESSURE MEASUREMENTS',
                'keywords_vocabulary': 'GCMD Science Keywords',
                'geospatial_lat_min': str(lat),
                'geospatial_lat_max': str(lat),
                'geospatial_lon_min': str(lon),
                'geospatial_lon_max': str(lon),
                'time_coverage_start': np.datetime_as_string(ds.time[0], timezone='UTC', unit='s'),
                'time_coverage_end': np.datetime_as_string(ds.time[-1], timezone='UTC', unit='s'),
                'Conventions': 'CF-1.11, ACDD-1.3',
                'history': f'{datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}, created file.',
                'date_created': datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                'creator_type': 'person',
                'creator_institution': 'University of Silesia',
                'creator_name': 'Łukasz Małarzewski',
                'creator_email': 'lukasz.malarzewski@us.edu.pl',
                'creator_url': 'https://us.edu.pl/instytut/inoz/en/osoby/malarzewski-lukasz/',
                'project': 'CRIOS',
                'license': 'https://spdx.org/licenses/CC-BY-4.0 (CC-BY-4.0)',
                'iso_topic_category': 'climatologyMeteorologyAtmosphere',
                'activity_type': 'In Situ Land-based station',
                'operational_status': 'Not available',
                'featureType': 'timeSeries'}

    float_type = {'dtype': 'float32'}
    integer_type = {'dtype': 'int32'}

    encoding = {'time': integer_type,
                'surface_snow_thickness': float_type,
                'air_temperature': float_type,
                'relative_humidity': float_type,
                'air_pressure': float_type,
                'lat': float_type,
                'lon': float_type}

    ds.to_netcdf(filename, encoding=encoding, unlimited_dims='time')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download and save SPICE data.')
    parser.add_argument('spice',
                        choices=('SPICE34', 'SPICE35', 'SPICE36', 'SPICE37', 'SPICE38'),
                        help='SPICE station code. Can be SPICE34, SPICE35, SPICE36, SPICE37 or SPICE38.')
    parser.add_argument('start_ts',
                        help='Start time in UTC (YYYY-MM-DDTHH:MM:SSZ).')
    parser.add_argument('end_ts',
                        help='End time in UTC (YYYY-MM-DDTHH:MM:SSZ).')
    parser.add_argument('path', help='Path (including filename) to where netCDF file will be saved.')
    args = parser.parse_args()

    main(args.spice, args.start_ts, args.end_ts, args.path)
