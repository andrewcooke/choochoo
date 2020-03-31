

const BUSY_100 = {'message': 'Upload complete', percent: 100};


export default function handleGet(history, percent, onData, onBusy) {

    // busy logic is as follows:
    // - initially percent is null
    // - when a busy message is received. percent is set to some integer
    // - eventually percent will reach 100 but that may (will) not arrive because the server then
    //   thinks all is ok
    // - so instead, we receive data
    // - if we receive data and percent is not null, we set the 100% message
    // - the busy dialog clears percent to null on OK

    return response => {

        function handleJson(json) {
            try {
                console.log('JSON:');
                console.log(json);
                const keys = Object.keys(json);
                if (keys.includes('redirect')) {
                    console.log(`Redirect to ${json.redirect}`);
                    history.push(json.redirect);
                } else if (keys.includes('busy')) {
                    console.log('Received busy:');
                    console.log(json.busy);
                    onBusy(json.busy);
                } else if (keys.includes('data')) {
                    console.log('Received data:');
                    console.log(json.data);
                    if (percent !== null && percent < 100) onBusy(BUSY_100);
                    onData(json.data);
                } else {
                    throw new Error(`Unexpected response ${keys} / ${json}`);
                }
            } catch (e) {
                console.log(e.message);
                history.push('/error');
            }
        }

        console.log('Response:');
        console.log(response);
        return response.json().then(handleJson);
    }
}
