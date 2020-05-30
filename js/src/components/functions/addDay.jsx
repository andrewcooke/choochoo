import {parse, format, addDays} from 'date-fns';
import {FMT_DAY} from "../../constants";


export default function addDay(date, days=1) {
    // add one day to a textual date, returning a new textual date
    if (date.indexOf(' ') >= 0) date = date.split(' ')[0];  // drop time if present
    var datetime = parse(date, FMT_DAY, new Date());
    datetime = addDays(datetime, days);
    return format(datetime, FMT_DAY);
}