import React from 'react';
import {BrowserRouter, Route, Switch} from 'react-router-dom';
import Welcome from "./welcome/Welcome";


export default function Routes() {
    return (
        <BrowserRouter>
            <Switch>
                <Route path='' exact={true} component={Welcome}/>
            </Switch>
        </BrowserRouter>
    );
}
