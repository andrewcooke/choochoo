import React, {useEffect, useState} from 'react';
import {Grid, Typography} from "@material-ui/core";
import {
    ClimbField,
    EditField,
    FloatField,
    HRZoneField,
    IntegerField,
    JupyterActivity,
    NearbyMenu,
    ScoreField,
    ShrimpField,
    TextField,
    ValueField
} from "./elements";
import {makeStyles} from "@material-ui/core/styles";
import {ColumnCard, ColumnList, Layout, LinkButton, Loading, Text, Thumbnail} from "../../elements";
import {handleJson} from "../../functions";
import {parse} from "date-fns";
import {FMT_DAY} from "../../../constants";


const useStyles = makeStyles(theme => ({
    grid: {
        justifyContent: 'flex-start',
        alignItems: 'baseline',
    },
    center: {
        textAlign: 'center',
    },
    right: {
        textAlign: 'right',
    },
     img: {
        marginBottom: '-5px',
    },
    title: {
        background: theme.palette.secondary.dark,
        paddingBottom: '0px',
    },
}));


function childrenFromRest(head, rest, writer, level, history) {

    const classes = useStyles();
    let children = [];

    rest.forEach((row, i) => {
        if (Array.isArray(row)) {
            if (head.tag === 'shrimp') {
                children.push(<ShrimpField json={row} key={i}/>);
            } else if (head.tag === 'hr-zones-time') {
                children.push(<HRZoneField json={row} key={i}/>);
            } else {
                children.push(<Header writer={writer} json={row} level={level} history={history} key={i}/>);
            }
        } else {
            if (head.tag === 'activity' && i === 0 && row.label === 'Name' && row.type === 'edit') {
                children.push(<EditField writer={writer} json={row} xs={10} key={i}/>);
                children.push(<Grid item xs={2} key={i+0.5}>
                    <Thumbnail activity_id={head.db} className={classes.img}/>
                </Grid>);
            } else {
                children.push(<Field writer={writer} json={row} key={i}/>);
            }
        }
    });
    return children;
}


function Title(props) {

    const {header} = props;
    const classes = useStyles();
    const match = header.match(/^(.*\))\s*(.*)$/)

    return <ColumnCard className={classes.title}>
        <Grid item xs={10}><Typography variant='h2' component='span'>{match[1]}</Typography></Grid>
        <Grid item xs={2} className={classes.right}><Typography variant='h2' component='span'>{match[2]}</Typography></Grid>
    </ColumnCard>
}


function Header(props) {

    const {writer, json, level, history} = props;
    const [head, ...rest] = json;
    const classes = useStyles();

    const children = head.tag === 'jupyter-activity' ?
        <JupyterActivity json={rest}/> :
        childrenFromRest(head, rest, writer, level + 1, history);

    if (head.tag === 'climb') {
        return (<ClimbField json={json}/>);
    } else if (head.tag === 'nearby-links') {
        return (<NearbyMenu json={json} history={history}/>);
    } else {
        return (<>
            <Grid item xs={12} className={classes.grid}>
                <Typography variant={'h' + level}>{head.value}</Typography>
            </Grid>
            {children}
        </>);
    }
}


function Field(props) {

    const {writer, json} = props;
    const classes = useStyles();

    if (json.type === 'edit') {
        return <EditField writer={writer} json={json}/>
    } else if (json.type === 'integer') {
        return <IntegerField writer={writer} json={json}/>
    } else if (json.type === 'float') {
        return <FloatField writer={writer} json={json}/>
    } else if (json.type === 'score') {
        return <ScoreField writer={writer} json={json}/>
    } else if (json.type === 'text') {
        return <TextField json={json}/>
    } else if (json.type === 'value') {
        return <ValueField json={json}/>
    } else if (json.type === 'link') {
        if (json.tag === 'health') {
            return (<Grid item xs={4} className={classes.center}>
                <LinkButton href='api/jupyter/health'><Text>{json.value}</Text></LinkButton>
            </Grid>);
        } else {
            return (<Grid item xs={4}>
                <Text>Unsupported link: {JSON.stringify(json)}</Text>
            </Grid>);
        }
    } else {
        return (<Grid item xs={4}>
            <Text>Unsupported type: {JSON.stringify(json)}</Text>
        </Grid>);
    }
}


function TopLevelPaper(props) {

    const {writer, json, history} = props;
    const [head, ...rest] = json;

    if (['diary', 'activities'].includes(head.tag)) {
        // splice into the top level
        return rest.map((row, i) => <TopLevelPaper writer={writer} json={row} history={history} key={i}/>);
    } else if (head.tag === 'activity-title') {
        return (<>
            <Title header={head.value}/>
            {rest.map((row, i) => <TopLevelPaper writer={writer} json={row} history={history} key={i}/>)}
        </>);
    } else {
        const children = head.tag === 'jupyter-activity' ?
            <JupyterActivity json={rest}/> :
            childrenFromRest(head, rest, writer, 3, history);
        // we drop the title for these
        if (['activity', 'achievements', 'nearbys'].includes(head.tag)) {
            return (<ColumnCard>{children}</ColumnCard>);
        } else {
            return (<ColumnCard header={head.value}>{children}</ColumnCard>);
        }
    }
}


function Content(props) {

    const {writer, json, history} = props;

    if (json === null) {
        return <Loading/>;  // undefined initial data
    } else {
        // drop outer date label since we already have that in the page
        return (<ColumnList>
            {json.slice(1).map((row, i) => <TopLevelPaper writer={writer} json={row} history={history} key={i}/>)}
        </ColumnList>);
    }
}


export default function Day(props) {

    const {match, history, writer} = props;
    const {date} = match.params;
    const datetime = parse(date, FMT_DAY, new Date());
    const [json, setJson] = useState(null);
    const busyState = useState(null);
    const errorState = useState(null);
    const [error, setError] = errorState;
    const [reads, setReads] = useState(0);

    function reload() {
        setReads(reads + 1);
    }

    useEffect(() => {
        setJson(null);
        fetch('/api/diary/' + date)
            .then(handleJson(history, setJson, setError, busyState));
    }, [date, reads]);

    return (
        <Layout title={`Diary: ${date}`}
                content={<Content writer={writer} json={json} history={history}/>}
                reload={reload} busyState={busyState} errorState={errorState}/>
    );
}
