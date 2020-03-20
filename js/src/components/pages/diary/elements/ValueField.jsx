import React from 'react';
import {Grid, InputLabel} from "@material-ui/core";
import {FormatValueUnits} from "../../../elements";
import Measures from "./Measures";
import {makeStyles} from "@material-ui/core/styles";


const useStyles = makeStyles(theme => ({
    right: {
        textAlign: 'right',
    },
    center: {
        textAlign: 'center',
    },
    left: {
        textAlign: 'left',
    },
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
        <InputLabel shrink>{json.label}</InputLabel>
        <FormatValueUnits value={json.value} units={json.units} tag={json.tag}/>
    </>);
}


function SimpleValueField(props) {
    return (<Grid item xs={6}>
        <CommonValueField {...props}/>
    </Grid>);
}


function MeasuredValueField(props) {

    const {json} = props;
    const classes = useStyles();

    return (<>
        <Grid item xs={4} className={classes.left}>
            <CommonValueField {...props}/>
        </Grid>
        <Grid item xs={8} className={classes.right}>
            <Measures measures={json.measures}/>
        </Grid>
    </>);
}
