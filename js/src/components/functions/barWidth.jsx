import {barFraction, barEnd} from "../../constants";


export default function barWidth(array) {
    const n = array.length;
    if (n === 0) return 0;
    if (n === 1) return barFraction;
    return (barFraction - barEnd * (n - 1)) / n;
}
