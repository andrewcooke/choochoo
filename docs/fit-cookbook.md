
# FIT Cookbook

* [Installing Choocoo](#installing-choochoo)
* [Check a FIT File](#check-a-fit-file)
* [Check Many FIT Files](#check-many-fit-files)
* [Check Timestamps in a FIT File](#check-timestamps-in-a-fit-file)
* [Remove a Bad Timestamp from a FIT File](#remove-a-bad-timestamp-from-a-fit-file)
* [See What Data are Dropped](#see-what-data-are-dropped)
* [See What Data are Dropped in Detail](#see-what-data-are-dropped-in-detail)
* [Remove Arbitrary Data from a FIT File](#remove-arbitrary-data-from-a-fit-file)
* [Change the Times in a FIT File](#change-the-times-in-a-fit-file)
* [Search for Values in a FIT File](#search-for-values-in-a-fit-file)
* [Search for Values in a FIT File with Context](#search-for-values-in-a-fit-file-with-context)
* [Find FIT Files with Values](#find-fit-files-with-values)
* [Restrict Displayed Dates](#restrict-displayed-dates)
* [Read a FIT File in Python](#read-a-fit-file-in-python)

## Installing Choocoo

Instructions for install are [here](getting-started).

If you only want to use the python library programatically there is no
need to configure the system.

If you only want to use the `ch2 fit` and `ch2 fix-fit` commands, the
default configuration (`ch2 default-config`) is sufficient.

## Check a FIT File

To check for errors in `myfile.fit`:

    > ch2 fix-fit myfile.fit --discard
    [37m    INFO: [37mLogging to /home/andrew/.ch2/0-41/logs/fix-fit.log[0m
    [37m    INFO: [37mInput ----------[0m
    [37m    INFO: [37mReading binary data from myfile.fit[0m
    [37m    INFO: [37mInitial Data ----------[0m
    [37m    INFO: [37mLength: 5368 bytes[0m
    [37m    INFO: [37mHeader size: 14[0m
    [37m    INFO: [37mProtocol version: 16[0m
    [37m    INFO: [37mProfile version: 2014[0m
    [37m    INFO: [37mChecksum: 37636 (0x9304)[0m
    [37m    INFO: [37mValidation ----------[0m
    [37m    INFO: [37m--max-delta-t None[0m
    [37m WARNING: [36mTime-reversal is allowed unless max-delta-t is set[0m
    [37m    INFO: [37mFirst timestamp: 2018-07-26 13:34:49+00:00[0m
    [37m    INFO: [37mLast timestamp:  2018-07-26 13:59:18+00:00[0m
    [37m    INFO: [37mOK[0m
    [37m    INFO: [37mFinal Data ----------[0m
    [37m    INFO: [37mLength: 5368 bytes[0m
    [37m    INFO: [37mHeader size: 14[0m
    [37m    INFO: [37mProtocol version: 16[0m
    [37m    INFO: [37mProfile version: 2014[0m
    [37m    INFO: [37mChecksum: 37636 (0x9304)[0m
    [37m    INFO: [37mOutput ----------[0m
    [37m    INFO: [37mDiscarded output[0m


If there are no warnings or errors (as above) then the file is OK (as
far as my code can tell - to check timestamps see the next recipe).

## Check Many FIT Files

Maybe we have a collection of files and we want to know which have
problems.  Note that using `-v 2` reduces the logging to `ERROR` level
only (with `-v 0` we would see no logging, just the file names).

    > ch2 -v 2 fix-fit --name-bad *.fit
    [37m   ERROR: [1;31mData size incorrect (1542/757+12+2=771)[0m
    activity-activity-filecrc.fit
    [37m   ERROR: [1;31mBad checksum (a1d5/b1d5)[0m
    activity-filecrc.fit
    [37m   ERROR: [1;31mData size incorrect (854/757+12+2=771)[0m
    activity-settings-corruptheader.fit
    [37m   ERROR: [1;31mData size incorrect (853/757+12+2=771)[0m
    activity-settings.fit
    [37m   ERROR: [1;31mData size incorrect (786/757+12+2=771)[0m
    activity-settings-nodata.fit
    [37m   ERROR: [1;31mData size incorrect (768/757+12+2=771)[0m
    activity-unexpected-eof.fit
    [37m   ERROR: [1;31mData size incorrect (88904/58949+14+2=58965)[0m
    event_timestamp.fit


## Check Timestamps in a FIT File

To check that the timestamp never increases by more than 60s between
records:

    > ch2 fix-fit myfile.fit --max-delta-t 60 --discard
    [37m    INFO: [37mLogging to /home/andrew/.ch2/0-41/logs/fix-fit.log[0m
    [37m    INFO: [37mInput ----------[0m
    [37m    INFO: [37mReading binary data from myfile.fit[0m
    [37m    INFO: [37mInitial Data ----------[0m
    [37m    INFO: [37mLength: 5368 bytes[0m
    [37m    INFO: [37mHeader size: 14[0m
    [37m    INFO: [37mProtocol version: 16[0m
    [37m    INFO: [37mProfile version: 2014[0m
    [37m    INFO: [37mChecksum: 37636 (0x9304)[0m
    [37m    INFO: [37mValidation ----------[0m
    [37m    INFO: [37m--max-delta-t 60.0[0m
    [37m    INFO: [37mFirst timestamp: 2018-07-26 13:34:49+00:00[0m
    [37m   ERROR: [1;31mToo large shift in timestamp (273.0s: 2018-07-26 13:54:45+00:00/2018-07-26 13:59:18+00:00[0m
    [37m    INFO: [37mValidation failed[0m
    [37mCRITICAL: [1;31mToo large shift in timestamp (273.0s: 2018-07-26 13:54:45+00:00/2018-07-26 13:59:18+00:00[0m
    Traceback (most recent call last):
      File "/home/andrew/project/choochoo/py/ch2/__init__.py", line 111, in main
        command(config)
      File "/home/andrew/project/choochoo/py/ch2/commands/fix_fit.py", line 68, in fix_fit
        data = fix(data, warn=args[WARN],
      File "/home/andrew/project/choochoo/py/ch2/fit/fix.py", line 49, in fix
        validate_data(data, State(types, messages, max_delta_t=max_delta_t), warn=warn, force=force)
      File "/home/andrew/project/choochoo/py/ch2/fit/fix.py", line 258, in validate_data
        token = token_factory(data[offset:], state)
      File "/home/andrew/project/choochoo/py/ch2/fit/format/tokens.py", line 556, in token_factory
        token = Data(data, state)
      File "/home/andrew/project/choochoo/py/ch2/fit/format/tokens.py", line 292, in __init__
        super().__init__('DTA', data, state, data[0] & 0x0f)
      File "/home/andrew/project/choochoo/py/ch2/fit/format/tokens.py", line 223, in __init__
        self.__parse_timestamp(data, state)
      File "/home/andrew/project/choochoo/py/ch2/fit/format/tokens.py", line 236, in __parse_timestamp
        state.timestamp = times[0]
      File "/home/andrew/project/choochoo/py/ch2/fit/format/tokens.py", line 581, in timestamp
        self._timestamp = self._validate_timestamp(timestamp)
      File "/home/andrew/project/choochoo/py/ch2/fit/format/tokens.py", line 586, in _validate_timestamp
        raise Exception('Too large shift in timestamp (%.1fs: %s/%s' %
    Exception: Too large shift in timestamp (273.0s: 2018-07-26 13:54:45+00:00/2018-07-26 13:59:18+00:00
    [37m    INFO: [37mSee `ch2 help` for available commands.[0m
    [37m    INFO: [37mDocs at http://andrewcooke.github.io/choochoo[0m


Here we can see that there was a jump of 273 seconds.

## Remove a Bad Timestamp from a FIT File

The `fix-fit` command can "drop" data that cause errors.  In this case
(compare timestamps in the two recipes above) it is the final
timestamp that apperas to be wrong.  So we can drop that without
worrying about further, incorrect timestamps.

Note that dropping a record may remove important information from the
file (see below to understand what information is removed).

The command to drop data is (see notes below):

    > ch2 fix-fit myfile.fit --max-delta-t 60 --drop --fix-header --fix-checksum --max-fwd-len 500 -o fixed.fit
    [37m    INFO: [37mLogging to /home/andrew/.ch2/0-41/logs/fix-fit.log[0m
    [37m    INFO: [37mInput ----------[0m
    [37m    INFO: [37mReading binary data from myfile.fit[0m
    [37m    INFO: [37mInitial Data ----------[0m
    [37m    INFO: [37mLength: 5368 bytes[0m
    [37m    INFO: [37mHeader size: 14[0m
    [37m    INFO: [37mProtocol version: 16[0m
    [37m    INFO: [37mProfile version: 2014[0m
    [37m    INFO: [37mChecksum: 37636 (0x9304)[0m
    [37m    INFO: [37mDrop Data ----------[0m
    [37m    INFO: [37m--min-sync-cnt 3[0m
    [37m    INFO: [37m--max-record-len None[0m
    [37m    INFO: [37m--max-drop-cnt 1[0m
    [37m    INFO: [37m--max-back-cnt 3[0m
    [37m    INFO: [37m--max-fwd-len 500[0m
    [37m    INFO: [37m--max-delta-t 60.0[0m
    [37m    INFO: [37mRead complete from 5366[0m
    [37m    INFO: [37mFound slices :4975[0m
    [37m    INFO: [37mSlice ----------[0m
    [37m    INFO: [37mSlices: :4975[0m
    [37m    INFO: [37mHave 4975 bytes after slicing[0m
    [37m WARNING: [36mSlicing decreased length by 393 bytes[0m
    [37m    INFO: [37mHeader and Checksums ----------[0m
    [37m    INFO: [37m--header-size None[0m
    [37m    INFO: [37m--protocol-version None[0m
    [37m    INFO: [37m--profile-version None[0m
    [37m WARNING: [36mFixing header data size: 5352 -> 4959[0m
    [37m WARNING: [36mFixing header checksum: 067b -> 5447[0m
    [37m WARNING: [36mAdding 2 byte(s) for checksum[0m
    [37m WARNING: [36mFixing final checksum: 0000 -> 8cdf[0m
    [37m WARNING: [36mFixing header data size: 4959 -> 4961[0m
    [37m WARNING: [36mFixing header checksum: 5447 -> ccc5[0m
    [37m    INFO: [37mValidation ----------[0m
    [37m    INFO: [37m--max-delta-t 60.0[0m
    [37m    INFO: [37mFirst timestamp: 2018-07-26 13:34:49+00:00[0m
    [37m    INFO: [37mLast timestamp:  2018-07-26 13:54:45+00:00[0m
    [37m    INFO: [37mOK[0m
    [37m    INFO: [37mFinal Data ----------[0m
    [37m    INFO: [37mLength: 4977 bytes[0m
    [37m    INFO: [37mHeader size: 14[0m
    [37m    INFO: [37mProtocol version: 16[0m
    [37m    INFO: [37mProfile version: 2014[0m
    [37m    INFO: [37mChecksum: 36063 (0x8cdf)[0m
    [37m    INFO: [37mOutput ----------[0m
    [37m    INFO: [37mWriting binary data to fixed.fit[0m


Note that:

  * We specified a maximum amount to drop of 500 bytes (`--max-fwd-len
    500`).  The default is 200, but was insufficient in this case.
    Using a larger value makes the program run slower, so don't do
    this unless necessary.

  * We specified an output file (`-o fixed.fit`).

  * Reading the output above, we can see that the first 4975 bytes of
    data were used.  We will use this in the next recipe.

## See What Data are Dropped

In the recipe above data were dropped after the first 4975 bytes.  We
can see what records that affected as follows:

    > ch2 fit records --after-bytes 4975 myfile.fit
    [37m    INFO: [37mLogging to /home/andrew/.ch2/0-41/logs/fit.log[0m
    
    207 04975 lap
      end_position_lat: -33.42734768986702°,
      end_position_long: -70.60800148174167°,     enhanced_avg_speed: 5.577m/s,
      enhanced_max_speed: 7.838m/s,   event: lap,     event_type: stop,
      lap_trigger: session_end,   message_index: 0,   sport: cycling,
      start_position_lat: -33.42788371257484°,
      start_position_long: -70.60833390802145°,
      start_time: 2018-07-26 13:34:49+00:00,  sub_sport: generic,
      timestamp: 2018-07-26 13:59:18+00:00s,  total_ascent: 78m,
      total_calories: 181kcal,    total_descent: 49m,     total_distance: 5538.87m,
      total_elapsed_time: 1186.958s,  total_timer_time: 993.097s
    
    209 05207 session
      enhanced_avg_speed: 5.577m/s,   enhanced_max_speed: 7.838m/s,   event: lap,
      event_type: stop,   first_lap_index: 0,     message_index: 0,
      nec_lat: -33.42733050696552°,   nec_long: -70.58597140945494°,  num_laps: 1,
      sport: cycling,     start_position_lat: -33.42788371257484°,
      start_position_long: -70.60833390802145°,
      start_time: 2018-07-26 13:34:49+00:00,  sub_sport: generic,
      swc_lat: -33.435353580862284°,  swc_long: -70.60833390802145°,
      timestamp: 2018-07-26 13:59:18+00:00s,  total_ascent: 78m,
      total_calories: 181kcal,    total_descent: 49m,     total_distance: 5538.87m,
      total_elapsed_time: 1186.958s,  total_timer_time: 993.097s,
      trigger: activity_end
    
    211 05347 activity
      event: activity,    event_type: stop,   local_timestamp: 2018-07-26 09:59:18,
      num_sessions: 1,    timestamp: 2018-07-26 13:59:18+00:00,
      total_timer_time: 993.097s,     type: manual
    


That looks like metadata associated with ending an activity.  Probably
the "stop" button wasn't pressed until some minutes after the activity
ended.  Personally, I see no need to drop this data - it seems like
the jump in timestamps we saw has a reasonable explanation.

## See What Data are Dropped in Detail

Maybe we are a bit more curious about the data above.  What else can
we see?

Notice how the record numbers are `207`, `209`, and `211`.  Since
those are not consecutive there must be some internal messages also
present.  We can display those too:

    > ch2 fit records --after-bytes 4975 --internal myfile.fit
    [37m    INFO: [37mLogging to /home/andrew/.ch2/0-41/logs/fit.log[0m
    
    207 04975 lap
      end_position_lat: -33.42734768986702°,
      end_position_long: -70.60800148174167°,     enhanced_avg_speed: 5.577m/s,
      enhanced_max_speed: 7.838m/s,   event: lap,     event_type: stop,
      lap_trigger: session_end,   message_index: 0,   sport: cycling,
      start_position_lat: -33.42788371257484°,
      start_position_long: -70.60833390802145°,
      start_time: 2018-07-26 13:34:49+00:00,  sub_sport: generic,
      timestamp: 2018-07-26 13:59:18+00:00s,  total_ascent: 78m,
      total_calories: 181kcal,    total_descent: 49m,     total_distance: 5538.87m,
      total_elapsed_time: 1186.958s,  total_timer_time: 993.097s
    
    208 05069 definition
      architecture: b'\x00',  field_0: timestamp (uint32),
      field_1: start_time (uint32),   field_10: nec_long (sint32),
      field_11: swc_lat (sint32),     field_12: swc_long (sint32),
      field_13: unknown (uint8),  field_14: unknown (uint8),
      field_15: message_index (uint16),   field_16: total_calories (uint16),
      field_17: avg_speed (uint16),   field_18: max_speed (uint16),
      field_19: total_ascent (uint16),    field_2: start_position_lat (sint32),
      field_20: total_descent (uint16),   field_21: first_lap_index (uint16),
      field_22: num_laps (uint16),    field_23: avg_vertical_oscillation (uint16),
      field_24: avg_stance_time_percent (uint16),
      field_25: avg_stance_time (uint16),     field_26: event (enum),
      field_27: event_type (enum),    field_28: sub_sport (enum),
      field_29: avg_heart_rate (uint8),   field_3: start_position_long (sint32),
      field_30: max_heart_rate (uint8),   field_31: avg_cadence (uint8),
      field_32: max_cadence (uint8),  field_33: total_training_effect (uint8),
      field_34: event_group (uint8),  field_35: trigger (enum),
      field_36: avg_temperature (sint8),  field_37: max_temperature (sint8),
      field_38: unknown (uint8),  field_39: avg_fractional_cadence (uint8),
      field_4: total_elapsed_time (uint32),
      field_40: max_fractional_cadence (uint8),
      field_41: total_fractional_cycles (uint8),  field_42: unknown (uint8),
      field_43: sport_index (uint8),  field_5: total_timer_time (uint32),
      field_6: total_distance (uint32),   field_7: sport (enum),
      field_8: total_cycles (uint32),     field_9: nec_lat (sint32),
      local_message_type: 1,  message_name: session,  message_number: 18,
      no_of_fields: 44,   reserved: b'\x00'
    
    209 05207 session
      enhanced_avg_speed: 5.577m/s,   enhanced_max_speed: 7.838m/s,   event: lap,
      event_type: stop,   first_lap_index: 0,     message_index: 0,
      nec_lat: -33.42733050696552°,   nec_long: -70.58597140945494°,  num_laps: 1,
      sport: cycling,     start_position_lat: -33.42788371257484°,
      start_position_long: -70.60833390802145°,
      start_time: 2018-07-26 13:34:49+00:00,  sub_sport: generic,
      swc_lat: -33.435353580862284°,  swc_long: -70.60833390802145°,
      timestamp: 2018-07-26 13:59:18+00:00s,  total_ascent: 78m,
      total_calories: 181kcal,    total_descent: 49m,     total_distance: 5538.87m,
      total_elapsed_time: 1186.958s,  total_timer_time: 993.097s,
      trigger: activity_end
    
    210 05317 definition
      architecture: b'\x00',  field_0: timestamp (uint32),
      field_1: total_timer_time (uint32),     field_2: local_timestamp (uint32),
      field_3: num_sessions (uint16),     field_4: type (enum),
      field_5: event (enum),  field_6: event_type (enum),
      field_7: event_group (uint8),   local_message_type: 4,
      message_name: activity,     message_number: 34,     no_of_fields: 8,
      reserved: b'\x00'
    
    211 05347 activity
      event: activity,    event_type: stop,   local_timestamp: 2018-07-26 09:59:18,
      num_sessions: 1,    timestamp: 2018-07-26 13:59:18+00:00,
      total_timer_time: 993.097s,     type: manual
    
    212 05366 checksum
      checksum: 37636
    


Hmm.  Some message defintions and the checksum.  Nothing very
exciting.

We can also see the same data in binary form.  For example:

    > ch2 fit tokens --after-bytes 4975 myfile.fit
    [37m    INFO: [37mLogging to /home/andrew/.ch2/0-41/logs/fit.log[0m
    207 04975 DTA 00b687bc35f981bc35b5a33ae82425cacdb0bc3ae8a234cacd8e1c120049270f009f730800ffffffff7dbd3ae84f37cecd964739e82425cacd0000b500c9159e1e4e003100ffffffffffffffff0901ffffffffff0702ff007f7fffffffff
    208 05069 DFN 41000012002cfd04860204860304850404850704860804860904860a04861d04851e04851f04852004854e04866e1007fe02840b02840e02840f02841602841702841902841a02845902845a02845b02840001000101000501000601001001021101021201021301021801021b01021c01003901013a01015101005c01025d01025e01026d01026f0102
    209 05207 DTA 01b687bc35f981bc35b5a33ae82425cacd8e1c120049270f009f730800ffffffff7dbd3ae84f37cecd964739e82425cacdffffffff42696b650000000000000000000000000000b500c9159e1e4e00310000000100ffffffffffff09010200ffffffffffff007f7f00ffffffffff
    210 05317 DFN 440000220008fd0486000486050486010284020100030100040100060102
    211 05347 DTA 04b687bc3549270f00764fbc350100001a01ff
    212 05366 CRC 0493


## Remove Arbitrary Data from a FIT File

In the recipe above, perhaps we want to remove the `session` message
and its associated defintion.  This doesn't seem that smart an idea to
me, but it works as an example.

First, we note from the `tokens` dump that the data extend from offset
`5069` to `5316` (the end value is one before the next token at
`5317`).  We can remove that by taking the slices `:5069,5317:` as
follows:

    > ch2 fix-fit myfile.fit --slices :05069,05317: --fix-header --fix-checksum -o sliced.fit
    [37m    INFO: [37mLogging to /home/andrew/.ch2/0-41/logs/fix-fit.log[0m
    [37m    INFO: [37mInput ----------[0m
    [37m    INFO: [37mReading binary data from myfile.fit[0m
    [37m    INFO: [37mInitial Data ----------[0m
    [37m    INFO: [37mLength: 5368 bytes[0m
    [37m    INFO: [37mHeader size: 14[0m
    [37m    INFO: [37mProtocol version: 16[0m
    [37m    INFO: [37mProfile version: 2014[0m
    [37m    INFO: [37mChecksum: 37636 (0x9304)[0m
    [37m    INFO: [37mSlice ----------[0m
    [37m    INFO: [37mSlices: :5069,5317:-2[0m
    [37m    INFO: [37mHave 5118 bytes after slicing[0m
    [37m WARNING: [36mSlicing decreased length by 250 bytes[0m
    [37m    INFO: [37mHeader and Checksums ----------[0m
    [37m    INFO: [37m--header-size None[0m
    [37m    INFO: [37m--protocol-version None[0m
    [37m    INFO: [37m--profile-version None[0m
    [37m WARNING: [36mFixing header data size: 5352 -> 5102[0m
    [37m WARNING: [36mFixing header checksum: 067b -> ec8d[0m
    [37m WARNING: [36mAdding 2 byte(s) for checksum[0m
    [37m WARNING: [36mFixing final checksum: 0000 -> 99ab[0m
    [37m WARNING: [36mFixing header data size: 5102 -> 5104[0m
    [37m WARNING: [36mFixing header checksum: ec8d -> 6c0d[0m
    [37m    INFO: [37mValidation ----------[0m
    [37m    INFO: [37m--max-delta-t None[0m
    [37m WARNING: [36mTime-reversal is allowed unless max-delta-t is set[0m
    [37m    INFO: [37mFirst timestamp: 2018-07-26 13:34:49+00:00[0m
    [37m    INFO: [37mLast timestamp:  2018-07-26 13:59:18+00:00[0m
    [37m    INFO: [37mOK[0m
    [37m    INFO: [37mFinal Data ----------[0m
    [37m    INFO: [37mLength: 5120 bytes[0m
    [37m    INFO: [37mHeader size: 14[0m
    [37m    INFO: [37mProtocol version: 16[0m
    [37m    INFO: [37mProfile version: 2014[0m
    [37m    INFO: [37mChecksum: 39339 (0x99ab)[0m
    [37m    INFO: [37mOutput ----------[0m
    [37m    INFO: [37mWriting binary data to sliced.fit[0m


Note that `fix-fit` won't let you remove data that would corrupt the
file (to the best of its ability).

## Change the Times in a FIT File

    > ch2 fix-fit myfile.fit --start '2018-01-01 12:00:00' --fix-checksum -o fixed.fit
    [37m    INFO: [37mLogging to /home/andrew/.ch2/0-41/logs/fix-fit.log[0m
    [37m    INFO: [37mInput ----------[0m
    [37m    INFO: [37mReading binary data from myfile[0m
    [37m    INFO: [37mInitial Data ----------[0m
    [37m    INFO: [37mLength: 557213 bytes[0m
    [37m    INFO: [37mHeader size: 14[0m
    [37m    INFO: [37mProtocol version: 16[0m
    [37m    INFO: [37mProfile version: 2044[0m
    [37m    INFO: [37mChecksum: 36047 (0x8ccf)[0m
    [37m    INFO: [37mStart ----------[0m
    [37m    INFO: [37mStart: 2018-01-01 12:00:00[0m
    [37m WARNING: [36mShifting timestamps by -460d 21h36m33s[0m
    [37m    INFO: [37mHeader and Checksums ----------[0m
    [37m    INFO: [37m--header-size None[0m
    [37m    INFO: [37m--protocol-version None[0m
    [37m    INFO: [37m--profile-version None[0m
    [37m WARNING: [36mFixing final checksum: 8ccf -> 2b06[0m
    [37m    INFO: [37mValidation ----------[0m
    [37m    INFO: [37m--max-delta-t None[0m
    [37m WARNING: [36mTime-reversal is allowed unless max-delta-t is set[0m
    [37m    INFO: [37mFirst timestamp: 2018-01-01 12:00:00+00:00[0m
    [37m    INFO: [37mLast timestamp:  2018-01-01 17:35:24+00:00[0m
    [37m    INFO: [37mOK[0m
    [37m    INFO: [37mFinal Data ----------[0m
    [37m    INFO: [37mLength: 557213 bytes[0m
    [37m    INFO: [37mHeader size: 14[0m
    [37m    INFO: [37mProtocol version: 16[0m
    [37m    INFO: [37mProfile version: 2044[0m
    [37m    INFO: [37mChecksum: 11014 (0x2b06)[0m
    [37m    INFO: [37mOutput ----------[0m
    [37m    INFO: [37mWriting binary data to fixed.fit[0m


The `--start` value sets the first timestamp in the file.  Subsequent
timestamps have the same relative increment as before.

## Search for Values in a FIT File

For some reason we want to know if a file contains any speed values
over 7 m/s:

    > ch2 fit grep -p '.*speed>7' --compact myfile.fit
    usage: ch2 fit grep [-h] [--after-records N] [--limit-records N]
                        [--after-bytes N] [--limit-bytes N] [-w] [--no-validate]
                        [--max-delta-t S] [--name] [--not] [--match MATCH]
                        [--compact] [--context] --pattern MSG:FLD[=VAL]
                        [MSG:FLD[=VAL] ...] [--width WIDTH]
                        PATH [PATH ...]
    ch2 fit grep: error: the following arguments are required: --pattern


## Search for Values in a FIT File with Context

Seeing the results above we'd like to know more about the records
where we were over 7.5m/s:

    > ch2 fit grep -p 'record:enhanced_speed>7' --context myfile.fit
    usage: ch2 fit grep [-h] [--after-records N] [--limit-records N]
                        [--after-bytes N] [--limit-bytes N] [-w] [--no-validate]
                        [--max-delta-t S] [--name] [--not] [--match MATCH]
                        [--compact] [--context] --pattern MSG:FLD[=VAL]
                        [MSG:FLD[=VAL] ...] [--width WIDTH]
                        PATH [PATH ...]
    ch2 fit grep: error: the following arguments are required: --pattern


The search expression has the form `record:field=value` where `record`
and `field` are regular expressions.  If the `:` is omitted then the
record name is ignored.  The comparison can be `=`, `>`, `<` or `~` -
the last of these is for regular expression matching on the value.

## Find FIT Files with Values

This has made us curious.  Do we have any rides where we exceed 17m/s?

    > ch2 fit grep -p 'record:enhanced_speed>17' --match 0 --name *.fit
    usage: ch2 fit grep [-h] [--after-records N] [--limit-records N]
                        [--after-bytes N] [--limit-bytes N] [-w] [--no-validate]
                        [--max-delta-t S] [--name] [--not] [--match MATCH]
                        [--compact] [--context] --pattern MSG:FLD[=VAL]
                        [MSG:FLD[=VAL] ...] [--width WIDTH]
                        PATH [PATH ...]
    ch2 fit grep: error: the following arguments are required: --pattern


The `--name` flag displays filenames on matching, while `--match 0`
means that no matching data are displayed.

## Restrict Displayed Dates

The "usual" display options lets us restrict the range of records or
bytes, but not timestamps (or any other field).  But we can work
around this by using `--grep`:

    > ch2 fit grep -p '.*:timestamp>2018-03-04 11:56:33+00:00' '.*:timestamp<2018-03-04 12:00:00+00:00' -- myfile.fit
    usage: ch2 fit grep [-h] [--after-records N] [--limit-records N]
                        [--after-bytes N] [--limit-bytes N] [-w] [--no-validate]
                        [--max-delta-t S] [--name] [--not] [--match MATCH]
                        [--compact] [--context] --pattern MSG:FLD[=VAL]
                        [MSG:FLD[=VAL] ...] [--width WIDTH]
                        PATH [PATH ...]
    ch2 fit grep: error: the following arguments are required: --pattern


Note that we needed to explicitly include a wildcard record for the
timestamp because the timestamp value itself contains colons - without
the leading `.*:` the left-most colon in the timestamp would have been
taken as the record separator.

Also, it's worth understanding that comparisons with `--grep` are done
via strings *unless* the given pattern can be parsed as a float.

## Read a FIT File in Python

So maybe now we want to know what the maximum speed is in a file?  We
need to write some code to do that...

    from logging import basicConfig, getLogger, INFO
    from ch2.fit.profile.profile import read_fit, read_profile
    from ch2.fit.format.records import no_bad_values
    from ch2.fit.format.read import parse_data
    
    basicConfig(level=INFO)
    log = getLogger()
    
    data = read_fit('myfile.fit')
    types, messages = read_profile(log)
    state, tokens = parse_data(data, types, messages)
    
    SPEED = 'enhanced_speed'
    max_speed = None
    
    for offset, token in tokens:
        record = token.parse_token()
        data = record.as_dict(no_bad_values).data
        if SPEED in data:
            values, units = data[SPEED]
            for value in values:
                if max_speed is None or value > max_speed:
                    max_speed = value
    
    print('Maximum speed: %.2f' % max_speed)

Giving the output

    Maximum speed: 7.80


