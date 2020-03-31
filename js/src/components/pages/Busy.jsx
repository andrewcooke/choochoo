import React, {useEffect, useState} from 'react';
import {Grid} from "@material-ui/core";
import {ColumnCard, ColumnList, Layout, Loading, MainMenu, P, PercentBar} from "../elements";


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
                <PercentBar percent={json.percent} fraction={1}/>
            </Grid></ColumnCard>
        </ColumnList>);
        if (json.percent !== 100) {
            setTimeout(reload, 1000);
        }
    } else {
        content = <Loading/>
    }

    const navigation = <MainMenu/>;

    return (<Layout navigation={navigation} content={content} match={match} title='Busy'/>);
}
