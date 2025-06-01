<script lang="ts">
  import { onMount } from "svelte";
  import type { User } from "../lib/User"; // Assuming User type
  import "./styles/Search.css"; // Styles for the search view

  export let userInfo: User | null; // Passed from App.svelte
  export let logout: () => void; // Passed from App.svelte

  let searchQuery = "";

  // Search types can be extended with checkboxes or a multi-select
  let searchTypes = {
    track: true,
    artist: true,
    album: true,
  };

  // Interfaces to define the structure of search results
  interface ArtistSimple {
    name: string;
    id?: string;
  }
  interface ImageSimple {
    url: string;
    height?: number;
    width?: number;
  }

  interface TrackResult {
    id: string;
    name: string;
    artists: ArtistSimple[];
    album_name?: string;
    image_url?: string;
    url?: string;
  }
  interface ArtistResult {
    id: string;
    name: string;
    image_url?: string;
    genres?: string[];
    url?: string;
  }
  interface AlbumResult {
    id: string;
    name: string;
    artists: ArtistSimple[];
    image_url?: string;
    release_date?: string;
    total_tracks?: number;
    url?: string;
  }

  // Overall structure to hold search results
  interface SearchResults {
    tracks?: TrackResult[];
    artists?: ArtistResult[];
    albums?: AlbumResult[];
  }

  // Global Variables to hold search state
  let results: SearchResults = {};
  let isLoading = false;
  let errorMessage = "";
  let noResultsMessage = "";

  async function performSearch() {
    // Check if the search query is empty or only whitespace
    if (!searchQuery.trim()) {
      errorMessage = "Please enter a search query.";
      results = {};
      noResultsMessage = "";
      // Reset results and messages and return without performing search
      return;
    }

    // Covert searchTypes object to a comma-separated string of active types
    // that are checked for the backemd API call
    const activeTypes = Object.entries(searchTypes)
      .filter(([, isActive]) => isActive)
      .map(([type]) => type)
      .join(",");

    // Check for: At least one type must be selected
    if (!activeTypes) {
      errorMessage =
        "Please select at least one search type (tracks, artists, albums).";
      results = {};
      noResultsMessage = "";
      return;
    }

    // Set UI State for Loading
    isLoading = true;
    errorMessage = "";
    noResultsMessage = "";
    console.log(
      `SEARCH: Searching for "${searchQuery}" types: "${activeTypes}"`
    );

    // Make the API call to the backend
    try {
      const response = await fetch(
        `/api/spotify/search?q=${encodeURIComponent(searchQuery)}&type=${encodeURIComponent(activeTypes)}&limit=10`
      );

      // Check if the response is ok (status 200)
      if (!response.ok) {
        if (response.status === 401) {
          errorMessage =
            "Your session may have expired. Please log out and log back in.";
        } else {
          const errData = await response
            .json()
            .catch(() => ({ error: "Failed to parse server error" }));
          errorMessage = errData.error || `Error: ${response.statusText}`;
        }
        results = {};
      } else {
        // Parse the JSON response
        const data: SearchResults = await response.json();
        console.log("SEARCH: Results received:", data);
        results = data;
        // Check if all categories are empty/missing
        if (
          (!data.tracks || data.tracks.length === 0) &&
          (!data.artists || data.artists.length === 0) &&
          (!data.albums || data.albums.length === 0)
        ) {
          noResultsMessage = "No results found for your query.";
        }
      }
    } catch (err) {
      console.error("SEARCH: Network or parsing error:", err);
      errorMessage =
        "Failed to fetch search results. Please check your connection and try again.";
      results = {};
    }
    // Update UI State after search
    isLoading = false;
  }

  // Helper function to format artist names from an array of artist objects
  function getArtistNames(artists: ArtistSimple[] | undefined): string {
    if (!artists) return "Unknown Artist";
    return artists.map((a) => a.name).join(", ");
  }
</script>

<svelte:head>
  <title>Search | Music Match</title>
</svelte:head>

