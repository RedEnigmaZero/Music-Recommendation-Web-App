<script lang="ts">
    import type { User } from './lib/User';
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

    // Function to transform new releases data from Spotify API
    function transformNewReleases(releases: any) {
      if (!releases.items) return [];
      return releases.items.map((album: any) => {
        return {
          image: album.image,
          name: album.name,
          artist: album.artists,
          id: album.id,
          url: album.url,
          release_date: album.release_date,
          album_type: album.album_type
        }
      });
    }

    // Function to transform user tracks data from Spotify API
    function transformUserTracks(userTracks: any) {
      if (!userTracks.items) return [];
      return userTracks.items.map((item: any) => {
        return {
          image: item.image || '/default-album-cover.png',
          name: item.name,
          artist: item.artists,
          id: item.id,
          url: item.url,
          added_at: item.added_at,
          album_name: item.album_name,
          popularity: item.popularity
        }
      });
    }

    // Function to transform browse categories data from Spotify API
    function transformBrowseCategories(categories: any) {
      if (!categories.items) return [];
      return categories.items.map((category: any) => {
        return {
          id: category.id,
          name: category.name,
          image: category.icons && category.icons.length > 0 ? category.icons[0].url : '/default-category.png',
          href: category.href,
          // Create Spotify URL for category
          url: `https://open.spotify.com/genre/${category.id}`
        }
      });
    }

    let trendingSongs = [];
    let recentSongs = [];
    let newReleases = [];
    let userTracks = [];
    let browseCategories = [];
    let userTracksSource = '';
    let loading = true;
    let error = null;

    // Function to fetch new releases from your backend
    async function fetchNewReleases() {
      try {
        const response = await fetch('/api/new-releases?limit=10');
        if (!response.ok) {
          throw new Error(`Failed to fetch new releases: ${response.status}`);
        }
        const data = await response.json();
        return transformNewReleases(data);
      } catch (err) {
        console.error('Error fetching new releases:', err);
        error = 'Failed to load new releases';
        return [];
      }
    }

    // Function to fetch user's saved tracks or top tracks from your backend
    async function fetchUserTracks() {
      try {
        const response = await fetch('/api/user-tracks?limit=10');
        if (!response.ok) {
          throw new Error(`Failed to fetch user tracks: ${response.status}`);
        }
        const data = await response.json();
        userTracksSource = data.source || 'unknown';
        return transformUserTracks(data);
      } catch (err) {
        console.error('Error fetching user tracks:', err);
        error = 'Failed to load user tracks';
        return [];
      }
    }

    // Function to fetch browse categories from your backend
    async function fetchBrowseCategories() {
      try {
        const response = await fetch('/api/browse-categories?limit=12');
        if (!response.ok) {
          throw new Error(`Failed to fetch browse categories: ${response.status}`);
        }
        const data = await response.json();
        return transformBrowseCategories(data);
      } catch (err) {
        console.error('Error fetching browse categories:', err);
        error = 'Failed to load browse categories';
        return [];
      }
    }

    onMount(async () => {
      loading = true;
      
      // Get trending songs and recent songs from backend.
      // Hopefully transformation can be done on backend side too.
      trendingSongs = transformData(sampleTracks);
      recentSongs = transformData(sampleTracks);
      
      // Fetch new releases, user tracks, and browse categories from Spotify
      const [newReleasesData, userTracksData, browseCategoriesData] = await Promise.all([
        fetchNewReleases(),
        fetchUserTracks(),
        fetchBrowseCategories()
      ]);
      
      newReleases = newReleasesData;
      userTracks = userTracksData;
      browseCategories = browseCategoriesData;
      
      loading = false;
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
      <!-- User's Music Section (Saved Tracks or Top Tracks) -->
      <h2>🎵 {userTracksSource === 'saved_tracks' ? 'Your Recently Saved Music' : 'Your Top Tracks'}</h2>
      {#if loading}
        <p>Loading your music...</p>
      {:else if error && userTracks.length === 0}
        <p class="error-message">{error}</p>
      {:else if userTracks.length === 0}
        <p>No saved tracks found. Try saving some music to your library!</p>
      {:else}
        <div class="scroll-container">
          {#each userTracks as track}
            <div class="album-card clickable" on:click={() => track.url && window.open(track.url, '_blank')}>
              <img
                src={track.image}
                alt={track.name}
                style="width: 160px; height: 160px; object-fit: cover; border-radius: 6px;"
              />
              <p><strong>{track.name}</strong></p>
              <p style="font-size: 0.85rem;">{track.artist}</p>
              {#if track.album_name}
                <p style="font-size: 0.75rem; color: #666;">{track.album_name}</p>
              {/if}
            </div>
          {/each}
        </div>
      {/if}

	  <!-- Browse Categories Section -->
      <h2>🎭 Browse by Category</h2>
      {#if loading}
        <p>Loading categories...</p>
      {:else if error}
        <p class="error-message">{error}</p>
      {:else if browseCategories.length === 0}
        <p>No categories available at the moment.</p>
      {:else}
        <div class="scroll-container">
          {#each browseCategories as category}
            <div class="album-card clickable" on:click={() => window.open(category.url, '_blank')}>
              <img
                src={category.image}
                alt={category.name}
                style="width: 160px; height: 160px; object-fit: cover; border-radius: 6px;"
              />
              <p><strong>{category.name}</strong></p>
            </div>
          {/each}
        </div>
      {/if}

      <!-- New Releases Section -->
      <h2>Spotify's Featured Music</h2>
      {#if loading}
        <p>Loading new releases...</p>
      {:else if error}
        <p class="error-message">{error}</p>
      {:else}
        <div class="scroll-container">
          {#each newReleases as album}
            <div class="album-card clickable" on:click={() => window.open(album.url, '_blank')}>
              <img
                src={album.image || '/default-album-cover.png'}
                alt={album.name}
                style="width: 160px; height: 160px; object-fit: cover; border-radius: 6px;"
              />
              <p><strong>{album.name}</strong></p>
              <p style="font-size: 0.85rem;">{album.artist}</p>
              {#if album.release_date}
                <p style="font-size: 0.75rem; color: #666;">{album.release_date}</p>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
      
    </section>
  </main>

  <style>
    .error-message {
      color: #ff6b6b;
      font-style: italic;
      padding: 1rem;
    }

    .clickable {
      cursor: pointer;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .clickable:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    .clickable:active {
      transform: translateY(0);
    }
  </style>
