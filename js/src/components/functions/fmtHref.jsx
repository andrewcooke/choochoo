import {vsprintf} from 'sprintf-js';


export default function fmtHref(pattern, ...args) {
    return vsprintf(pattern, args.map(arg => encodeURIComponent(arg)));
}
