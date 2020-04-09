import React, {useEffect, useState} from 'react';
import {ColumnCard, ColumnList, ConfirmedWriteButton, Layout, Loading, MainMenu, P} from "../../elements";
import {handleJson} from "../../functions";
import {Grid, TextField, Paper} from "@material-ui/core";
import {FMT_DAY_TIME} from "../../../constants";
import format from 'date-fns/format';
import {makeStyles} from "@material-ui/core/styles";
import {DateTimePicker} from "@material-ui/pickers";


const useStyles = makeStyles(theme => ({
    paper: {
        padding: theme.spacing(1),
    },
}));


function isString(value) {
    return value instanceof String || typeof(value) === typeof('string')
}


function isNumber(value) {
    return ! isNaN(value);
}


function isComposite(value) {
    return ! (isString(value) || isNumber(value));
}


const EDIT_WIDTH = 10;
const SAVE_WIDTH = 2;


function Field(props) {
    const {label, value, setValue} = props;
    return (<TextField label={label} value={value} onChange={event => setValue(event.target.value)} fullWidth />);
}


function Value(props) {

    const {constantState, index=0} = props;
    const [constant, setConstant] = constantState;
    const value = constant.values[index].value;

    if (constant.composite) {
        return Object.keys(value).map(name => (
            <Field label={name} value={value[name]}
                   setValue={value => {
                       const copy = {...constant};
                       copy.values[index].value[name] = value;
                       setConstant(copy);
                   }}/>));
    } else {
        return (<Field label='Value' value={value}
                      setValue={value => {
                          const copy = {...constant};
                          copy.values[index].value = value;
                          setConstant(copy);
                      }}/>);
    }
}


function DatedValue(props) {

    const {constantState, index = 0} = props;
    const [constant, setConstant] = constantState;
    const classes = useStyles();

    return (<Grid item xs={EDIT_WIDTH}><Paper variant='outlined' className={classes.paper}>
        <Value constantState={constantState} index={index}/>
        <DateTimePicker value={constant.values[index].time}
                        onChange={time => {
                            const copy = {...constant};
                            copy.values[index].time = time;
                            setConstant(copy);
                        }}/>
    </Paper></Grid>);
}


function UndatedValue(props) {

    const {constantState, index=0} = props;
    const classes = useStyles();

    return (<Grid item xs={EDIT_WIDTH}><Paper variant='outlined' className={classes.paper}>
        <Value constantState={constantState} index={index}/>
    </Paper></Grid>);
}


function emptyCopy(constant) {
    const extra = {...constant};
    console.log('extra');
    if (constant.values.length > 0) {
        if (constant.composite) {
            console.log('composite', extra);
            extra.values = [{value: {...constant.values[0].value}, time: constant.values[0].time}];
            Object.keys(extra.values[0].value).forEach(
                name => extra.values[0].value[name] = isString(extra.values[0].value[name]) ? '' : 0);
        } else {
            console.log('single', extra);
            extra.values = [{value: '', time: format(new Date(), FMT_DAY_TIME)}];
        }
    } else {
        console.log('empty', extra);
        extra.values = [{value: ''}];
    }
    extra.values[0].time = format(new Date(), FMT_DAY_TIME);
    console.log('done', extra);
    return extra;
}


function DatedConstant(props) {

    const {constant, reload} = props;
    if (constant.values.length === 0) {
        constant.values.push({value: '', time: format(new Date(), FMT_DAY_TIME)});
    }
    const constantState = useState(constant);
    const [newConstant, setNewConstant] = constantState;
    const extraState = useState(emptyCopy(constant));
    const [extra, setExtra] = extraState;

    console.log('DatedConstant', newConstant);

    return (<ColumnCard header={constant.name}>
        <Grid item xs={12}><P>{constant.description}</P></Grid>
        {newConstant.values.map((entry, index) =>
            <DatedValue index={index} constantState={constantState}/>)}
        <ConfirmedWriteButton xs={SAVE_WIDTH} label='Save' disabled={newConstant === constant}
                              href='/api/configure/constant' setData={reload}
                              json={{'constant': convertTypes(newConstant)}}>
            Modifying the constant will change how data are processed.
        </ConfirmedWriteButton>
        <DatedValue constantState={extraState}/>
        <ConfirmedWriteButton xs={SAVE_WIDTH} label='Add'
                              href='/api/configure/constant' setData={reload}
                              json={{'constant': convertTypes(newConstant)}}>
            Adding a new value for the constant will change how data are processed.
        </ConfirmedWriteButton>
    </ColumnCard>);
}


function UndatedConstant(props) {

    const {constant, reload} = props;
    if (constant.values.length === 0) {
        constant.values.push({value: '', time: format(new Date(), FMT_DAY_TIME)});
    }
    const constantState = useState(constant);
    const [newConstant, setNewConstant] = constantState;

    return (<ColumnCard header={constant.name}>
        <Grid item xs={12}><P>{constant.description}</P></Grid>
        <UndatedValue constantState={constantState}/>
        <ConfirmedWriteButton xs={SAVE_WIDTH} label='Save' disabled={newConstant === constant}
                              href='/api/configure/constant' setData={reload}
                              json={{'constant': convertTypes(newConstant)}}>
            Modifying the constant will change how data are processed.
        </ConfirmedWriteButton>
    </ColumnCard>);
}


function Columns(props) {

    const {constants, reload} = props;

    if (constants === null) {
        return <Loading/>;
    } else {
        return (<ColumnList>
            {constants.map(constant =>
                constant.single ?
                    <UndatedConstant constant={constant} reload={reload}/> :
                    <DatedConstant constant={constant} reload={reload}/>)}
        </ColumnList>);
    }
}


function annotateConstants(constants) {
    constants.forEach(constant => {
        constant.composite = constant.values.length > 0 && isComposite(constant.values[0].value);
        if (constant.composite) {
            const value = constant.values[0].value;
            constant.types = {};
            Object.keys(value).forEach(name => constant.types[name] = isString(value[name]) ? String : Number);
        }
    });
    return constants;
}


function convertTypes(constant) {
    if (constant.composite) {
        constant.values.forEach(
            entry => Object.keys(entry.value).forEach(
                name => {
                    entry.value[name] = constant.types[name](entry.value[name])
                }));
    }
    return constant;
}


export default function Constants(props) {

    const {match, history} = props;
    const [constants, setConstants] = useState(null);
    const [edits, setEdits] = useState(0);
    const errorState = useState(null);
    const [error, setError] = errorState;

    function reload() {
        setEdits(edits + 1);
    }

    useEffect(() => {
        setConstants(null);
        fetch('/api/configure/constants')
            .then(handleJson(history, constants => setConstants(annotateConstants(constants)), setError));
    }, [edits]);

    return (
        <Layout navigation={<MainMenu kit/>}
                content={<Columns constants={constants} reload={reload}/>}
                match={match} title='Edit Constants' reload={reload}
                errorState={errorState}/>
    );
}
