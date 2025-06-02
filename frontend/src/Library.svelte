<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import type { User } from "./lib/User"; // Assuming User type is defined
  import "./styles/library.css";

  // Props passed from App.svelte
  export let userInfo: User | null; // User info, can be null if not immediately available
  export let logout: () => void; // Logout function passed from App.svelte

  interface Playlist {
    id: string;
    name: string;
    url?: string;
    imageUrl?: string;
    track_count: number;
  }

  let playlists: Playlist[] = [];
  let isLoading = true;
  let errorMessage: string | null = null;
  let isMounted = false; // To prevent state updates if component is unmounted

  async function fetchUserPlaylists() {
    if (!isMounted) return; // Don't fetch if component isn't mounted or already unmounted
    isLoading = true;
    errorMessage = null;
    console.log("LIBRARY: Attempting to fetch user playlists...");

    try {
      const response = await fetch("/api/playlists"); // Proxied by Vite

      if (!isMounted) return; // Check again before updating state

      if (!response.ok) {
        if (response.status === 401) {
          console.error(
            "LIBRARY: Unauthorized (401) to fetch playlists. Session might have expired or token invalid."
          );
          errorMessage =
            "Your session may have expired. Please try logging out and logging back in.";
        } else {
          let errMessage = "Failed to load playlists.";
          try {
            const errData = await response.json();
            errMessage =
              errData.message || errData.error || response.statusText;
          } catch (parseError) {
            console.warn(
              "LIBRARY: Could not parse error JSON from server",
              parseError
            );
            errMessage = response.statusText || "Server error.";
          }
          console.error(
            "LIBRARY: Error fetching playlists:",
            response.status,
            errMessage
          );
          errorMessage = `Could not load playlists: ${errMessage}`;
        }
        playlists = [];
      } else {
        const data: Playlist[] = await response.json();
        if (!isMounted) return; // Check again
        console.log("LIBRARY: Playlists received from backend:", data);
        playlists = data;
        if (playlists.length === 0) {
          console.log("LIBRARY: User has no playlists or none were returned.");
        }
      }
    } catch (e: any) {
      if (!isMounted) return; // Check again
      console.error(
        "LIBRARY: Network or other critical error fetching playlists:",
        e
      );
      errorMessage =
        "A network error occurred, or the server could not be reached. Please try again.";
      playlists = [];
    }
    if (isMounted) {
      isLoading = false;
    }
  }

  onMount(() => {
    isMounted = true;
    // Fetch playlists only if userInfo is present, indicating user is likely authenticated.
    // The backend /api/playlists will ultimately verify the token.
    if (userInfo) {
      console.log(
        "LIBRARY: UserInfo present onMount, fetching playlists.",
        userInfo
      );
      fetchUserPlaylists();
    } else {
      // If userInfo is null, it means App.svelte's handleAuth/getUserInfo determined no active session.
      console.log(
        "LIBRARY: UserInfo not present onMount. User is not authenticated."
      );
      errorMessage = "Please log in to see your library.";
      isLoading = false;
    }

    return () => {
      isMounted = false; // Cleanup on unmount
    };
  });

  // Reactive statement to refetch if userInfo changes from null to a user (e.g. after login completes)
  // This is useful if Library tab is already active when login finishes.
  $: if (
    userInfo &&
    playlists.length === 0 &&
    !isLoading &&
    !errorMessage &&
    isMounted
  ) {
    console.log(
      "LIBRARY: userInfo became available or changed, re-fetching playlists if empty."
    );
    fetchUserPlaylists();
  }
</script>

<svelte:head>
  <title>Library | Music Match</title>
</svelte:head>

<main class="main-view">
  <header class="main-header">
    <h1>📚 Your Spotify Playlists</h1>
    {#if logout}
      <button class="logout-btn" on:click={logout}>Logout</button>
    {/if}
  </header>

  <section class="content">
    {#if isLoading}
      <p>Loading your playlists...</p>
    {:else if errorMessage}
      <p class="error-message">{errorMessage}</p>
      {#if !errorMessage.includes("session may have expired")}
        <button class="action-button" on:click={fetchUserPlaylists}
          >Try Again</button
        >
      {/if}
    {:else if playlists.length === 0}
      <p>
        You don't have any playlists on Spotify, or we couldn't load them yet.
      </p>
    {:else}
      <p>Here are your playlists ({playlists.length}):</p>
      <ul class="playlist-grid">
        {#each playlists as playlist (playlist.id)}
          <li class="playlist-item">
            <a
              href={playlist.url || "#"}
              target="_blank"
              rel="noopener noreferrer"
              class="playlist-link"
            >
              {#if playlist.imageUrl}
                <img
                  src={playlist.imageUrl}
                  alt="{playlist.name} cover"
                  class="playlist-image"
                  on:error={(e) => {
                    (e.target as HTMLImageElement).style.display = "none";
                  }}
                />
              {:else}
                <div class="playlist-image-placeholder">🎵</div>
              {/if}
              <div class="playlist-info">
                <h3 class="playlist-name">{playlist.name}</h3>
                <p class="playlist-tracks">Tracks: {playlist.track_count}</p>
              </div>
            </a>
          </li>
        {/each}
      </ul>
    {/if}
  </section>
</main>
