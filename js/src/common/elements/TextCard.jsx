import React from 'react';
import {Grid} from "@material-ui/core";
import {ColumnCard, Text} from ".";


export default function TextCard(props) {

    const {header, children} = props;

    return (<ColumnCard header={header}><Grid item xs={12}><Text>
        {children}
    </Text></Grid></ColumnCard>);
}
