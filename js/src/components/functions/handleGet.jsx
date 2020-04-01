
export default function handleGet(history, setData, busy, setBusy) {

    // busy logic is as follows:
    // - initially busy is null
    // - when a busy message is received. busy is set
    // - eventually busy.percent will reach 100 but that may (will) not arrive because the server then
    //   thinks all is ok
    // - so instead, we receive data
    // - if we receive data and percent is not null, we set the 100% message
    // - the busy dialog clears busy to null on OK

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
                    setBusy(json.busy);
                } else if (keys.includes('data')) {
                    console.log('Received data:');
                    console.log(json.data);
                    if (busy !== null && busy.percent < 100) {
                        // fill in final message
                        let copy = {...busy};
                        copy.message = copy.complete;
                        copy.percent = 100;
                        setBusy(copy);
                    }
                    setData(json.data);
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
