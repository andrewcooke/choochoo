import React from 'react';
import {BrowserRouter, Route, Switch} from 'react-router-dom';
import {Welcome, Analysis, Diary} from "./pages";
import {Change, Statistics} from "./pages/kit";


export default function Routes() {
    return (
        <BrowserRouter>
            <Switch>
                <Route path='/' exact={true} component={Welcome}/>
                <Route path='/analysis' exact={true} component={Analysis}/>
                <Route path='/kit/change' exact={true} component={Change}/>
                <Route path='/kit/statistics' exact={true} component={Statistics}/>
                <Route path='/:date' exact={true} component={Diary}/>
            </Switch>
        </BrowserRouter>
    );
}
