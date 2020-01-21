
import React, { Component } from 'react';
import Button from '@material-ui/core/Button';

export default class Diary extends Component {

    render() {
        console.log(this.props)
        return (
            <Button variant="contained" color="primary">
                Hello World
            </Button>
       )
    }

}
