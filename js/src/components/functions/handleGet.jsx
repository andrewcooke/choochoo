

export default function handleGet(history, onSuccess) {

    return response => {

        function handleJson(json) {
            try {
                console.log('JSON:');
                console.log(json);
                const keys = Object.keys(json);
                if (keys.includes('redirect')) {
                    console.log(`Redirect to ${json.redirect}`);
                    history.push(json.redirect);
                } else if (keys.includes('data')) {
                    console.log('Received data:');
                    console.log(json.data);
                    onSuccess(json.data);
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
