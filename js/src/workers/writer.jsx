
const pause_ms = 500;
var timeout;


function queue(event) {
    console.log(`queue ${event}`)
}


function write() {
    console.log('write');
}


self.addEventListener('message', (event) => {
    if (timeout !== undefined) clearTimeout(timeout);
    queue(event);
    timeout = setTimeout(write, pause_ms);
});
