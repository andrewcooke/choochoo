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
import {ColumnList, LinkButton, Text} from "../../utils";


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
    const classes = useStyles();
    console.log(json);

    if (!Array.isArray(json)) return <div/>; // undefined initial data
    const ids = addIds(json);

    // drop outer date label since we already have that in the page
    return (<ColumnList>
        {json.slice(1).map(row => <TopLevel writer={writer} json={row} history={history} key={row.id}/>)}
    </ColumnList>);
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
                children.push(<OuterGrid writer={writer} json={row} level={level} history={history} key={row.id}/>);
            }
        } else {
            children.push(<InnerField writer={writer} json={row} key={row.id}/>);
        }
    });
    return children;
}


function TopLevel(props) {

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


function OuterGrid(props) {

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


function InnerField(props) {

    const {writer, json} = props;

    if (json.type === 'edit') {
        return <EditField key={json.id} writer={writer} json={json}/>
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
            return <Text>Unsupported link: {json}</Text>
        }
    } else {
        return (<Grid item xs={4}>
            <Typography variant='body1'>{json.label}={json.value}</Typography>
        </Grid>);
    }
}


function addIds(json) {

    /* react docs say keys only need to be unique amongst siblings.
       if that's literally true then this is overkill. */

    function add(base) {
        return (json, index) => {
            const id = (base === undefined) ? `${index}` : `${base},${index}`;
            json.id = id;
            if (Array.isArray(json)) json.map(add(id));
        }
    }

    add()(json, 0);

    let ids = [];

    function list(json) {
        ids.push(json.id);
        if (Array.isArray(json)) json.forEach(list);
    }

    list(json);

    return ids
}
