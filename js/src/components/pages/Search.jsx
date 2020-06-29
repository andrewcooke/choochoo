import React, {useEffect, useState} from 'react';
import {SearchResults} from "../elements";
import {ColumnCard, ColumnList, Loading, Text} from "../../common/elements";
import {Button, Checkbox, Collapse, FormControlLabel, Grid, IconButton, TextField, Typography} from "@material-ui/core";
import {makeStyles} from "@material-ui/styles";
import {ExpandLess, ExpandMore} from "@material-ui/icons";
import {Layout} from "../elements";


const useStyles = makeStyles(theme => ({
    button: {
        width: '100%',
    },
}));


function SearchTerm(props) {

    const {term} = props;

    return (<>
        <Grid item xs={10}>
            <Typography variant='h3'>{term.name}</Typography>
        </Grid>
        <Grid item xs={2}>
            <Text>{term.units}</Text>
        </Grid>
        <Grid item xs={12}>
            <Text>{term.description}</Text>
        </Grid>
    </>);
}


function SearchTerms(props) {

    const {termsState} = props;
    const [terms, setTerms] = termsState;

    useEffect(() => {
        fetch('/api/search/activity-terms').
            then(response => response.json()).
            then(response => setTerms(response))
    }, [1]);

    return (<ColumnCard header='Available Statistic Names'>
        {terms === null ? <Loading/> : terms.map((term, i) => <SearchTerm term={term} key={i}/>)}
    </ColumnCard>);
}


function AdvancedHelp(props) {

    const {expandedState} = props;
    const [expanded, setExpanded] = expandedState;

    return (<>
        <Grid item xs={12}><Text>
            <p>Find activities that match the search expression.
                <IconButton onClick={() => setExpanded(!expanded)}>
                    {expanded ? <ExpandLess/> : <ExpandMore/>}
                </IconButton>
            </p>
            <Collapse in={expanded} timeout="auto" unmountOnExit>
                <p>A search expression compares statistic names with values. For example</p>
                <pre>active-distance &gt; 10</pre>
                <p>would search for activities where the Active Distance statistic was larger than 10km.</p>
                <p>Expressions can be combined using <code>and</code> and <code>or</code>:</p>
                <pre>active-distance &gt; 10 and active-time &lt; 3600</pre>
                <p>(time is measured in seconds so 3600 is an hour).</p>
            </Collapse>
        </Text></Grid>
    </>)
}


function BasicHelp(props) {
    return (<Grid item xs={12}>
        <Text>
            <p>Find activities that contain the given words in the name or description.</p>
        </Text>
    </Grid>)
}


function SearchBox(props) {

    const {advancedState, queryState} = props;
    const [advanced, setAdvanced] = advancedState;
    const [query, setQuery] = queryState;
    const [localQuery, setLocalQuery] = useState(query);
    const expandedState = useState(true);
    const classes = useStyles();

    return (<ColumnCard>
        <Grid item xs={12}>
            <TextField label='Query' value={localQuery}
                       onChange={event => setLocalQuery(event.target.value)}
                       onKeyPress={event => {
                           if (event.key === 'Enter') setQuery(localQuery);
                       }}
                       fullWidth/>
        </Grid>
        <Grid item xs={6}>
            <FormControlLabel
                control={<Checkbox checked={advanced} onChange={event => setAdvanced(event.target.checked)}/>}
                label='Advanced'/>
        </Grid>
        <Grid item xs={2}/>
        <Grid item xs={4}>
            <Button variant='contained' className={classes.button}
                    onClick={() => setQuery(localQuery)}>Search</Button>
        </Grid>
        {advanced ? <AdvancedHelp expandedState={expandedState}/> : <BasicHelp/>}
    </ColumnCard>);
}


export default function Search(props) {

    const queryState = useState('');
    const [query, setQuery] = queryState;
    const advancedState = useState(false);
    const [advanced, setAdvanced] = advancedState;
    const termsState = useState(null);

    const content = (<ColumnList>
        <SearchBox advancedState={advancedState} queryState={queryState}/>
        <SearchResults query={query} advanced={advanced}/>
        {advanced ? <SearchTerms termsState={termsState}/> : null}
    </ColumnList>);

    return (
        <Layout title='Search'
                content={content}/>
    );
}
