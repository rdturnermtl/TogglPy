# Ryan Turner (turnerry@iro.umontreal.ca)
'''
Example usage:
python toggl_report.py api_key.txt config.ini
'''
from __future__ import print_function
import configparser
from os.path import join
from sys import argv
import numpy as np
import pandas as pd
from TogglPy import Toggl

time_entry_url = 'https://www.toggl.com/api/v8/time_entries'
pid_req_fmt = 'https://www.toggl.com/api/v8/projects/%d'

time_types = str
pid_type = object  # so some int and some NaN, if no nan then np.int64
col_dtypes = {'duronly': bool,
              'wid': np.int64,
              'description': str,
              'stop': time_types,
              'pid': pid_type,
              'start': time_types,
              'at': time_types,
              'billable': bool,
              'duration': np.int64,
              'guid': str,
              'id': np.int64,
              'uid': np.int64}

# Load in API key and settings
print('reading in settings')
api_key_file = argv[1]
settings_ini_file = argv[2] if len(argv) > 2 else 'config.ini'

with open(api_key_file, 'r') as f:
    api_key = f.read()

config = configparser.ConfigParser()
config.read(settings_ini_file)
start_date = config.get('Time', 'StartDate')
end_date = config.get('Time', 'EndDate')
internal_time = config.get('Time', 'InternalTime')
display_time = config.get('Time', 'DisplayTime')
dump_path = config.get('IO', 'DumpPath')

print('starting API')  # Initial setup
toggl = Toggl()
toggl.setAPIKey(api_key)

params = {'start_date': start_date, 'end_date': end_date}
print('Making request')  # Get the raw data on time entries
response = toggl.request(time_entry_url, parameters=params)
print('%d records' % len(response))
df = pd.DataFrame(response)  # TODO pass in dtypes

# Get a list of project ids
pids = df['pid'].unique()
pids = pids[np.isfinite(pids)].astype(int)

# Add column with name of project, so not just project id in df
print('Making project request')
response = [toggl.request(pid_req_fmt % pp)['data'] for pp in pids]
print('%d records' % len(response))
pid_df = pd.DataFrame(response)
pid_df.set_index('id', drop=True, inplace=True)
df['proj_name'] = df['pid'].map(pid_df['name'])

# Break into date and time in both UTC and local time
start_time = df['start']
start_time = pd.to_datetime(start_time)
start_time = start_time.dt.tz_localize(internal_time)
df['start_date_' + internal_time] = start_time.dt.date
df['start_time_' + internal_time] = start_time.dt.time
start_time = start_time.dt.tz_convert(display_time)
df['start_date_' + display_time] = start_time.dt.date
df['start_time_' + display_time] = start_time.dt.time

# Save dump of everything to csv
print('saving')
df.to_csv(join(dump_path, 'toggl_all.csv'),
          na_rep='', header=True, index=False)

# Break into daily files based on local time
gdf = df.groupby('start_date_' + display_time)
for date, sub_df in gdf:
    sub_df.to_csv(join(dump_path, 'toggl_local_%s.csv' % date),
                  na_rep='', header=True, index=False)

# Break into daily files based on UTC
gdf = df.groupby('start_date_' + internal_time)
for date, sub_df in gdf:
    sub_df.to_csv(join(dump_path, 'toggl_utc_%s.csv' % date),
                  na_rep='', header=True, index=False)

print('done')
