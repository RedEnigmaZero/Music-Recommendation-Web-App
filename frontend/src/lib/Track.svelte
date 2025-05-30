<script lang="ts">
    import '../styles/track.css';
    interface Track {
        added_at: string,
        track: {
            album: {
                images: {url: string, height: number | null, width: number | null}[],
                name: string,
                uri: string,
            }
            artists: {external_urls: {spotify: string}, name: string}[],
            name: string,
            uri: string,
            duration_ms: number,
            external_urls: {spotify: string}
        }
    }

    interface Props {
        track: Track
    }

    let { track }: Props = $props();

    // Such an inefficient looking function for styling the time
    function styleDuration(duration_ms: number): string {
        let duration_sec = Math.round(duration_ms / 1000);
        let duration_min = duration_sec / 60;
        duration_sec = duration_sec % 60;

        let duration_sec_str = `${Math.round(duration_sec)}`
        if (duration_sec_str.length === 1) {
            duration_sec_str = "0" + duration_sec_str;
        }

        return `${Math.round(duration_min)}:${duration_sec_str}`;
    }

    function styleArtist(artists: {external_urls: {spotify: string}, name: string}[]) {
        return artists.map((artist) => artist.name).join(', ');
    }
</script>


<a id="track-container" href={track.track.external_urls.spotify}>
    <img src={track.track.album.images[0].url} alt={`Cover image for album ${track.track.album.name}`} />
    <div id="track-title-duration">
        <p id="track-name">{track.track.name}</p>
        <p id="track-duration">{styleDuration(track.track.duration_ms)}</p>
    </div>
    <p id="track-artists">{styleArtist(track.track.artists)}</p>
</a>