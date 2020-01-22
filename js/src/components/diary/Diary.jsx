
import React from 'react';
import Button from '@material-ui/core/Button';
import TopBar from './TopBar.jsx'


export default function Diary(props) {
    return (
        <div>
            <TopBar />
            <Button variant="contained" color="primary">
                Hello World
            </Button>
        </div>
   )
}


