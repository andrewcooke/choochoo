
# FIT Files

## Introduction

The FIT format is used by ANT+ hardware (bike computers, smart
watches, sensors) to transmit and store data.  If you are curious
about the technical details, see the
[SDK](https://www.thisisant.com/resources/fit).

Choochoo includes a library that reads (but does not write) FIT format
data.  This can be used by third parties (see the API docs below), but
is intended mainly to allow data to be imported into the ch2 diary.
However, this is not yet implemented - currently all that is possible
is displaying the data in a variety of formats.

## Contents

* [Displaying FIT data](#displaying-fit-data)

  * [The `records` format](#the-records-format) (the default) - this
    shows the file contents in a high-level, easy-to-read format.
  
  * The `messages` format - this displays the low-level binary data and
    is mostly of use when debugging errors.

  * The `fields` format - a more detailed low-level display that is also
    mostly used for debugging.

  * The `csv` format - used to compare test data with the examples
    provided in the [SDK](https://www.thisisant.com/resources/fit).

* Third-party API use

* Implementation and limitations

## Displaying FIT Data

For details of all the options:

    ch2 dump-fit -h

### The `records` Format

#### Example Usage

    ch2 -v 0 dump-fit FILE

    ch2 -v 0 dump-fit --records FILE

    ch2 -v 0 dump-fit --records --all-fields --all-messages FILE

    ch2 -v 0 dump-fit --records --after N1 --limit N2 FILE

#### Format Description

This command displays the contents of the file in two ways:

* Messages which occur 3 times or less are displayed in order of
  appearance, using name/value pairs.

* Messages which occur more often are displayed grouped into "tables",
  with values in columns and names in the column titles.

#### Example Output

    file_id
      garmin_product: fr230,  manufacturer: garmin,
      serial_number: 3918730542,
      time_created: 2018-08-03 15:52:12+00:00,
      type: activity

    file_creator
      software_version: 710

    device_settings
      active_time_zone: 0,
      activity_tracker_enabled: False,
      autosync_min_steps: 1000steps,
      autosync_min_time: 60minutes,   backlight_mode: manual,
      mounting_side: left,    move_alert_enabled: True,
      time_mode: hour24,  time_offset: 4294952896s,
      time_zone_offset: 0.0hr,    utc_offset: 0

    user_profile
      activity_class: 0,  dist_setting: metric,
      elev_setting: metric,   gender: male,   height: 1.73m,
      height_setting: metric,     hr_setting: max,
      language: english,
      position_setting: degree_minute_second,
      resting_heart_rate: 42bpm,  sleep_time: 79200,
      speed_setting: metric,  temperature_setting: metric,
      wake_time: 21600,   weight: 65.0kg,
      weight_setting: metric

    sport
      name: Bike,     sport: cycling,     sub_sport: generic

    zones_target
      hr_calc_type: percent_max_hr

    lap
      end_position_lat: -33.427340649068356°,
      end_position_long: -70.60799863189459°,
      enhanced_avg_speed: 5.59m/s,
      enhanced_max_speed: 8.295m/s,   event: lap,
      event_type: stop,   lap_trigger: session_end,
      message_index: 0,   sport: cycling,
      start_position_lat: -33.42752396129072°,
      start_position_long: -70.60802654363215°,
      start_time: 2018-08-03 15:52:13+00:00,
      sub_sport: generic,
      timestamp: 2018-08-03 16:16:28+00:00s,
      total_ascent: 35m,  total_calories: 193kcal,
      total_descent: 81m,     total_distance: 6500.22m,
      total_elapsed_time: 1398.718s,
      total_timer_time: 1162.728s

    session
      enhanced_avg_speed: 5.59m/s,
      enhanced_max_speed: 8.295m/s,   event: lap,
      event_type: stop,   first_lap_index: 0,
      message_index: 0,   nec_lat: -33.42733855359256°,
      nec_long: -70.58107445016503°,  num_laps: 1,
      sport: cycling,
      start_position_lat: -33.42752396129072°,
      start_position_long: -70.60802654363215°,
      start_time: 2018-08-03 15:52:13+00:00,
      sub_sport: generic,     swc_lat: -33.43541686423123°,
      swc_long: -70.60802654363215°,
      timestamp: 2018-08-03 16:16:28+00:00s,
      total_ascent: 35m,  total_calories: 193kcal,
      total_descent: 81m,     total_distance: 6500.22m,
      total_elapsed_time: 1398.718s,
      total_timer_time: 1162.728s,    trigger: activity_end

    activity
      event: activity,    event_type: stop,
      local_timestamp: 2018-08-03 12:16:28,
      num_sessions: 1,
      timestamp: 2018-08-03 16:16:28+00:00,
      total_timer_time: 1162.728s,    type: manual

    event
      timestamp,                    event,  event_group,
	event_type,     timer_trigger
      2018-08-03 15:52:13+00:00s,   timer,  0,          
	start,          manual       
      2018-08-03 15:53:45+00:00s,   timer,  0,          
	stop_all,       auto         
      2018-08-03 15:53:45+00:00s,   4,      38,         
	-               marker       
    [...]
      2018-08-03 16:15:36+00:00s,   timer,  0,          
	stop_all,       manual       

    device_info
      timestamp,                    device_index,
	device_type,    garmin_product,     manufacturer,
	serial_number,  software_version,   source_type
      2018-08-03 15:52:13+00:00s,   creator,     
	-               fr230,              garmin,      
	3918730542,     7.1,                local      
      2018-08-03 15:52:13+00:00s,   1,           
	0,              1619,               garmin,      
	-               3.0,                local      
      2018-08-03 16:15:36+00:00s,   creator,     
	-               fr230,              garmin,      
	3918730542,     7.1,                local      
      2018-08-03 16:15:36+00:00s,   1,           
	0,              1619,               garmin,      
	-               3.0,                local      

    record
      timestamp,                    distance,
	enhanced_altitude,      enhanced_speed,
	position_lat,           position_long      
      2018-08-03 15:52:13+00:00s,   1.44m,   
	617.2m,                 1.176m/s,      
	-33.42752396129072°,    -70.60802654363215°
      2018-08-03 15:52:20+00:00s,   13.22m,  
	616.5999999999999m,     1.997m/s,      
	-33.42753980308771°,    -70.60791338793933°
      2018-08-03 15:52:37+00:00s,   73.97m,  
	618.0m,                 2.034m/s,      
	-33.428066186606884°,   -70.60771004296839°
    [...]
      2018-08-03 16:14:53+00:00s,   6317.99m,
	600.5999999999999m,     7.203m/s,      
	-33.42879055067897°,    -70.60721852816641°
      2018-08-03 16:15:01+00:00s,   6378.29m,
	599.5999999999999m,     7.017m/s,      
	-33.428278835490346°,   -70.607436792925°  
      2018-08-03 16:15:11+00:00s,   6440.3m, 
	596.8m,                 6.149m/s,      
	-33.42774691991508°,    -70.60764122754335°
      2018-08-03 16:15:31+00:00s,   6500.22m,
	594.8m,                 0.0m/s,        
	-33.427340649068356°,   -70.60799863189459°

In the example above some details have been elided with `[...]`.

The `event`, `device_info` and `record` messages are displayed in
tabular format; all others are listed beforehand.

Some fields could not be completely parsed.  This is not unusual with
the FIT format, which is very extensible and incompletely documented.
Sucj fields are marker by `-`.

