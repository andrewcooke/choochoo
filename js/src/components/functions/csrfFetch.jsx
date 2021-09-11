
import log from 'loglevel';


export default function csrfFetch(url, init={}) {
    if (! ('headers' in init)) init.headers = {};
    init.headers['CsrfCheck'] = 'True';
    init.credentials = 'same-origin';
    log.debug(init);
    if (process.env.NODE_ENV === 'development')
        return fetch('http://localhost:8000' + url, init);
    else
        return fetch(url, init);
}
