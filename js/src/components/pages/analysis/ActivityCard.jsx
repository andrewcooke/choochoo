import React from 'react';
import {ColumnCard, LinkButton} from "../../elements";
import {Grid} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";


const useStyles = makeStyles(theme => ({
    right: {
        textAlign: 'right',
    },
}));


export default function ActivityCard(props) {
    const {header, href, pad, children} = props;
    const classes = useStyles();
    return (<ColumnCard header={header}>
        {children}
        {pad === undefined ?  null : <Grid item xs={pad}/>}
        <Grid item xs={4} className={classes.right}>
            <LinkButton href={href}>Display</LinkButton>
        </Grid>
    </ColumnCard>);
}
