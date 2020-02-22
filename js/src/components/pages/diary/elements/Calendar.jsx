import React from "react";
import {getDay, getDaysInMonth, parse} from "date-fns";
import {Loading, range} from "../../../utils";


function dayOfWeek(date) {
    let dow = getDay(date);   // 0 is sunday!
    dow = dow - 1;  // 0 is monday but sunday is negative
    dow = (dow + 7) % 7;  // range 0-6
    return dow;
}


function CalendarDays(props) {
    return (<tr>{['M', 'T', 'W', 'T', 'F', 'S', 'S'].map(
        (day, key) => <td key={key}>{day}</td>
    )}</tr>);
}


function CalendarWeek(props) {
    const {start, finish} = props;
    return (<tr>
        {range(start, Math.min(start+7, finish+1)).map(
            day => day > 0 ? <td key={day}>{day + ''}</td> : <td key={day}/>
        )}
    </tr>)
}


export default function Calendar(props) {

    const {month, active, onChange} = props;

    if (!Array.isArray(active)) {
        return <Loading/>;  // undefined initial data
    } else {
        const first = parse(month + '-01', 'yyyy-MM-dd', new Date());
        const start = dayOfWeek(first);
        const days = getDaysInMonth(first);
        return (<table><tbody>
        <CalendarDays/>
        {range(1-start, days, 7).map(
            start => <CalendarWeek start={start} finish={days} key={start}/>)}
        </tbody></table>)
    }
}
