import React from 'react';
import {BrowserRouter, Route, Switch} from 'react-router-dom';
import {Jupyter, Search, Upload, Welcome} from "./pages";
import {Edit, Snapshot, KitStatistics} from "./pages/kit";
import {Constants, Initial, Import} from "./pages/configure";
import {Day, Month, Year} from "./pages/diary";
import {Create, Sector} from "./pages/sector";
import {Statistics} from "./pages/statistics";


export default function Routes() {

    // load this once - if it's inside Day then it is reloaded on each view
    const writer = new Worker('/api/static/writer.js');

    return (
        <BrowserRouter>
            <Switch>
                <Route path='/search' exact={true} component={Search}/>
                <Route path='/configure/initial' exact={true} component={Initial}/>
                <Route path='/configure/import' exact={true} component={Import}/>
                <Route path='/configure/constants' exact={true} component={Constants}/>
                <Route path='/jupyter' exact={true} component={Jupyter}/>
                <Route path='/kit/edit' exact={true} component={Edit}/>
                <Route path='/kit/statistics' exact={true} component={KitStatistics}/>
                <Route path='/kit/:date' exact={true} component={Snapshot}/>
                <Route path='/sector/:id(\d+)' exact={true} component={Sector}/>
                <Route path='/sector/new/:id(\d+)' exact={true} component={Create}/>
                <Route path='/statistics' exact={true} component={Statistics}/>
                <Route path='/statistics/:name([-a-z0-9]*)' exact={true} component={Statistics}/>
                <Route path='/upload' exact={true} component={Upload}/>
                <Route path='/:date(\d+)' exact={true} component={Year}/>
                <Route path='/:date(\d+-\d+)' exact={true} component={Month}/>
                <Route path='/:date(\d+-\d+-\d+)' exact={true}
                       render={(props) => <Day {...props} writer={writer}/>}/>
                <Route path='/*' component={Welcome}/>
            </Switch>
        </BrowserRouter>
    );
}
