<script lang="ts">
    import type { User } from './lib/User';
    import Playlist from "./lib/Playlist.svelte";
    import Track from "./lib/Track.svelte";
    import './styles/library.css'
    // Sample data - to be fetched from backend on mount
    import playlists from './assets/sample_playlist.json';
    import tracks from './assets/sample_songs.json';

    let userInfo: User = $props();
</script>

<svelte:head>
    <title>Library | Music Match</title>
</svelte:head>

<main class="main-view">
    <header class="main-header">
        <h1>📚 Your Library</h1>
    </header>

    <section class="content">
        <p>Your saved music and preferences.</p>
        <!-- Add library content here -->

        <!-- Section for songs that was swiped right in explore -->
        <p class="library-section-title">Liked Songs</p>
        <div id="library-songs">
            {#each tracks.items as track}
                <Track track={track} />
            {/each}
        </div>

        <!-- Section for playlists fetched from spotify -->
        <p class="library-section-title">Your Playlists</p>
        <div id="library-playlists">
            {#each playlists.items as playlist}
                <Playlist playlist={playlist} />
            {/each}
        </div>

    </section>
</main>