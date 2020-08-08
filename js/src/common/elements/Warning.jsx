import {ColumnCard, P} from "./index";
import {Grid, Link} from "@material-ui/core";
import React from "react";
import {makeStyles} from "@material-ui/styles";


const useStyles = makeStyles(theme => ({
    warning: {
        background: theme.palette.secondary.dark,
        paddingBottom: '0px',
    },
}));


export default function Warning(props) {

    const {title, warning, extra} = props;
    const classes = useStyles();

    return (<ColumnCard header={title} className={classes.warning}><Grid item xs={12}>
        <P>{warning}</P>
        {extra}
    </Grid></ColumnCard>);
}
