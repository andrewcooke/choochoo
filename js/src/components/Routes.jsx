import React from 'react';
import {BrowserRouter, Route, Switch} from 'react-router-dom';
import Welcome from "./pages/Welcome";
import Diary from "./pages/Diary";


export default function Routes() {
    return (
        <BrowserRouter>
            <Switch>
                <Route path='/' exact={true} component={Welcome}/>
                <Route path='/:date' exact={true} component={Diary}/>
            </Switch>
        </BrowserRouter>
    );
}
