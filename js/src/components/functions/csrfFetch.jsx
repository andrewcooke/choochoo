
import log from 'loglevel';


export default function csrfFetch(path, init={}) {
    if (! ('headers' in init)) init.headers = {};
    init.headers['CsrfCheck'] = 'True';
    init.credentials = 'same-origin';
    log.debug(init);
    return fetch('http://localhost:8002' + path, init);
}
