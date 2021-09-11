import {sprintf} from "sprintf-js";
import {last} from "../../../../common/functions";
import {scaleLinear} from "d3-scale";
import {Grid, Slider, useTheme} from "@material-ui/core";
import log from "loglevel";
import {Area, Circle, Line, LinePath} from "@visx/shape";
import {AxisBottom, AxisLeft, AxisRight} from "@visx/axis";
import {ParentSize} from "@visx/responsive";
import React, {useState} from "react";
import {ColumnCard, Text} from "../../../../common/elements";


function hms(seconds) {
    const s = seconds % 60;
    const m = Math.round(((seconds - s) / 60) % 60);
    const h = Math.round(((seconds - s) / 60 - m) / 60);
    if (h > 0) return sprintf('%0d:%02d:%02d', h, m, s);
    if (m > 0) return sprintf('%d:%02d', m, s);
    return sprintf('%d', s);
}


function Comparison(props) {

    const {width, height, slider, fast, slow, min, max, fColour, sColour,
        margin={top: 10, bottom: 40, left: 40, right: 40}} = props;

    const sliderFast = interpolate(fast, slider * last(fast).distance, 'distance');
    const slowAtTime = interpolate(slow, sliderFast.time, 'time');
    const slowAtDistance = interpolate(slow, sliderFast.distance, 'distance');

    const distanceScale = scaleLinear([0, max.distance], [margin.left, width-margin.right]);
    // note inversion of y axis
    const timeScale = scaleLinear([0, max.time], [height-margin.bottom, margin.top]);
    const elevationScale = scaleLinear([min.elevation, max.elevation], [height-margin.bottom, margin.top]);

    const theme = useTheme();
    const fg = theme.palette.text.secondary;
    const fs = 10;
    function tlp(anchor, dy=0) {
        return () => ({fill: fg, fontSize: fs, textAnchor: anchor, dy: dy});
    }

    return (<svg width='100%' height={height}>
        <Area data={fast} fill={fg} opacity={0.05}
              x={fast => distanceScale(fast.distance)}
              y1={fast => elevationScale(fast.elevation)} y0={fast => height-margin.bottom}/>
        <LinePath data={fast} stroke={fg} strokeWidth={1} opacity={0.2}
                  x={fast => distanceScale(fast.distance)} y={fast => elevationScale(fast.elevation)}/>
        <LinePath data={slow} stroke={sColour} strokeWidth={2}
                  x={slow => distanceScale(slow.distance)} y={slow => timeScale(slow.time)}/>
        <LinePath data={fast} stroke={fColour} strokeWidth={2}
                  x={fast => distanceScale(fast.distance)} y={fast => timeScale(fast.time)}/>
        <Line stroke={sColour} opacity={0.5}
              from={{x: distanceScale(slowAtTime.distance), y: margin.top}}
              to={{x: distanceScale(slowAtTime.distance), y: height-margin.bottom}}/>
        <Circle fill={sColour} cx={distanceScale(slowAtTime.distance)} cy={timeScale(slowAtTime.time)} r={3}/>
        <Line stroke={sColour} opacity={0.5}
              from={{x: margin.left, y: timeScale(slowAtDistance.time)}}
              to={{x: width-margin.right, y: timeScale(slowAtDistance.time)}}/>
        <Circle fill={sColour} cx={distanceScale(slowAtDistance.distance)} cy={timeScale(slowAtDistance.time)}
                r={3}/>
        <Line stroke={fColour} opacity={0.5}
              from={{x: distanceScale(sliderFast.distance), y: margin.top}}
              to={{x: distanceScale(sliderFast.distance), y: height-margin.bottom}}/>
        <Line stroke={fColour} opacity={0.5}
              from={{x: margin.left, y: timeScale(sliderFast.time)}}
              to={{x: width-margin.right, y: timeScale(sliderFast.time)}}/>
        <Circle fill={fColour} cx={distanceScale(sliderFast.distance)} cy={timeScale(sliderFast.time)} r={3}/>
        <text x={0.87 * width} y={0.8 * height} fontSize={fs+2} fill={fg} textAnchor='end'>
            {sprintf('%.1fs / %.1fm', slowAtDistance.time - sliderFast.time,
                1000 * (sliderFast.distance - slowAtTime.distance))}
        </text>
        <AxisLeft scale={timeScale} left={margin.left} stroke={fg}
                  tickStroke={fg} tickLabelProps={tlp('end', '0.25em')} tickFormat={hms}/>
        <text x={0} y={0} transform={`translate(${margin.left+15},${margin.top})\nrotate(-90)`} fontSize={fs}
              textAnchor='end' fill={fg}>Time / hms</text>
        <AxisRight scale={elevationScale} left={width-margin.right} stroke={fg}
                   tickStroke={fg} tickLabelProps={tlp('start', '0.25em')}/>
        <text x={0} y={0} transform={`translate(${width-margin.right-10},${margin.top})\nrotate(-90)`} fontSize={fs}
              textAnchor='end' fill={fg}>Elevation / m</text>
        <AxisBottom scale={distanceScale} top={height-margin.bottom} stroke={fg}
                    tickStroke={fg} tickLabelProps={tlp('middle')}
                    labelProps={{fill: fg, fontSize: fs, textAnchor: 'middle'}} label='Distance / km'/>
    </svg>);
}


