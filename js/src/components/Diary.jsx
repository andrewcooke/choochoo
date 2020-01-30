import React from 'react';
import Layout from "./Layout";
import makeStyles from "@material-ui/core/styles/makeStyles";
import {drawerWidth} from "../layout";
import AppBar from "@material-ui/core/AppBar";
import Tabs from "@material-ui/core/Tabs";
import Tab from "@material-ui/core/Tab";
import Typography from "@material-ui/core/Typography";
import Box from "@material-ui/core/Box";
import {DatePicker} from "@material-ui/pickers";


const useStyles = makeStyles(theme => ({
    root: {
        display: 'flex',
    },
    toolbar: theme.mixins.toolbar,
    content: {
        flexGrow: 1,
        padding: theme.spacing(3),
    },
    nested: {
        paddingLeft: theme.spacing(4),
    },
    tab: {
        'min-width': drawerWidth / 3,
        backgroundColor: theme.palette.background.paper
    },
}));


function TabPanel(props) {

    const {children, value, index, ...other} = props;

    return (
        <Typography
            component="div"
            role="tabpanel"
            hidden={value !== index}
            id={`simple-tabpanel-${index}`}
            aria-labelledby={`simple-tab-${index}`}
            {...other}
        >
            {value === index && <Box p={props.p}>{children}</Box>}
        </Typography>
    );
}

TabPanel.defaultProps = {
    p: 3  /* set to zero to remove padding */
};


function DiaryMenu(props) {

    const [value, setValue] = React.useState(0);
    const onChange = (event, newValue) => {
        setValue(newValue);
    };

    const classes = useStyles();

    return (
        <>
            <AppBar position="static">
                <Tabs value={value} variant="fullWidth" onChange={onChange}
                      indicatorColor="primary"
                      textColor="primary">
                    <Tab label="Day" className={classes.tab}/>
                    <Tab label="Month" className={classes.tab}/>
                    <Tab label="Year" className={classes.tab}/>
                </Tabs>
            </AppBar>
            <TabPanel value={value} index={0}>
                Day Picker
            </TabPanel>
            <TabPanel value={value} index={1}>
                Month Picker
            </TabPanel>
            <TabPanel value={value} index={2}>
                <DatePicker
                    views={["year"]}
                />
            </TabPanel>
        </>
    );
}

export default function Diary(props) {

    const {match} = props;

    const classes = useStyles();

    const content = (
        <p>
            Diary here.
        </p>);

    return (
        <Layout navigation={<DiaryMenu/>} content={content} match={match} title='Diary'/>
    );
}
