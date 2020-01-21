
import React, { Component } from 'react';
import { BrowserRouter, Route, Switch } from 'react-router-dom';
import Diary from './Diary';


export default class Routes extends Component {

    render() {
        return (
            <BrowserRouter>
                <Switch>
                    <Route path='/:date' component={Diary} />
                </Switch>
            </BrowserRouter>
        );
    }

}
