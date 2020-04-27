import React from 'react';
import ReactDOM from 'react-dom';
import {Routes} from "./components";
import {MuiPickersUtilsProvider} from '@material-ui/pickers';
import {DateFnsUtils} from '@date-io';
import {ThemeProvider} from "@material-ui/styles";
import {theme} from './theme';
import {CssBaseline} from "@material-ui/core";


ReactDOM.render(
    <MuiPickersUtilsProvider utils={DateFnsUtils}>
        <ThemeProvider theme={theme}>
            <CssBaseline/>
            <Routes/>
        </ThemeProvider>
    </MuiPickersUtilsProvider>,
    document.getElementById("content"));
