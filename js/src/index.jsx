import React from 'react';
import ReactDOM from 'react-dom';
import {Routes} from "./components";
import {MuiPickersUtilsProvider} from '@material-ui/pickers';
import DateFnsUtils from '@date-io/date-fns';
import {ThemeProvider} from "@material-ui/styles";
import {theme} from './theme';
import {CssBaseline} from "@material-ui/core";
import log from "loglevel";


log.enableAll();

ReactDOM.render(
    <MuiPickersUtilsProvider utils={DateFnsUtils}>
        <ThemeProvider theme={theme}>
            <CssBaseline/>
            <Routes/>
        </ThemeProvider>
    </MuiPickersUtilsProvider>,
    document.getElementById("content"));
