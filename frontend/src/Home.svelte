<script lang="ts">
    import type { User } from './lib/User';

    // The sample data is from https://developer.spotify.com/documentation/web-api/reference/get-users-saved-tracks
    // From what I see on spotify documentation, although some fields might differ
    // the content of array for songs seem to be fairly consistent.
    // Changing from sample data to normal data should require minimal modification
    import sampleTracks from './assets/sample_songs.json'
    import {onMount} from "svelte";
  
    export let userInfo: User;
    export let logout: () => void;

    function transformData(songs: any) {
      return songs.items.map((song: any) => {
        return {
          image: song.track.album.images[0]?.url, // Can put if condition here for default image
          name: song.track.name,
          artist: song.track.artists.map((artist: any) => artist.name).join(", "), // More than one artist
        }
      });
    }

    let trendingSongs = [];
    let recentSongs = [];

    onMount(() => {
      // Get trending songs and recent songs from backend.
      // Hopefully transformation can be done on backend side too.
      trendingSongs = transformData(sampleTracks);
      recentSongs = transformData(sampleTracks);
    })
  </script>
  
  <svelte:head>
    <title>Home | Music Match</title>
  </svelte:head>
  
  <main class="main-view">
    <header class="main-header">
      <h1>🎵 Welcome, {userInfo?.name || "User"}!</h1>
      <button class="logout-btn" on:click={logout}>Logout</button>
    </header>
  
    <section class="scroll-section">
      <h2>🔥 Trending Now</h2>
      <div class="scroll-container">
        {#each trendingSongs as song}
          <div class="album-card">
            <img
              src={song.image}
              alt={song.name}
              style="width: 160px; height: 160px; object-fit: cover; border-radius: 6px;"
            />
            <p><strong>{song.name}</strong></p>
            <p style="font-size: 0.85rem;">{song.artist}</p>
          </div>
        {/each}
      </div>
      <h2>🎵 Recents</h2>
      <div class="stack-container">
        {#each recentSongs as song}
          <div class="album-card">
            <img
                    src={song.image}
                    alt={song.name}
                    style="width: 160px; height: 160px; object-fit: cover; border-radius: 6px;"
            />
            <p><strong>{song.name}</strong></p>
            <p style="font-size: 0.85rem;">{song.artist}</p>
          </div>
        {/each}
      </div>
    </section>
  </main>
  