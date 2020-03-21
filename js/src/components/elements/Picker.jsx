import {DatePicker} from "@material-ui/pickers";
import React from "react";


export default function Picker(props) {
    const {ymdSelected, datetime, onChange} = props;
    switch (ymdSelected) {
        case 0:
            return <DatePicker value={datetime} views={["year"]} onChange={onChange}/>;
        case 1:
            return <DatePicker value={datetime} views={["year", "month"]} onChange={onChange}/>;
        case 2:
            return <DatePicker value={datetime} animateYearScrolling onChange={onChange}/>;
    }
}
