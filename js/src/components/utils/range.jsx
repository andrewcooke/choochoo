
function* iRange(start, end, step = 1) {
    let state = start;
    while (state < end) {
        yield state;
        state += step;
    }
}


export default function range(start, end, step=1) {
    return Array.from(iRange(start, end, step));
}
