import React from 'react';
import {BrowserRouter, Route, Switch} from 'react-router-dom';
import {Analysis, Diary, Upload, Welcome, Search} from "./pages";
import {Edit, Snapshot, Statistics} from "./pages/kit";
import {Initial, Upgrade, Constants} from "./pages/configure";


export default function Routes() {

    const writer = new Worker('/api/static/writer.js');

    return (
        <BrowserRouter>
            <Switch>
                <Route path='/' exact={true} component={Welcome}/>
                <Route path='/analysis' exact={true} component={Analysis}/>
                <Route path='/search' exact={true} component={Search}/>
                <Route path='/configure/initial' exact={true} component={Initial}/>
                <Route path='/configure/upgrade' exact={true} component={Upgrade}/>
                <Route path='/configure/constants' exact={true} component={Constants}/>
                <Route path='/upload' exact={true} component={Upload}/>
                <Route path='/kit/edit' exact={true} component={Edit}/>
                <Route path='/kit/statistics' exact={true} component={Statistics}/>
                <Route path='/kit/:date' exact={true} component={Snapshot}/>
                <Route path='/:date' exact={true}
                       render={(props) => <Diary {...props} writer={writer}/>}/>
            </Switch>
        </BrowserRouter>
    );
}
