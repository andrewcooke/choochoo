
import log from "loglevel";


export default function handleJson(history, setData, setError, busyState) {

    // busy logic is as follows:
    // - initially busy is null
    // - when a busy message is received. busy is set
    // - eventually busy.percent will reach 100 but that may (will) not arrive because the server then
    //   thinks all is ok
    // - so instead, we receive data
    // - if we receive data and percent is not null, we set the 100% message
    // - the busy dialog clears busy to null on OK

    // error logic:
    // - if server traps an exception it sends an error
    // - setError is called
    // - error dialog is displayed
    // - user either continues or reloads

    // redirect logic:
    // - if server sends a redirect we respond

    const [busy, setBusy] = busyState === undefined ? [null, undefined] : busyState;

    return response => {

        function handler(json) {
            try {
                log.debug('JSON:', json);
                const keys = Object.keys(json);
                if (keys.includes('redirect')) {
                    log.debug(`Redirect to ${json.redirect}`);
                    history.push(json.redirect);
                } else if (setBusy !== undefined && keys.includes('busy')) {
                    log.debug('Received busy:');
                    log.debug(json.busy);
                    setBusy(json.busy);
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
                    if (busy !== null && busy.percent < 100) {
                        if (setBusy === undefined) {
                            log.debug(`Ignoring busy - undefined setBusy()`)
                        } else {
                            // fill in final message
                            let copy = {...busy};
                            copy.message = copy.complete;
                            copy.percent = 100;
                            setBusy(copy);
                        }
                    }
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
