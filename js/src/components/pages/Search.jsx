import React, {useEffect, useState} from 'react';
import {ColumnCard, ColumnList, Layout, Loading, Text} from "../elements";
import {Button, Checkbox, Collapse, FormControlLabel, Grid, IconButton, TextField, Typography} from "@material-ui/core";
import {makeStyles} from "@material-ui/styles";
import {ExpandLess, ExpandMore} from "@material-ui/icons";


const useStyles = makeStyles(theme => ({
    right: {
        textAlign: 'right',
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
        {terms === null ? <Loading/> : terms.map(term => <SearchTerm term={term}/>)}
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
                <pre>Active Distance &gt; 10</pre>
                <p>would search for activities where the Active Distance statistic was larger than 10km.</p>
                <p>Expressions can be combined using <code>and</code> and <code>or</code>:</p>
                <pre>Active Distance &gt; 10 and Active Time &lt; 3600</pre>
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


function SearchResult(props) {

    const {result} = props;

    return (<ColumnCard>
        {result}
    </ColumnCard>);
}


function SearchBox(props) {

    const {setResult, advancedState} = props;
    const [advanced, setAdvanced] = advancedState;
    const expandedState = useState(true);
    const [query, setQuery] = useState('');
    const classes = useStyles();

    function onSearch() {
        fetch('/api/search/activity/' + encodeURIComponent(query) + '?advanced=' + advanced).
            then(response => response.json).
            then(setResult(response));
    }

    return (<ColumnCard>
        <Grid item xs={12}>
            <TextField label='Query' value={query} onChange={event => setQuery(event.target.value)} fullWidth/>
        </Grid>
        <Grid item xs={6}>
            <FormControlLabel
                control={<Checkbox checked={advanced} onChange={event => setAdvanced(event.target.checked)}/>}
                label='Advanced'/>
        </Grid>
        <Grid item xs={6} className={classes.right}>
            <Button variant='contained' onClick={onSearch}>Search</Button>
        </Grid>
        {advanced ? <AdvancedHelp expandedState={expandedState}/> : <BasicHelp/>}
    </ColumnCard>);
}


export default function Search(props) {

    const [result, setResult] = useState(null);
    const termsState = useState(null);
    const advancedState = useState(false);
    const [advanced, setAdvanced] = advancedState;

    const content = (<ColumnList>
        <SearchBox setResult={setResult} advancedState={advancedState}/>
        {result !== null ? <SearchResult result={result}/> : null}
        {advanced ? <SearchTerms termsState={termsState}/> : null}
    </ColumnList>);

    return (
        <Layout title='Search'
                content={content}/>
    );
}
