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
    const {header, href, displayWidth=12, children} = props;
    const classes = useStyles();
    return (<ColumnCard header={header}>
        {children}
        <Grid item xs={displayWidth} className={classes.right}>
            <LinkButton href={href}>Display</LinkButton>
        </Grid>
    </ColumnCard>);
}
