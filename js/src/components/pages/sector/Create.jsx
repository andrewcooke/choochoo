import React, {useEffect, useState} from 'react';
import {ConfirmedWriteButton, Layout, Map, Route} from "../../elements";
import {ColumnCard, ColumnList, Loading, Text} from "../../../common/elements";
import {handleJson} from "../../functions";
import {Grid, Slider, TextField} from "@material-ui/core";
import log from "loglevel";
import {makeStyles} from "@material-ui/styles";


const useStyles = makeStyles(theme => ({
    button: {
        width: '100%',
    },
}));


function Columns(props) {

    const {activity, data, history} = props;

    if (data === null) {
        return (<>
            <Loading/>
        </>);
    } else {
        return <CreateMap activity={activity} data={data} history={history}/>;
    }
}


function CreateMap(props) {

    const {activity, data, history} = props;
    const [ends, setEnds] = useState([0, 1]);
    const [name, setName] = useState('')
    const full_latlon = data['latlon'];
    const n = full_latlon.length - 1;
    const [start, finish] = ends;
    const istart = Math.floor(n * start);
    const ifinish = Math.ceil(n * finish);
    const latlon = full_latlon.slice(istart, ifinish);

    log.debug(`activity ${activity}`);

    function handleSlider(event, ends) {
        const [start, finish] = ends;
        if (start === finish) {
            setEnds([start > 0 ? start - 0.001 : start, finish < 1 ? finish + 0.001 : finish]);
        } else {
            setEnds([start, finish]);
        }
    }

    function handleEdit(event) {
        setName(event.target.value);
    }

    function redirect(data) {
        log.debug(data);
    }

    return (<>
        <ColumnList>
            <ColumnCard>
                <Grid item xs={12}><Text>
                    <p>Sectors are recognised across activities and let you compare performance over
                        time.</p>
                    <p>Adjust the sliders to select the start and end points and enter a suitable
                        name.</p>
                </Text></Grid>
            </ColumnCard>
            <ColumnCard>
                <Grid item xs={12}>
                    <Map latlon={latlon} routes={<Route latlon={latlon}/>}/>
                    <Slider value={ends} onChange={handleSlider} min={0} max={1} step={0.001}
                            getAriaLabel={(index) => (index === 0 ? 'Start' : 'Finish')}/>
                </Grid>
                <Grid item xs={9}>
                    <TextField label='Name' value={name} onChange={handleEdit}
                               fullWidth multiline={false} variant="filled"/>
                </Grid>
                <ConfirmedWriteButton xs={3} label='Create' variant='contained' method='post'
                                      href={`/api/route/add-sector/${activity}`} setData={redirect}
                                      json={{start: istart, finish: ifinish, name: name}}>
                    Creating the sector will take time as statistics are calculated.
                </ConfirmedWriteButton>
            </ColumnCard>
        </ColumnList>
    </>);
}


export default function Create(props) {

    const {match, history} = props;
    const {id} = match.params;
    const [data, setData] = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;

    useEffect(() => {
        fetch('/api/route/activity/' + id)
            .then(handleJson(history, setData, setError));
    }, [id]);

    log.debug(`id ${id}`)

    return (
        <Layout title='New Sector'
                content={<Columns data={data} activity={id} history={history}/>}
                errorState={errorState}/>
    );
}
