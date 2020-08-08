
import log from "loglevel";


export default function handleJson(history, setData, setError) {

    // error logic:
    // - if server traps an exception it sends an error
    // - setError is called
    // - error dialog is displayed
    // - user either continues or reloads

    // redirect logic:
    // - if server sends a redirect we respond

    return response => {

        function handler(json) {
            try {
                log.debug('JSON:', json);
                const keys = Object.keys(json);
                if (keys.includes('redirect')) {
                    log.debug(`Redirect to ${json.redirect}`);
                    history.push(json.redirect);
                } else if (keys.includes('error')) {
                    log.debug('Received error:');
                    log.debug(json.error);
                    if (setError === undefined) {
                        log.debug(`Ignoring error - undefined setError()`)
                    } else {
                        setError(json.error);
                    }
                } else if (keys.includes('data')) {
                    log.debug('Received data:');
                    log.debug(json.data);
                    setData(json.data);
                } else {
                    throw new Error(`Unexpected response ${keys} / ${json}`);
                }
            } catch (e) {
                log.debug(`Caught ${e}`)
                setError(e.message);
            }
        }

        log.debug('Response:');
        log.debug(response);
        return response.json().then(handler);
    }
}
