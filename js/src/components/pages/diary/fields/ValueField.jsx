import React from 'react';
import {Grid} from "@material-ui/core";
import {Text} from '../../../utils';
import {makeStyles} from "@material-ui/core/styles";


const useStyles = makeStyles(theme => ({
    svg: {
        overflow: 'visible',
    },
    barBackground: {
        fill: theme.palette.background.default,
        stroke: theme.palette.text.secondary,
    },
    barForeground: {
        fill: theme.palette.text.secondary,
        fillOpacity: 0.2,
        stroke: 'none',
    },
    barLine: {
        stroke: theme.palette.text.secondary,
        strokeWidth: 0.75,
    },
    barText: {
        fontSize: 11,
        fill: theme.palette.text.secondary,
    }
}));


export default function ValueField(props) {
    const {json} = props;
    if (json.measures) {
        return <MeasuredValueField {...props}/>
    } else {
        return <SimpleValueField {...props}/>
    }
}


function CommonValueField(props) {
    const {json} = props;
    return (<>
        <Text secondary>{json.label}: </Text>
        <Text>{json.value}</Text>
        {json.units && <Text secondary> {json.units}</Text>}
    </>);
}


function SimpleValueField(props) {
    return (<Grid item xs={4}>
        <p>
            <CommonValueField {...props}/>
        </p>
    </Grid>);
}


function MeasuredValueField(props) {
    const {json} = props;
    return (<>
        <Grid item xs={5}>
            <CommonValueField {...props}/>
        </Grid>
        <Grid item xs={7}>
            <Schedules schedules={json.measures.schedules}/>
        </Grid>
    </>);
}


function Schedules(props) {

    const {schedules} = props;

    return (Object.entries(schedules).map(entry => {
        const [period, [percent, rank]] = entry;
        const [width, height] = [50, 19];
        const x = width * percent / 100;
        return (<>
            <PercentBar percent={percent}/>
            <Text secondary> {rank}/{period} &nbsp;</Text>
        </>)
    }));
}


function PercentBar(props) {

    const {percent} = props;
    const classes = useStyles();
    const [width, height] = [50, 19];
    const x = width * percent / 100;

    return (<svg width={width + 1} height={0} className={classes.svg}>
        <g transform='translate(0.5, -15.5)'>
            <rect width={width} height={height} className={classes.barBackground}/>
            <rect width={x} height={height} className={classes.barForeground}/>
            <text x={3} y={height - 6} className={classes.barText}>{percent.toFixed(0)} %</text>
            {/* <line x1={x} x2={x} y1={0} y2={height} className={classes.barLine}/> */}
        </g>
    </svg>);
}

