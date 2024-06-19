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

        try:
            _FillValue = json_data['metadata'][variable]['v']['_FillValue']
        except KeyError:
            pass
        else:
            data_arrays[variable] = data_arrays[variable].where(data_arrays[variable].notnull(), _FillValue)
            data_arrays[variable].attrs['_FillValue'] = _FillValue

    ds = xr.Dataset(data_vars=data_arrays)
    ds['time'].attrs = {'standard_name': 'time', 'long_name': 'time of observation'}

    # Find weighted averages of latitude and longitude (use reported CEP for weighting).
    latitude = np.array([item['v'] for item in json_data['IridiumLatitude']], dtype=float)
    longitude = np.array([item['v'] for item in json_data['IridiumLongitude']], dtype=float)
    cep = np.array([item['v'] for item in json_data['IridiumCEP']], dtype=float)

    cep_weights = (1 / (1 / cep).sum()) * (1 / cep)
    # Round lat/lon to two decimals.
    weighted_mean_latitude = np.round((cep_weights * latitude).sum(), 2)
    weighted_mean_longitude = np.round((cep_weights * longitude).sum(), 2)

    ds = ds.assign(lat=weighted_mean_latitude)
    ds['lat'].attrs = {'units': 'degree_north', 'standard_name': 'latitude'}

    ds = ds.assign(lon=weighted_mean_longitude)
    ds['lon'].attrs = {'units': 'degree_east', 'standard_name': 'longitude'}

    # TODO: attributes must be filled in.
    ds.attrs = {'title': 'filler',
                'summary': 'filler',
                'keywords': 'EARTH SCIENCE > CRYOSPHERE > SNOW/ICE > SNOW DEPTH,'
                            'EARTH SCIENCE > ATMOSPHERE > ATMOSPHERIC TEMPERATURE > SURFACE TEMPERATURE > '
                            'AIR TEMPERATURE,'
                            'EARTH SCIENCE > ATMOSPHERE > ATMOSPHERIC WATER VAPOR > WATER VAPOR INDICATORS > HUMIDITY >'
                            ' RELATIVE HUMIDITY,'
                            'EARTH SCIENCE > ATMOSPHERE > ATMOSPHERIC PRESSURE > ATMOSPHERIC PRESSURE MEASUREMENTS',
                'keywords_vocabulary': 'GCMD Science Keywords',
                'geospatial_lat_min': f'{ds['lat'].values:.2f}',
                'geospatial_lat_max': f'{ds['lat'].values:.2f}',
                'geospatial_lon_min': f'{ds['lon'].values:.2f}',
                'geospatial_lon_max': f'{ds['lon'].values:.2f}',
                'time_coverage_start': np.datetime_as_string(ds.time[0], timezone='UTC', unit='s'),
                'time_coverage_end': np.datetime_as_string(ds.time[-1], timezone='UTC', unit='s'),
                'Conventions': 'CF-1.11, ACDD-1.3',
                'history': f'{datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}, created file.',
                'date_created': datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                'creator_type': 'filler',
                'creator_institution': 'filler',
                'creator_name': 'filler',
                'creator_email': 'filler',
                'creator_url': 'filler',
                'project': 'filler',
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
                        help='SPICE station code. Can be SPICE34, SPICE35, SPICE36, SPICE37 or SPICE38.')
    parser.add_argument('start_ts',
                        help='Start time in UTC (YYYY-MM-DDTHH:MM:SSZ).')
    parser.add_argument('end_ts',
                        help='End time in UTC (YYYY-MM-DDTHH:MM:SSZ).')
    parser.add_argument('path', help='Path (including filename) to where netCDF file will be saved.')
    args = parser.parse_args()

    main(args.spice, args.start_ts, args.end_ts, args.path)
