<script>
	import { onMount } from 'svelte';
	let query = '';
	let token = '';
	let results = [];
	let error = '';
  
	async function fetchToken() {
	  try {
		const response = await fetch('http://localhost:5137/spotify/token', {
		  method: 'POST'
		});
		if (!response.ok) throw new Error('Token request failed');
		const data = await response.json();
		token = data.access_token;
	  } catch (err) {
		error = 'Failed to fetch Spotify token.';
	  }
	}
  
	async function searchSpotify() {
	  if (!query.trim() || !token) return;
  
	  try {
		const response = await fetch(`http://localhost:5137/spotify/search?q=${encodeURIComponent(query)}`, {
		  headers: {
			Authorization: `Bearer ${token}`
		  }
		});
  
		const data = await response.json();
		if (data.error) {
		  error = data.error.message || 'Error fetching search results';
		  results = [];
		} else {
		  results = data.tracks?.items || [];
		  error = '';
		}
	  } catch (err) {
		error = 'Failed to fetch search results.';
	  }
	}
  
	onMount(fetchToken);
  </script>
  
  <style src="./styles/search.css"></style>
  
  <div class="main-view">
	<div class="search-page">
	  <h1>Search</h1>
	  <p>Look up songs, artists, or genres.</p>
  
	  <div class="search-bar">
		<input type="text" bind:value={query} placeholder="Enter song name..." />
		<button on:click={searchSpotify}>Search</button>
	  </div>
  
	  {#if error}
		<p class="error">{error}</p>
	  {/if}
  
	  {#if results.length > 0}
		<ul class="results">
		  {#each results as track}
			<li>
			  <img src={track.album.images[2]?.url} alt="cover" />
			  <div>
				<strong>{track.name}</strong><br />
				{track.artists.map(a => a.name).join(', ')}
			  </div>
			</li>
		  {/each}
		</ul>
	  {/if}
	</div>
  </div>
  