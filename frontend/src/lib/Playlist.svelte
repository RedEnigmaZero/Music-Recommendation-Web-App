<script lang="ts">
    import '../styles/playlist.css';
    interface Playlist {
        description: string,
        external_urls: {
            spotify: string
        },
        images: {url: string, height: number | null, width: number | null}[],
        name: string,
        uri: string,
        owner: {
            display_name: string,
        }
    }

    interface Props {
        playlist: Playlist
    }

    let { playlist } : Props = $props();
</script>


<a id="playlist-container" href={playlist.external_urls.spotify}>
    <img src={playlist.images[0].url} alt={`Cover image for playlist ${playlist.name}`} />
    <p id="playlist-name">{playlist.name}</p>
    {#if playlist.description !== ""}
        <p id="playlist-description">{playlist.description}</p>
    {:else}
        <p id="playlist-description">Playlist・{playlist.owner.display_name}</p>
    {/if}
</a>