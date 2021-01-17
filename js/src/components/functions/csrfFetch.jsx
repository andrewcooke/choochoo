
import log from 'loglevel';


export default function csrfFetch(url, init={}) {
    if (! ('headers' in init)) init.headers = {};
    init.headers['CsrfCheck'] = 'True';
    init.credentials = 'same-origin';
    log.debug(init);
    return fetch(url, init);
}
