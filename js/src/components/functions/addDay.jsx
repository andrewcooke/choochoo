import {parse, format, addDays} from 'date-fns';
import {FMT_DAY} from "../../constants";


export default function addDay(date, days=1) {
    // add one day to a text ual date, returning a new textual date
    var datetime = parse(date, FMT_DAY, new Date());
    datetime = addDays(datetime, days);
    return format(datetime, FMT_DAY);
}