import React from 'react';
import {Button} from "@material-ui/core";
import {makeStyles} from "@material-ui/styles";
import log from "loglevel";


const useStyles = makeStyles(theme => ({
    button: {
        width: '100%',
    },
}));


export default function LinkButton(props) {
    const {href, children, disabled=false, variant='outlined'} = props;
    const classes = useStyles();
    const prefix = href.startsWith('/api') ? 'http://localhost:8002' :
        (href.startsWith('api') ? 'http://localhost:8002/' : '');
    log.debug(`URL ${href} with prefix ${prefix}`);
    function onClick() {
        window.open(prefix + href, '_blank')
    }
    return (<Button variant={variant} onClick={onClick} disabled={disabled} className={classes.button}>
        {children}
    </Button>);
}
