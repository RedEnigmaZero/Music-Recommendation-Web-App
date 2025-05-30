// To initialize spotify iFrameAPI
// Function content is directly copied from https://open.spotify.com/embed/iframe-api/v1
export default function initSpotify() {
    var scriptUrl = 'https://embed-cdn.spotifycdn.com/_next/static/iframe_api.04eab59592b341e5286c.js';
    var host = 'https://open.spotify.com';
    try {
        var ttPolicy = window.trustedTypes.createPolicy('spotify-embed-api', {
            createScriptURL: function (x) {
                return x;
            },
        });
        scriptUrl = ttPolicy.createScriptURL(scriptUrl);
    } catch (e) {}

    if (!window.SpotifyIframeConfig) {
        window.SpotifyIframeConfig = {};
    }
    SpotifyIframeConfig.host = host;


    if (SpotifyIframeConfig.loading) {
        console.warn('The Spotify Iframe API has already been initialized.');
        return;
    }
    SpotifyIframeConfig.loading = 1;

    var a = document.createElement('script');
    a.type = 'text/javascript';
    a.id = 'spotify-iframeapi-script';
    a.src = scriptUrl;
    a.async = true;
    var c = document.currentScript;
    if (c) {
        var n = c.nonce || c.getAttribute('nonce');
        if (n) a.setAttribute('nonce', n);
    }
    var b = document.getElementsByTagName('script')[0];
    b.parentNode.insertBefore(a, b);
}