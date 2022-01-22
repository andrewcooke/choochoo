import React, {useEffect, useState} from 'react';
import {Layout} from "../../elements";
import {Loading} from "../../../common/elements";
import {useQuery} from "../../../common/functions";
import {handleJson} from "../../functions";
import {Brush, Circle, Group, ParentSize, PatternLines} from "@visx/shape";
import {AxisBottom, AxisLeft} from "@visx/axis";
import {scaleLinear, scaleTime} from "d3-scale";
import {useTheme} from "@material-ui/core";
import {parse} from 'date-fns';
import {FMT_DAY_TIME} from "../../../constants";
import {csrfFetch} from "../../functions";


function StatisticsPlot(props) {

    const {
        height, width, data, start = null, finish = null, brush = false, setRange=null,
        margin = {top: 10, bottom: 20, left: 40, right: 40}
    } = props;

    const min = {y: Math.min(...data.map(s => s.value)), x: Math.min(...data.map(s => s.date))};
    const max = {y: Math.max(...data.map(s => s.value)), x: Math.max(...data.map(s => s.date))};
    const yScale = scaleLinear([min.y, max.y], [height - margin.bottom, margin.top]);
    const xScale = scaleTime([start ? start : min.x, finish ? finish : max.x],
        [margin.left, width - margin.right]);

    // brush doesn't handle margins correctly, so we do it ourselves (see Group)
    const brushWidth = width - margin.left - margin.right;
    const brushScale = scaleTime([start ? start : min.x, finish ? finish : max.x],
        [0, brushWidth]);

    const theme = useTheme();
    const fg = theme.palette.text.secondary;
    const fs = 10;
    function tlp(anchor, dy=0) {
        return () => ({fill: fg, fontSize: fs, textAnchor: anchor, dy: dy});
    }
    function fill(s) {
        return fg;
    }

    return (<svg width='100%' height={height}>
        {data.map(s => <Circle fill={fill(s)} cx={xScale(s.date)} cy={yScale(s.value)} r={3}/>)}
        {brush ? (<Group left={margin.left}>
            <PatternLines id='pattern' height={8} width={8} stroke={fg} strokeWidth={1}
                          orientation={['diagonal']}/>
            <Brush xScale={brushScale} yScale={yScale} width={brushWidth} height={height}
                   margin={margin} handleSize={8} resizeTriggerAreas={['left', 'right']}
                   brushDirection="horizontal"
                   initialBrushPosition={{start: {x: brushScale(min.x)}, end: {x: brushScale(max.x)}}}
                   onChange={(domain) => {
                       if (domain) setRange([domain.x0, domain.x1]);
                   }}
                   onClick={() => setRange([min.x, max.x])}
                   selectedBoxStyle={{fill: 'url(#pattern)', stroke: fg}}/>
        </Group>) : (<>
            <AxisLeft scale={yScale} left={margin.left} stroke={fg}
                      tickStroke={fg} tickLabelProps={tlp('end', '0.25em')}/>
            <text x={0} y={0} transform={`translate(${margin.left + 15},${margin.top})\nrotate(-90)`} fontSize={fs}
                  textAnchor='end' fill={fg}>Speed / km/h
            </text>
            <AxisBottom scale={xScale} top={height - margin.bottom} stroke={fg}
                        tickStroke={fg} tickLabelProps={tlp('middle')}
                        labelProps={{fill: fg, fontSize: fs, textAnchor: 'middle'}}/>
        </>)}
    </svg>);
}


function BrushStatisticsPlot(props) {
    const {width, data} = props;
    const [range, setRange] = useState([null, null]);
    return (<>
        <StatisticsPlot height={Math.max(300, width * 0.6)} width={width} data={data}
                        start={range[0]} finish={range[1]}/>
        <StatisticsPlot height={50} width={width} data={data}
                        setRange={setRange} brush={true}
                        margin={{top: 10, bottom: 0, left: 40, right: 40}}/>
    </>);
}


function AutoScaleStatisticsPlot(props) {
    const {data} = props;
    return (<ParentSize>
        {({width: visWidth, height: visHeight}) =>
            <BrushStatisticsPlot width={visWidth ? visWidth : 500} data={data}/>}
    </ParentSize>);
}


export default function Statistics(props) {

    const {match, history} = props;
    const {name} = match.params;
    const [data, setData] = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;
    const query = useQuery();
    const owner = query.get("owner");

    function setJson(json) {
        setData(fixStatistics(json));
    }

    function fixStatistics(json) {
        if (json !== null) {
            json = json.map(fixDatum);
        }
        return json;
    }

    function fixDatum(row, i) {
        row.date = parse(row.date, FMT_DAY_TIME, new Date());
        return row;
    }

    useEffect(() => {
        let url = '/api/statistics/by-date/' + name;
        if (owner) url += '?owner=' + owner;
        csrfFetch(url).then(handleJson(history, setJson, setError));
    }, [name, owner]);

    const content = data ? <AutoScaleStatisticsPlot data={data}/> : <Loading/>;

    return <Layout title='Statistics' content={content} errorState={errorState}/>;
}
