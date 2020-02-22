import React from 'react';
import {Box, Grid, ListItem, Paper, Typography} from "@material-ui/core";
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
import {ColumnList, LinkButton, Loading, setIds, Text} from "../../utils";


const useStyles = makeStyles(theme => ({
    listItem: {
        padding: theme.spacing(1),
    },
    paper: {
        padding: theme.spacing(1),
        margin: theme.spacing(1),
        width: '100%',
    },
    grid: {
        justifyContent: 'flex-start',
        alignItems: 'baseline',
    },
}));


export default function Day(props) {

    const {writer, json, history} = props;
    console.log(json);

    if (!Array.isArray(json)) {
        return <Loading/>;  // undefined initial data
    } else {
        setIds(json);
        // drop outer date label since we already have that in the page
        return (<ColumnList>
            {json.slice(1).map(row => <TopLevelPaper writer={writer} json={row} history={history} key={row.id}/>)}
        </ColumnList>);
    }
}


function childrenFromRest(head, rest, writer, level, history) {
    let children = [];
    rest.forEach((row) => {
        if (Array.isArray(row)) {
            if (head === 'shrimp') {
                children.push(<ShrimpField json={row} key={row.id}/>);
            } else if (head === 'hr-zones-time') {
                children.push(<HRZoneField json={row} key={row.id}/>);
            } else {
                children.push(<IndentedGrid writer={writer} json={row} level={level} history={history} key={row.id}/>);
            }
        } else {
            children.push(<Field writer={writer} json={row} key={row.id}/>);
        }
    });
    return children;
}


function TopLevelPaper(props) {

    const {writer, json, history} = props;
    const [head, ...rest] = json;
    const classes = useStyles();
    const children = childrenFromRest(head.tag, rest, writer, 3, history);

    return (<ListItem className={classes.listItem}>
        <Paper className={classes.paper}>
            <Box mb={1}><Typography variant={'h2'}>{head.value}</Typography></Box>
            <Grid container spacing={1} className={classes.grid}>
                {children}
            </Grid>
        </Paper>
    </ListItem>);
}


function IndentedGrid(props) {

    const {writer, json, level, history} = props;
    const [head, ...rest] = json;
    const classes = useStyles();
    const children = head.tag === 'jupyter-activity' ?
        <JupyterActivity json={rest}/> :
        childrenFromRest(head.tag, rest, writer, level + 1, history);

    if (head.tag === 'climb') {
        return (<ClimbField json={json}/>);
    } else if (head.tag === 'nearby-links') {
        return (<NearbyMenu json={json} history={history}/>);
    } else {
        return (<Grid item container spacing={1} className={classes.grid}>
            <Grid item xs={12} className={classes.grid}>
                <Typography variant={'h' + level}>{head.value}</Typography>
            </Grid>
            <Grid item xs={1} className={classes.grid}/>
            <Grid item container xs={11} spacing={1} justify='space-between' className={classes.grid}>
                {children}
            </Grid>
        </Grid>);
    }
}


function Field(props) {

    const {writer, json} = props;

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
            return <LinkButton href='jupyter/health'><Text>{json.value}</Text></LinkButton>
        } else {
            return (<Grid item xs={4}><Text>Unsupported link: {json}</Text></Grid>);
        }
    } else {
        return (<Grid item xs={4}><Text>Unsupported type: {json}</Text></Grid>);
    }
}
