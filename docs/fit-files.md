
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
  
  * [The `messages` format](#the-messages-format) - this displays the
    low-level binary data and is mostly of use when debugging errors.

  * [The `fields` format](#the-fields-format) - a more detailed
    low-level display that is also mostly used for debugging.

  * [The `csv` format](#the-csv-format) - used to compare test data
    with the examples provided in the
    [SDK](https://www.thisisant.com/resources/fit).

* [Third party API use](#third-party-api-use)

* [Implementation and limitations](#implementation-and-limitations)

## Displaying FIT Data

For details of all the options:

    ch2 dump-fit -h

### The `records` Format

#### Example Usage

    ch2 -v 0 dump-fit FILE

    ch2 -v 0 dump-fit --records FILE

    ch2 -v 0 dump-fit --records --all-fields --all-messages FILE

    ch2 -v 0 dump-fit --records --after N1 --limit N2 FILE

Note that `-v 0` is used to supress any logging that would otherwise
confuse the output to the screen.  Logs are still written to the logs
directory.

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
Such fields are marker by `-`.

### The `messages` Format

#### Example Usage

    ch2 -v 0 dump-fit --messages FILE

    ch2 -v 0 dump-fit --messages --after N1 --limit N2 FILE

#### Format Description

Messages are displayed, one per line, as hex values.  The data are
preceded by the record number, offset (in bytes from the file start),
and type.

#### Example Output

    000 00000 HDR 0c106400f50200002e464954
    001 00012 DFN 40000100000503048c040486010284020284000100
    002 00033 DTA 007fffffff29e60712000f000104
    003 00047 DFN 400001003102000284010102
    004 00059 DFN 400001003101000284
    005 00068 DTA 0000f0
    006 00071 DFN 410001001505fd0486030486000100010100040102
    007 00092 DFN 410001001505fd0486030100000100010100040102
    008 00113 DTA 0129e6071200000000
    009 00122 DFN 420001001406fd0486000485010485050486020284060284
    010 00146 DTA 0229e607121d85612ecbfbb497000000020f330000
    011 00167 DTA 0229e607131d85612ecbfbb498000000020f330000
    012 00188 DTA 0229e607141d85612ecbfbb498000000020f330000
    013 00209 DTA 0229e607151d856139cbfbb482000000150f330000
    014 00230 DTA 0229e607161d856140cbfbb4790000001c0f330000
    015 00251 DTA 0229e607171d856146cbfbb472000000230f330000
    016 00272 DTA 0229e607181d85614acbfbb46c000000290f330000
    017 00293 DTA 0229e607191d856177cbfbb414000000720f330000
    018 00314 DTA 0229e6071a1d85618dcbfbb3b4000000b90f33005c
    019 00335 DTA 0229e6071b1d8561aecbfbb33c000001130f330098
    020 00356 DTA 0229e6071c1d8561cccbfbb2d70000015f0f3300d1
    021 00377 DTA 0229e6071d1d8561aacbfbb279000001a60f330106
    022 00398 DTA 0229e6071e1d85615fcbfbb28d000001ed0f330133
    023 00419 DTA 0229e6071f1d856112cbfbb2570000023d0f330170
    024 00440 DTA 0129e6071f00000400
    025 00449 DFN 430001001314fd0486020486030485040485050485060485070486080486090486fe02840b02840c02840d02840e0284150284160284000100010100180100190100
    026 00515 DTA 0329e607a329e607121d85612ecbfbb4971d856112cbfbb257000035b5000035b50000023d00000000000001a101700000000009010701
    027 00570 DFN 410001001505fd0486030486000100010100040102
    028 00591 DTA 0129e607a300000001080901
    [...]
    219 04931 DTA 0d7d33c73572793ae81f59cacdf7a309007f15231c
    220 04952 DTA 0d8533c7354b913ae8f34ecacd85bb09007a15691b
    221 04973 DTA 0d8f33c73515aa3ae86c45cacdbed309006c150518
    222 04994 DTA 02a333c73501000000000400
    223 05006 DTA 02a333c735040000002603ff
    224 05018 DTA 0da333c73504bd3ae8c434cacd26eb090062150000
    225 05039 DFN 4f00008c0015fd04860204850304850504850604850704850902840a02840e02840f02841002840001020101020401020801020b01000c01000d0102110101120102130102
    226 05108 DTA 0fa733c735000000000000000000000000000000000000000004000110ffffffffffff3c000a000200007fffff
    227 05153 DTA 02a733c735040000002603ff
    228 05165 DTA 02a833c73500000000000400
    229 05177 DTA 03a833c7352e1593e9ffffffffffffffffffffffffffffffff0000000001006d08c602ffff000000ffffffff00ffff05
    230 05225 DTA 03a833c73500000000ffffffffffffffffffffffffffffffff00000000010053062c01ffff00000100ffffff00ffff05
    231 05273 DFN 400000130029fd04860204860304850404850504850604850704860804860904860a04861b04851c04851d04851e0485fe02840b02840d02840e02841502841602844702844d02844e02844f02840001000101000f01021001021101021201021701001801001901001a0102270100320101330101480100500102510102520102
    232 05402 DTA 00dc33c7352d2ec73579b43ae87733cacd04bd3ae8c434cacdbe571500e8bd110026eb0900ffffffff1dbd3ae8861bcfcda34439e87733cacd0000c100d615672023005100ffffffffffffffff0901ffffffffff0702ff007f7fffffffff
    233 05496 DFN 41000012002cfd04860204860304850404850704860804860904860a04861d04851e04851f04852004854e04866e1007fe02840b02840e02840f02841602841702841902841a02845902845a02845b02840001000101000501000601001001021101021201021301021801021b01021c01003901013a01015101005c01025d01025e01026d01026f0102
    234 05634 DTA 01dc33c7352d2ec73579b43ae87733cacdbe571500e8bd110026eb0900ffffffff1dbd3ae8861bcfcda34439e87733cacdffffffff42696b650000000000000000000000000000c100d61567202300510000000100ffffffffffff09010200ffffffffffff007f7f00ffffffffff
    235 05744 DFN 440000220008fd0486000486050486010284020100030100040100060102
    236 05774 DTA 04dc33c735e8bd11009cfbc6350100001a01ff
    237 05793 CRC 01a2

The example above shows header (HDR), definition (DFN), data (DTA),
and checksum (CRC) messages.

### The `fields` Format

#### Example Usage

    ch2 -v 0 dump-fit --fields FILE

    ch2 -v 0 dump-fit --fields --after N1 --limit N2 FILE

#### Format Description

Messages and fields are displayed as hex values.  The message data are
preceded by the record number, offset (in bytes from the file start),
and type.

#### Example Output

    000 00000 HDR 0e10de07931600002e4649541e51
      0e - header
      10 - protocol version
      de07 - profile version
      93160000 - data size
      2e464954 - data type
      1e51 - checksum
    001 00014 DFN 40000000000703048c040486070486010284020284050284000100
      40 - header (msg 0)
      00 - reserved
      00 - architecture
      0000 - msg no (file_id)
      07 - no of fields
	03048c - fld 0: serial_number (uint32z)
	040486 - fld 1: time_created (uint32)
	070486 - fld 2: unknown (uint32)
	010284 - fld 3: manufacturer (uint16)
	020284 - fld 4: product (uint16)
	050284 - fld 5: number (uint16)
	000100 - fld 6: type (enum)
    002 00041 DTA 002e1593e92c2ec735ffffffff01006d08ffff04
      00 - header (msg 0 - file_id)
      2e1593e9 - serial_number (uint32z)
      2c2ec735 - time_created (uint32)
      ffffffff - unknown (uint32)
      0100 - manufacturer (uint16)
      6d08 - product (uint16)
      ffff - number (uint16)
      04 - type (enum)
    [...]
    235 05744 DFN 440000220008fd0486000486050486010284020100030100040100060102
      44 - header (msg 4)
      00 - reserved
      00 - architecture
      2200 - msg no (activity)
      08 - no of fields
	fd0486 - fld 0: timestamp (uint32)
	000486 - fld 1: total_timer_time (uint32)
	050486 - fld 2: local_timestamp (uint32)
	010284 - fld 3: num_sessions (uint16)
	020100 - fld 4: type (enum)
	030100 - fld 5: event (enum)
	040100 - fld 6: event_type (enum)
	060102 - fld 7: event_group (uint8)
    236 05774 DTA 04dc33c735e8bd11009cfbc6350100001a01ff
      04 - header (msg 4 - activity)
      dc33c735 - timestamp (uint32)
      e8bd1100 - total_timer_time (uint32)
      9cfbc635 - local_timestamp (uint32)
      0100 - num_sessions (uint16)
      00 - type (enum)
      1a - event (enum)
      01 - event_type (enum)
      ff - event_group (uint8)
    237 05793 CRC 01a2
      01a2 - checksum

### The `csv` Format

#### Example Usage

    ch2 -v 0 dump-fit --csv FILE

    ch2 -v 0 dump-fit --csv --after N1 --limit N2 FILE

#### Format Description

The output generated is tailored to match the CSV format used by the
FIT SDK in their examples.  Exceptions are decribed in [implementation
and limitations](#implementation-and-limitations).

#### Example Output

    Definition,0,file_id,serial_number,1,,time_created,1,,unknown,1,,manufacturer,1,,number,1,,type,1,,product,1,
    Data,0,file_id,serial_number,3918730542,,time_created,902245932,,@9:13,,,manufacturer,1,,number,,,type,4,,garmin_product,2157,
    Definition,1,file_creator,software_version,1,,hardware_version,1,
    Data,1,file_creator,software_version,710,,hardware_version,,
    Definition,2,event,timestamp,1,,event,1,,event_type,1,,event_group,1,,data,1,
    Data,2,event,timestamp,902245933,s,event,0,,event_type,0,,event_group,0,,timer_trigger,0,
    Definition,3,device_info,timestamp,1,,serial_number,1,,cum_operating_time,1,,unknown,1,,unknown,1,,unknown,1,,unknown,1,,manufacturer,1,,software_version,1,,battery_voltage,1,,ant_device_number,1,,device_index,1,,hardware_version,1,,unknown,1,,battery_status,1,,ant_transmission_type,1,,ant_network,1,,unknown,1,,source_type,1,,product,1,,device_type,1,
    Data,3,device_info,timestamp,902245933,s,serial_number,3918730542,,cum_operating_time,,s,@13:17,,,@17:21,,,@21:25,,,@25:29,,,manufacturer,1,,software_version,7.1,,battery_voltage,,V,ant_device_number,,,device_index,0,,hardware_version,,,@42:43,,,battery_status,,,ant_transmission_type,,,ant_network,,,@46:47,,,source_type,5,,garmin_product,2157,,device_type,,
    [...]
    Definition,0,lap,timestamp,1,,start_time,1,,start_position_lat,1,,start_position_long,1,,end_position_lat,1,,end_position_long,1,,total_elapsed_time,1,,total_timer_time,1,,total_distance,1,,unknown,1,,unknown,1,,unknown,1,,unknown,1,,message_index,1,,total_calories,1,,avg_speed,1,,max_speed,1,,total_ascent,1,,total_descent,1,,wkt_step_index,1,,avg_vertical_oscillation,1,,avg_stance_time_percent,1,,avg_stance_time,1,,event,1,,event_type,1,,avg_heart_rate,1,,max_heart_rate,1,,intensity,1,,lap_trigger,1,,sport,1,,event_group,1,,sub_sport,1,,avg_temperature,1,,max_temperature,1,,unknown,1,,avg_fractional_cadence,1,,max_fractional_cadence,1,,total_fractional_cycles,1,,total_cycles,1,,avg_cadence,1,,max_cadence,1,
    Data,0,lap,timestamp,902247388,s,start_time,902245933,,start_position_lat,-398805895,semicircles,start_position_long,-842386569,semicircles,end_position_lat,-398803708,semicircles,end_position_long,-842386236,semicircles,total_elapsed_time,1398.718,s,total_timer_time,1162.728,s,total_distance,6500.22,m,@41:45,-398803683,,@45:49,-842065018,,@49:53,-398900061,,@53:57,-842386569,,message_index,0,,total_calories,193,kcal,avg_speed,COMPOSITE,m/s,enhanced_avg_speed,5.59,m/s,max_speed,COMPOSITE,m/s,enhanced_max_speed,8.295,m/s,total_ascent,35,m,total_descent,81,m,wkt_step_index,,,avg_vertical_oscillation,,mm,avg_stance_time_percent,,percent,avg_stance_time,,ms,event,9,,event_type,1,,avg_heart_rate,,bpm,max_heart_rate,,bpm,intensity,,,lap_trigger,7,,sport,2,,event_group,,,sub_sport,0,,avg_temperature,,C,max_temperature,,C,@90:91,,,avg_fractional_cadence,,rpm,max_fractional_cadence,,rpm,total_fractional_cycles,,cycles,total_cycles,,cycles,avg_cadence,,rpm,max_cadence,,rpm
    Definition,1,session,timestamp,1,,start_time,1,,start_position_lat,1,,start_position_long,1,,total_elapsed_time,1,,total_timer_time,1,,total_distance,1,,nec_lat,1,,nec_long,1,,swc_lat,1,,swc_long,1,,unknown,1,,unknown,16,,message_index,1,,total_calories,1,,avg_speed,1,,max_speed,1,,total_ascent,1,,total_descent,1,,first_lap_index,1,,num_laps,1,,avg_vertical_oscillation,1,,avg_stance_time_percent,1,,avg_stance_time,1,,event,1,,event_type,1,,sport,1,,sub_sport,1,,avg_heart_rate,1,,max_heart_rate,1,,total_training_effect,1,,event_group,1,,trigger,1,,avg_temperature,1,,max_temperature,1,,unknown,1,,avg_fractional_cadence,1,,max_fractional_cadence,1,,total_fractional_cycles,1,,unknown,1,,sport_index,1,,total_cycles,1,,avg_cadence,1,,max_cadence,1,
    Data,1,session,timestamp,902247388,s,start_time,902245933,,start_position_lat,-398805895,semicircles,start_position_long,-842386569,semicircles,total_elapsed_time,1398.718,s,total_timer_time,1162.728,s,total_distance,6500.22,m,nec_lat,-398803683,semicircles,nec_long,-842065018,semicircles,swc_lat,-398900061,semicircles,swc_long,-842386569,semicircles,@49:53,,,@53:69,Bike,,message_index,0,,total_calories,193,kcal,avg_speed,COMPOSITE,m/s,enhanced_avg_speed,5.59,m/s,max_speed,COMPOSITE,m/s,enhanced_max_speed,8.295,m/s,total_ascent,35,m,total_descent,81,m,first_lap_index,0,,num_laps,1,,avg_vertical_oscillation,,mm,avg_stance_time_percent,,percent,avg_stance_time,,ms,event,9,,event_type,1,,sport,2,,sub_sport,0,,avg_heart_rate,,bpm,max_heart_rate,,bpm,total_training_effect,,,event_group,,,trigger,0,,avg_temperature,,C,max_temperature,,C,@104:105,0,,avg_fractional_cadence,,rpm,max_fractional_cadence,,rpm,total_fractional_cycles,,cycles,@108:109,,,sport_index,,,total_cycles,,cycles,avg_cadence,,rpm,max_cadence,,rpm
    Definition,4,activity,timestamp,1,,total_timer_time,1,,local_timestamp,1,,num_sessions,1,,type,1,,event,1,,event_type,1,,event_group,1,
    Data,4,activity,timestamp,902247388,,total_timer_time,1162.728,s,local_timestamp,902232988,,num_sessions,1,,type,0,,event,26,,event_type,1,,event_group,,

## Third Party API Use

The main entry point is `filtered_records` in `choochoo.fit.format.tokens`.

This takes the following arguments:

* `log` - an instance of the standard Python logger.

* `fit_path` - the path to the FIT format file.

* `after=0` - the number of records to skip on reading.

* `limit=-1` - the number of records to return on reading (-1 implines all).

* `profile_path=None` - the path to the `Profile.xlsx` file in the
  sdk.  If `None` then the "pickled" cache is used.

It returns the following values:

* `data` - the raw data (`bytes`) from the FIT file

* `types` - an instance of `choochoo.fit.profile.types.Types`
  describing the types in `Profile.xlsx` (the first sheet).

* `messages` - an instance of `choochoo.fit.profile.messages.Messages`
  describing the messages in `Profile.xslx` (the second sheet).

* `generator` - an iterator over
  `choochoo.fit.profile.record.LazyRecord` instances that describe the
  records in the FIT file.  The `data` attribute is an iterator over
  the fields within a record, structures as `(name, (values, units))`
  where `name` and `units` are strings (`units` is `None` if no units
  are defined), and `values` is a tuple of string values.

Both `generator` and the `data` attribute are lazy - the data are
generated only on demand and are available just once.  To make the
data permanent use `list(generator)` and `LazyRecord.force()`.

## Implementation and Limitations

The `Profile.xlsx` spreadsheet included in the FIT SDK is read
directly by the Python code and used to generate an in-memory
description of the known fields and messages.  This is then saved to
disk ("pickled" in Python parlance) so that it can be read quickly
when needed.

Details of parsing the data are done lazily wherever possible.  So if
a program only wants to read a certain kind of message it does not
have to do the work of decoding all the other message types.

The code is validated against the examples provided in the ANT SDK and
has the following known limtations:

* Accumulated fields are broken.

* The code cannot reproduce the values for the `timer_trigger` fields
  in the Activity example.

* The order of fields (within a single message) returned is not
  guaranteed to match the order of fields in the raw data or the order
  used in the CSV examples.

* The CSV data in the examples sometimes specifies floating point
  whole numbers (eg 2.0) where this library returns integers (eg 2).

* The CSV data in the examples include a value for *composite* fields
  (as well as the values for the sub-fields).  This library does not
  return these values (which do not appear to be well-defined) but,
  for the `csv` format only, returns the field name along with the
  value `COMPOSITE`.

* The CSV examples in the FIT SDK include a title row and empty fields
  as padding on some lines.  This is not duplicated by the CSV format
  output from this library.
  