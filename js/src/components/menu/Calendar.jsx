import React from "react";
import {getDay, getDaysInMonth, parse} from "date-fns";
import {Loading} from "../elements";
import {Button} from "@material-ui/core";
import {makeStyles} from "@material-ui/core/styles";
import {FMT_DAY} from "../../constants";
import {sprintf} from "sprintf-js";
import {range} from '../functions';


const useStyles = makeStyles(theme => ({
    table: {
        marginTop: theme.spacing(2),
        marginLeft: 'auto',
        marginRight: 'auto',
    },
    tdDay: {
        textAlign: 'center',
    },
    tdDate: {
        textAlign: 'center',
    },
    button: {
        padding: '0px',
        minWidth: '25px',
    },
}));


function dayOfWeek(date) {
    let dow = getDay(date);   // 0 is sunday!
    dow = dow - 1;  // 0 is monday but sunday is negative
    dow = (dow + 7) % 7;  // range 0-6
    return dow;
}


function CalendarDays(props) {
    const classes = useStyles();
    return (<tr>{['M', 'T', 'W', 'T', 'F', 'S', 'S'].map(
        (day, i) => <td className={classes.tdDay} key={i}>{day}</td>
    )}</tr>);
}


function CalendarWeek(props) {

    const {start, finish, month, active, onChange} = props;
    const classes = useStyles();

    return (<tr>
        {range(start, Math.min(start+7, finish+1)).map(
            (day, i) => {
                const date = sprintf('%s-%02d', month, day);
                const disabled = ! active.includes(date);
                return day > 0 ?
                    <td className={classes.tdDate} key={i}>
                        <Button className={classes.button} onClick={() => onChange(date)} disabled={disabled}>
                            {day + ''}
                        </Button>
                    </td> :
                    <td key={i+0.5}/>;
            }
        )}
    </tr>)
}


export default function Calendar(props) {

    const {month, active, onChange} = props;
    const classes = useStyles();

    if (!Array.isArray(active)) {
        return <Loading/>;  // undefined initial data
    } else {
        const first = parse(month + '-01', FMT_DAY, new Date());
        const start = dayOfWeek(first);
        const days = getDaysInMonth(first);
        return (<table className={classes.table}><tbody>
        <CalendarDays/>
        {range(1-start, days, 7).map(
            (start, i) => <CalendarWeek start={start} finish={days} month={month} active={active} key={i}
                                        onChange={onChange}/>)}
        </tbody></table>)
    }
}
