import {scaleLinear, scaleTime} from "d3-scale";
import {linearRegression} from "simple-statistics";
import {Grid, useTheme} from "@material-ui/core";
import {AxisBottom, AxisLeft, Brush, Circle, Group, Line, ParentSize, PatternLines, RectClipPath} from "@visx/visx";
import React, {useState} from "react";
import {ColumnCard, Text} from "../../../../common/elements";


function between(start, date, finish) {
    return (start === null || start <= date) && (finish === null || date <= finish);
}


function Scatter(props) {

    const {width, height, sectors, sector1=null, sector2=null,
        start=null, finish=null, brush=false, setRange=null,
        margin={top: 10, bottom: 20, left: 40, right: 40}} = props;

    function speed(s) {return 3500 * s.distance / s.time;}
    const groups = [];
    if (sector1) groups.push(sector1.activity_group);
    if (sector2) groups.push(sector2.activity_group);
    const inGroup = (s) => (!groups.length || groups.includes(s.activity_group));

    const filtered = sectors.filter(s => between(start, s.date, finish));
    const min = {speed: Math.min(...filtered.map(s => speed(s))), date: Math.min(...filtered.map(s => s.date))};
    const max = {speed: Math.max(...filtered.map(s => speed(s))), date: Math.max(...filtered.map(s => s.date))};
    const speedScale = scaleLinear([min.speed, max.speed], [height-margin.bottom, margin.top]);
    const dateScale = scaleTime([start ? start : min.date, finish ? finish : max.date],
        [margin.left, width-margin.right]);

    const toFit = filtered.filter(inGroup).map(s => [dateScale(s.date), speedScale(speed(s))]);
    const fit = linearRegression(toFit);

    // brush doesn't handle margins correctly, so we do it ourselves (see Group)
    const brushWidth = width - margin.left - margin.right;
    const brushScale = scaleTime([start ? start : min.date, finish ? finish : max.date], [0, brushWidth]);

    const theme = useTheme();
    const fg = theme.palette.text.secondary;
    const fs = 10;
    function tlp(anchor, dy=0) {
        return () => ({fill: fg, fontSize: fs, textAnchor: anchor, dy: dy});
    }
    function fill(s) {
        if (sector1 && sector1.db === s.db) return theme.palette.secondary.main;
        if (sector2 && sector2.db === s.db) return theme.palette.primary.main;
        if (inGroup(s)) return fg;
        return null;
    }

    return (<svg width='100%' height={height}>
        {filtered.map(s => <Circle fill={fill(s)} cx={dateScale(s.date)} cy={speedScale(speed(s))} r={3}/>)}
        {brush ? (<Group left={margin.left}>
            <PatternLines id='pattern' height={8} width={8} stroke={fg} strokeWidth={1}
                          orientation={['diagonal']}/>
            <Brush xScale={brushScale} yScale={speedScale} width={brushWidth} height={height}
                   margin={margin} handleSize={8} resizeTriggerAreas={['left', 'right']}
                   brushDirection="horizontal"
                   initialBrushPosition={{start: {x: brushScale(min.date)}, end: {x: brushScale(max.date)}}}
                   onChange={(domain) => {if (domain) setRange([domain.x0, domain.x1]);}}
                   onClick={() => setRange([min.date, max.date])}
                   selectedBoxStyle={{fill: 'url(#pattern)', stroke: fg}}/>
        </Group>) : (<>
            {fit && fit.m && fit.b ?
                (<>
                    <RectClipPath id='regression' x={margin.left} width={brushWidth} y={margin.top}
                                  height={height - margin.top - margin.bottom}/>
                    <Group clipPath='url(#regression)'>
                        <Line stroke={fg} from={{x: 0, y: fit.b}} to={{x: width, y: fit.m * width + fit.b}}/>
                    </Group>
                </>) : null}
            <AxisLeft scale={speedScale} left={margin.left} stroke={fg}
                      tickStroke={fg} tickLabelProps={tlp('end', '0.25em')}/>
            <text x={0} y={0} transform={`translate(${margin.left+15},${margin.top})\nrotate(-90)`} fontSize={fs}
                  textAnchor='end' fill={fg}>Speed / km/h</text>
            <AxisBottom scale={dateScale} top={height-margin.bottom} stroke={fg}
                        tickStroke={fg} tickLabelProps={tlp('middle')}
                        labelProps={{fill: fg, fontSize: fs, textAnchor: 'middle'}}/>
        </>)}
    </svg>);
}


function BrushScatter(props) {
    const {width, sectors, sector1, sector2} = props;
    const [range, setRange] = useState([null, null]);
    return (<>
        <Scatter height={300} width={width}
                 sectors={sectors} sector1={sector1} sector2={sector2}
                 start={range[0]} finish={range[1]}/>
        <Scatter height={50} width={width}
                 sectors={sectors} sector1={sector1} sector2={sector2}
                 setRange={setRange} brush={true} margin={{top: 10, bottom: 0, left: 40, right: 40}}/>
    </>);
}


export default function AutoScaleScatter(props) {
    const {sectors, sector1, sector2} = props;
    return (<ColumnCard>
        <Grid item xs={12}>
            <ParentSize>
                {({ width: visWidth, height: visHeight }) =>
                    <BrushScatter width={visWidth ? visWidth : 500}
                                  sectors={sectors} sector1={sector1} sector2={sector2}/>}
            </ParentSize>
        </Grid>
        <Grid item xs={12}>
            <Text>
                <p>The trend line is fitted to the data in the main display; drag the lower brush area to change.
                    Only activity groups that match the selected sectors are used.</p>
            </Text>
        </Grid>
    </ColumnCard>);
}