<main class="main-view">
  <header class="main-header">
    <h1>🔍 Search Spotify</h1>
    {#if logout}
      <button class="logout-btn" on:click={logout}>Logout</button>
    {/if}
  </header>

  <section class="content">
    <div class="search-controls">
      <input
        type="text"
        bind:value={searchQuery}
        placeholder="Search for songs, artists, albums..."
        class="search-input"
        on:keypress={(e) => e.key === "Enter" && performSearch()}
      />
      <div class="search-types">
        <label
          ><input type="checkbox" bind:checked={searchTypes.track} /> Tracks</label
        >
        <label
          ><input type="checkbox" bind:checked={searchTypes.artist} /> Artists</label
        >
        <label
          ><input type="checkbox" bind:checked={searchTypes.album} /> Albums</label
        >
      </div>
      <button
        class="search-button"
        on:click={performSearch}
        disabled={isLoading || !searchQuery.trim()}
      >
        {#if isLoading}Searching...{:else}Search{/if}
      </button>
    </div>

    {#if errorMessage}
      <p class="error-message">{errorMessage}</p>
    {/if}

    {#if noResultsMessage && !errorMessage && !isLoading}
      <p>{noResultsMessage}</p>
    {/if}

    {#if results.tracks && results.tracks.length > 0}
      <div class="results-category">
        <h2>Tracks</h2>
        <ul class="results-list tracks-list">
          {#each results.tracks as track (track.id)}
            <li class="result-item track-item">
              <a
                href={track.url || "#"}
                target="_blank"
                rel="noopener noreferrer"
                class="result-link"
              >
                {#if track.image_url}
                  <img
                    src={track.image_url}
                    alt="{track.name} album cover"
                    class="result-image"
                  />
                {:else}
                  <div class="result-image-placeholder">🎵</div>
                {/if}
                <div class="result-info">
                  <span class="result-name">{track.name}</span>
                  <span class="result-artists"
                    >{getArtistNames(track.artists)}</span
                  >
                  {#if track.album_name}<span class="result-album"
                      >Album: {track.album_name}</span
                    >{/if}
                </div>
              </a>
            </li>
          {/each}
        </ul>
      </div>
    {/if}

    {#if results.artists && results.artists.length > 0}
      <div class="results-category">
        <h2>Artists</h2>
        <ul class="results-list artists-list">
          {#each results.artists as artist (artist.id)}
            <li class="result-item artist-item">
              <a
                href={artist.url || "#"}
                target="_blank"
                rel="noopener noreferrer"
                class="result-link"
              >
                {#if artist.image_url}
                  <img
                    src={artist.image_url}
                    alt={artist.name}
                    class="result-image artist-image"
                  />
                {:else}
                  <div
                    class="result-image-placeholder artist-image-placeholder"
                  >
                    👤
                  </div>
                {/if}
                <div class="result-info">
                  <span class="result-name">{artist.name}</span>
                  {#if artist.genres && artist.genres.length > 0}
                    <span class="result-genres"
                      >Genres: {artist.genres.slice(0, 3).join(", ")}</span
                    >
                  {/if}
                </div>
              </a>
            </li>
          {/each}
        </ul>
      </div>
    {/if}

    {#if results.albums && results.albums.length > 0}
      <div class="results-category">
        <h2>Albums</h2>
        <ul class="results-list albums-list">
          {#each results.albums as album (album.id)}
            <li class="result-item album-item">
              <a
                href={album.url || "#"}
                target="_blank"
                rel="noopener noreferrer"
                class="result-link"
              >
                {#if album.image_url}
                  <img
                    src={album.image_url}
                    alt="{album.name} cover"
                    class="result-image"
                  />
                {:else}
                  <div class="result-image-placeholder">💿</div>
                {/if}
                <div class="result-info">
                  <span class="result-name">{album.name}</span>
                  <span class="result-artists"
                    >{getArtistNames(album.artists)}</span
                  >
                  {#if album.release_date}<span class="result-detail"
                      >Released: {album.release_date}</span
                    >{/if}
                </div>
              </a>
            </li>
          {/each}
        </ul>
      </div>
    {/if}
  </section>
</main>
