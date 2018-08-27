
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
