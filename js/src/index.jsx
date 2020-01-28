import React from 'react';
import ReactDOM from 'react-dom';
import Routes from "./components/Routes";
import { MuiPickersUtilsProvider } from '@material-ui/pickers';
import DateFnsUtils from '@date-io/date-fns';


ReactDOM.render(
    <MuiPickersUtilsProvider utils={DateFnsUtils}>
        <Routes/>
    </MuiPickersUtilsProvider>,
    document.getElementById("content"));
