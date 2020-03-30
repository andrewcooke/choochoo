import React, {useEffect, useState} from 'react';
import {Grid} from "@material-ui/core";
import {ColumnCard, ColumnList, Layout, Loading, MainMenu, P} from "../elements";


export default function Busy(props) {

    const {match, history} = props;
    const [json, setJson] = useState(null);
    const [reloads, setReloads] = useState(0);

    function reload() {
        setReloads(reloads + 1);
    }

    useEffect(() => {
        fetch('/api/busy')
            .then(response => response.json())
            .then(json => setJson(json));
    }, [reloads]);

    let content;
    if (json) {
        content = (<ColumnList>
            <ColumnCard><Grid item xs={12}>
                <P>{json.reason}</P>
                <P>{json.percentage}</P>
            </Grid></ColumnCard>
        </ColumnList>);
        if (json.percentage !== 100) {
            setTimeout(reload, 100);
        }
    } else {
        content = <Loading/>
    }

    const navigation = <MainMenu/>;

    return (<Layout navigation={navigation} content={content} match={match} title='Busy'/>);
}
