# SPICE

The fetch_spice.py script allows you to download SPICE data and save it as a netCDF file. In order to run the script you must have installed the necessary dependencies. A environment.yml file is provided to make this easy. The following is an example of how the script can be run from the command line:

`python fetch_spice.py SPICE38 2023-09-01T00:00:00Z 2023-09-30T23:59:59Z test.nc`

Running the script with the -h flag shows what all of the different parameters are:
```
python fetch_spice.py -h
usage: fetch_spice.py [-h] spice start_ts end_ts path

Download and save SPICE data.

positional arguments:
  spice       SPICE station code. Can be SPICE34, SPICE35, SPICE36, SPICE37 or SPICE38.
  start_ts    Start time in UTC (YYYY-MM-DDTHH:MM:SSZ).
  end_ts      End time in UTC (YYYY-MM-DDTHH:MM:SSZ).
  path        Path (including filename) to where netCDF file will be saved.

options:
  -h, --help  show this help message and exit
```

There are currently a few issues with the script:

* The lat/lon values that are saved in the file are calculated as a weighted average of the Iridium estimated lat/lon values. The weighting is carried out such that the lowest estimated CEP values get the highest weighting. This could lead to different lat/lon values for the same station for different time periods as the Iridium estimates can vary. A way to deal with this would be to have a stable set of coordinates for the stations that are used instead of calculating an average for each run for different time periods.
* A lot of the metadata is currently missing. All attributes that have the value "filler" must have their value replaced with the appropriate value.
