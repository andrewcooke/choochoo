import React from 'react';
import {BrowserRouter, Route, Switch} from 'react-router-dom';
import {Welcome, Analysis, Diary} from "./pages";


export default function Routes() {
    return (
        <BrowserRouter>
            <Switch>
                <Route path='/' exact={true} component={Welcome}/>
                <Route path='/analysis' exact={true} component={Analysis}/>
                <Route path='/:date' exact={true} component={Diary}/>
            </Switch>
        </BrowserRouter>
    );
}