function interpolate(data, value, key) {
    const [i, j, norm, iweight, jweight] = bracket(data, value, key);
    log.debug(i, j, norm, iweight, jweight);
    const result = {};
    Object.keys(data[0]).forEach(key => {
        result[key] = (data[i][key] * iweight + data[j][key] * jweight) / norm;
    })
    return result;
}


function bracket(data, value, key) {
    log.debug(value, key);
    let a = 0;
    let c = data.length-1;
    while (c - a > 1) {
        const b = Math.floor(0.5 + 0.5 * (a + c));
        if (data[b][key] > value) {
            c = b;
        } else {
            a = b;
        }
    }
    return [a, c, data[c][key] - data[a][key], data[c][key] - value, value - data[a][key]];
}


export default function AutoScaleComparison(props) {

    const {sector1, sector2, n=100} = props;
    const [slider, setSlider] = useState(0);
    const theme = useTheme();
    const [fast, zfast, fColour, slow, zslow, sColour] = last(sector1.edt.time) > last(sector2.edt.time) ?
        [sector2.edt, sector2.zipped_edt, theme.palette.primary.main,
            sector1.edt, sector1.zipped_edt, theme.palette.secondary.main] :
        [sector1.edt, sector1.zipped_edt, theme.palette.secondary.main,
            sector2.edt, sector2.zipped_edt, theme.palette.primary.main];
    const elevation = fast.elevation.concat(slow.elevation);
    const min = {distance: 0, time: 0, elevation: Math.min(...elevation)};
    const max = {distance: Math.max(...fast.distance, ...slow.distance),
        time: Math.max(...fast.time, ...slow.time),
        elevation: Math.max(...elevation)};

    return (<ColumnCard>
        <Grid item xs={12}>
            <ParentSize>
                {({ width: visWidth, height: visHeight }) =>
                    <Comparison width={visWidth ? visWidth : 500} height={300}
                                slider={slider} fast={zfast} slow={zslow}
                                min={min} max={max} fColour={fColour} sColour={sColour}/>}
            </ParentSize>
        </Grid>
        <Grid item xs={12}>
            <Slider value={slider} onChange={(event, value) => setSlider(value)}
                    min={0} max={1} step={1 / n}
                    color={fColour === theme.palette.primary.main ? 'primary' : 'secondary'}/>
            <Text>
                <p>Moving the slider selects a point on the faster activity and displays the time and distance
                    difference to the slower activity at the same distance or time, respectively.</p>
            </Text>
        </Grid>
    </ColumnCard>);
}
