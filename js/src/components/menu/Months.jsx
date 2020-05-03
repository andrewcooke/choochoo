import React from "react";
import {Loading} from "../elements";
import {Button, Grid} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";
import {sprintf} from "sprintf-js";
import {range} from "../functions";


const useStyles = makeStyles(theme => ({
    button: {
        padding: '0px',
        minWidth: '25px',
    },
}));


export default function Months(props) {

    const {year, active, width=3, onChange} = props;
    const classes = useStyles();
    const names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    if (!Array.isArray(active)) {
        return <Loading/>;  // undefined initial data
    } else {
        return (<Grid container>
            {range(0, 12).map(
                (month, i) => {
                    const date = sprintf('%s-%02d', year, month+1);
                    const disabled = !active.includes(date);
                    return <Grid item xs={width} key={i}>
                        <Button className={classes.button} onClick={() => onChange(date)} disabled={disabled}>
                            {names[month]}
                        </Button>
                    </Grid>;
                })}
        </Grid>);
    }
}
