import React, {useEffect, useState} from 'react';
import {Grid, Link} from "@material-ui/core";
import {ColumnCard, ColumnList, Layout, MainMenu, P, Loading} from "../../elements";
import {handleGet} from "../../functions";


function Columns(props) {

    const {data} = props;

    if (data === null) {
        return <Loading/>;
    } else if (data.configured) {
        return (<ColumnList><ColumnCard><Grid item xs={12}>
            <P>The initial configuration has already been made.</P>
        </Grid></ColumnCard></ColumnList>);
    } else {
        return (<ColumnList><ColumnCard><Grid item xs={12}>
            <P>Hello handsome.</P>
        </Grid></ColumnCard></ColumnList>);
    }
}


export default function Initial(props) {

    const {match, history} = props;
    const [data, setData] = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;

    useEffect(() => {
        fetch('/api/configure/profiles')
            .then(handleGet(history, setData, setError));
    }, [1]);

    return (
        <Layout navigation={<MainMenu configure/>}
                content={<Columns data={data}/>}
                match={match} title='Configure' errorState={errorState}/>
    );
}
