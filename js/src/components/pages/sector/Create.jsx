import React, {useEffect, useState} from 'react';
import {ConfirmedWriteButton, Layout, OSMap, Route} from "../../elements";
import {ColumnCard, ColumnList, Loading, Text} from "../../../common/elements";
import {last} from "../../../common/functions";
import {handleJson} from "../../functions";
import {Grid, Slider, TextField, useTheme} from "@material-ui/core";
import log from "loglevel";
import {makeStyles} from "@material-ui/styles";
import {scaleLinear} from "d3-scale";
import {Area, AxisBottom, AxisLeft, LinePath, ParentSize} from "@visx/visx";


const useStyles = makeStyles(theme => ({
    button: {
        width: '100%',
    },
}));


function Elevation(props) {
    const {elevation, start, finish, width, height,
        margin={top: 10, bottom: 40, left: 40, right: 40}} = props;

    const distanceScale = scaleLinear(
        [0, last(elevation)[0]],
        [margin.left, width-margin.right]);
    const elevationScale = scaleLinear(
        [Math.min(...elevation.map(([d, e]) => e)), Math.max(...elevation.map(([d, e]) => e))],
        [height-margin.bottom, margin.top]);

    const theme = useTheme();
    const fg = theme.palette.text.secondary;
    const fs = 10;
    function tlp(anchor, dy=0) {
        return () => ({fill: fg, fontSize: fs, textAnchor: anchor, dy: dy});
    }

    return (<svg width='100%' height={height}>
        <Area data={elevation} fill={fg} opacity={0.05}
              x={elevation => distanceScale(elevation[0])}
              y1={elevation => elevationScale(elevation[1])}
              y0={elevation => height-margin.bottom}/>
        <LinePath data={elevation.slice(start, finish)} stroke={fg} strokeWidth={1} opacity={1}
                  x={elevation => distanceScale(elevation[0])}
                  y={elevation => elevationScale(elevation[1])}/>
        <AxisLeft scale={elevationScale} left={margin.left} stroke={fg}
                  tickStroke={fg} tickLabelProps={tlp('end', '0.25em')}/>
        <text x={0} y={0} transform={`translate(${margin.left+15},${margin.top})\nrotate(-90)`} fontSize={fs}
              textAnchor='end' fill={fg}>Elevation / m</text>
        <AxisBottom scale={distanceScale} top={height-margin.bottom} stroke={fg}
                    tickStroke={fg} tickLabelProps={tlp('middle')}
                    labelProps={{fill: fg, fontSize: fs, textAnchor: 'middle'}} label='Distance / km'/>
    </svg>);
}


function AutoScaleElevation(props) {
    const {elevation, start, finish, height} = props;
    return (<ParentSize>
        {({ width: visWidth, height: visHeight }) =>
            <Elevation width={visWidth ? visWidth : 500}
                       elevation={elevation} start={start} finish={finish} height={height}/>}
    </ParentSize>);
}


function CreateMap(props) {

    const {activity, data, history} = props;
    const [ends, setEnds] = useState([0, 1]);
    const [name, setName] = useState('')
    const full_latlon = data['latlon'];
    const elevation = data['elevation'];
    const n = full_latlon.length - 1;
    const [start, finish] = ends;
    const istart = Math.floor(n * start);
    const ifinish = Math.ceil(n * finish);
    const latlon = full_latlon.slice(istart, ifinish);

    log.debug(`activity ${activity}`);

    function handleSlider(event, ends) {
        const [start, finish] = ends;
        if (start === finish) {
            setEnds([start > 0 ? start - 0.001 : start, finish < 1 ? finish + 0.001 : finish]);
        } else {
            setEnds([start, finish]);
        }
    }

    function handleEdit(event) {
        setName(event.target.value);
    }

    function redirect(data) {
        log.debug(data);
    }

    return (<>
        <ColumnList>
            <ColumnCard>
                <Grid item xs={12}><Text>
                    <p>Sectors are recognised across activities and let you compare performance over
                        time.</p>
                    <p>Adjust the sliders to select the start and end points and enter a suitable
                        name.</p>
                </Text></Grid>
            </ColumnCard>
            <ColumnCard>
                <Grid item xs={12}>
                    <AutoScaleElevation elevation={elevation} start={istart} finish={ifinish} height={150}/>
                    <OSMap latlon={latlon} routes={<Route latlon={latlon}/>}/>
                    <Slider value={ends} onChange={handleSlider} min={0} max={1} step={1/1000}
                            getAriaLabel={(index) => (index === 0 ? 'Start' : 'Finish')}/>
                </Grid>
                <Grid item xs={9}>
                    <TextField label='Name' value={name} onChange={handleEdit}
                               fullWidth multiline={false} variant="filled"/>
                </Grid>
                <ConfirmedWriteButton xs={3} label='Create' variant='contained' method='post'
                                      href={`/api/sector`} setData={redirect}
                                      json={{start: istart, finish: ifinish, name: name, activity: activity}}>
                    Creating the sector will take time as statistics are calculated.
                </ConfirmedWriteButton>
            </ColumnCard>
        </ColumnList>
    </>);
}


export default function Create(props) {

    const {match, history} = props;
    const {id} = match.params;
    const [data, setData] = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;

    useEffect(() => {
        fetch('/api/route/latlon/activity/' + id)
            .then(handleJson(history, setData, setError));
    }, [id]);

    log.debug(`id ${id}`)

    const content =  data === null ? <Loading/> :
        <CreateMap activity={id} data={data} history={history}/>;

    return <Layout title='New Sector' content={content} errorState={errorState}/>;
}
