import React from 'react';
import {Grid, Typography} from "@material-ui/core";
import {JupyterGroupActivities, ShrimpField, SummaryField} from "./index";
import {makeStyles} from "@material-ui/core/styles";
import {Break, ColumnCard, ColumnList, LinkButton, Loading, SearchResults, Text} from "../../../elements";
import {addMonths, addYears, format} from 'date-fns';
import {FMT_DAY} from "../../../../constants";


const useStyles = makeStyles(theme => ({
    grid: {
        justifyContent: 'flex-start',
        alignItems: 'baseline',
    },
    right: {
        textAlign: 'right',
    },
    title: {
        background: theme.palette.secondary.dark,
        paddingBottom: '0px',
    },
}));


function childrenFromRest(head, rest, level, history) {
    let children = [];
    rest.forEach((row, i) => {
        if (Array.isArray(row)) {
            if (head === 'shrimp') {
                children.push(<ShrimpField json={row} key={i}/>);
            } else {
                children.push(<Break key={i}/>);
                children.push(<Header json={row} level={level} history={history} key={i+0.5}/>);
            }
        } else {
            children.push(<Field json={row} key={i}/>);
        }
    });
    return children;
}


function Title(props) {

    const {header} = props;
    const classes = useStyles();

    return <ColumnCard className={classes.title}>
        <Grid item xs={12} className={classes.right}><Typography variant='h2' component='span'>{header}</Typography></Grid>
    </ColumnCard>
}


function TopLevelPaper(props) {
    const {json, history} = props;
    const [head, ...rest] = json;
    if (head.tag === 'activities') {
        // splice activity groups into top level
        return rest.map((row, i) => <TopLevelPaper json={row} history={history} key={i}/>);
    } else if (head.tag === 'activity-group') {
        return (<>
           <Title header={head.value}/>
           {rest.map((row, i) => <TopLevelPaper json={row} history={history} key={i}/>)}
        </>)
    } else {
        const children = childrenFromRest(head.tag, rest, 3, history);
        return (<ColumnCard header={head.value}>{children}</ColumnCard>);
    }
}


function Header(props) {

    const {json, level, history} = props;
    const [head, ...rest] = json;
    const classes = useStyles();

    const children = childrenFromRest(head.tag, rest, level + 1, history);
    return (<>
        <Grid item xs={4} className={classes.grid}>
            <Typography variant={'h' + level}>{head.value}</Typography>
        </Grid>
        {children}
    </>);
}


function Field(props) {

    const {json} = props;

    if (json.type === 'value') {
        return <SummaryField json={json}/>
    } else if (json.type === 'link') {
        if (json.tag === 'health') {
            return (<Grid item xs={4}>
                <LinkButton href='api/jupyter/health'><Text>{json.value}</Text></LinkButton>
            </Grid>);
        } else if (json.tag === 'group-activities') {
            return <JupyterGroupActivities json={json}/>
        } else {
            return (<Grid item xs={4}><Text>Unsupported link: {JSON.stringify(json)}</Text></Grid>);
        }
    } else {
        return (<Grid item xs={4}><Text>Unsupported type: {JSON.stringify(json)}</Text></Grid>);
    }
}


export default function Schedule(props) {

    const {json, history, start, ymdSelected} = props;

    let finish;
    if (ymdSelected === 0) {
        finish = addYears(start, 1);
    } else {
        finish = addMonths(start, 1);
    }
    const query = `start >= ${format(start, FMT_DAY)} and start < ${format(finish, FMT_DAY)}`;

    if (json === null) {
        return <Loading/>;  // undefined initial data
    } else {
        // drop outer date label since we already have that in the page
        return (<ColumnList>
            <SearchResults query={query}/>
            {json.slice(1).map((row, i) => <TopLevelPaper json={row} history={history} key={i}/>)}
        </ColumnList>);
    }
}
