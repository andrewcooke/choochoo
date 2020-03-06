import React from "react";
import {makeStyles} from "@material-ui/core/styles";
import {sprintf} from 'sprintf-js'


const useStyles = makeStyles(theme => ({
    svg: {
        overflow: 'visible',
        marginRight: theme.spacing(1),
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



export default function PercentBar(props) {

    const {percent, label, width=60, height=19, fraction=null} = props;
    const classes = useStyles();
    const text = label ? label : percent.toFixed(0) + ' %';
    const finalWidth = fraction === null ? sprintf('%d', width + 1) : sprintf('%d%%', 100 * fraction);

    return (<svg width={finalWidth} height={0} className={classes.svg}>
        <g transform='translate(0.5, -15.5)'>
            <rect width='100%' height={height} className={classes.barBackground}/>
            <rect width={sprintf('%d%%', percent)} height={height} className={classes.barForeground}/>
            <text x={3} y={height - 6} className={classes.barText}>{text}</text>
            {/* <line x1={x} x2={x} y1={0} y2={height} className={classes.barLine}/> */}
        </g>
    </svg>);
}

