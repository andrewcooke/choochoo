import React from 'react';
import {BrowserRouter, Route, Switch} from 'react-router-dom';
import {Analysis, Diary, Upload, Welcome, Error, Busy} from "./pages";
import {Edit, Snapshot, Statistics} from "./pages/kit";


export default function Routes() {

    return (
        <BrowserRouter>
            <Switch>
                <Route path='/' exact={true} component={Welcome}/>
                <Route path='/error' exact={true} component={Error}/>
                <Route path='/busy' exact={true} component={Busy}/>
                <Route path='/analysis' exact={true} component={Analysis}/>
                <Route path='/upload' exact={true} component={Upload}/>
                <Route path='/kit/edit' exact={true} component={Edit}/>
                <Route path='/kit/statistics' exact={true} component={Statistics}/>
                <Route path='/kit/:date' exact={true} component={Snapshot}/>
                <Route path='/:date' exact={true} component={Diary}/>
            </Switch>
        </BrowserRouter>
    );
}
