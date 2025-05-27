<script lang="ts">
	import { onMount } from 'svelte';
  
	let isAuthenticated = false;
	let userInfo = null;
  
	// Check for auth token or handle redirect response
	onMount(async () => {
	  const params = new URLSearchParams(window.location.search);
	  const code = params.get('code');
  
	  if (code) {
		// Send code to your Flask backend to exchange for token
		const response = await fetch(`http://localhost:5000/api/auth/authorize?code=${code}`);
		if (response.ok) {
		  const data = await response.json();
		  userInfo = data.user;
		  isAuthenticated = true;
		}
	  }
	});
  
	const DEX_CLIENT_ID = "Music-app";
	const REDIRECT_URI = "http://localhost:8000/authorize";
	const DEX_AUTH_ENDPOINT = "http://localhost:5556/auth";
  
	const loginWithDex = () => {
	  const loginUrl = `${DEX_AUTH_ENDPOINT}?client_id=${DEX_CLIENT_ID}&redirect_uri=${encodeURIComponent(REDIRECT_URI)}&response_type=code&scope=openid email profile`;
	  window.location.href = loginUrl;
	};
  
	const logout = () => {
	  isAuthenticated = false;
	  userInfo = null;
	  window.location.href = '/';
	};
  </script>
  
  <svelte:head>
	<title>Music Match</title>
	<link rel="stylesheet" href="/app.css" />
  </svelte:head>
  
  {#if isAuthenticated}
	<div class="main-container">
	  <header>
		<h1>🎵 Welcome, {userInfo?.name || "User"}!</h1>
		<button on:click={logout}>Logout</button>
	  </header>
  
	  <section class="content">
		<p>Set your music preferences or start exploring recommendations.</p>
		<!-- Placeholder for additional components like preferences or song recs -->
	  </section>
	</div>
  {:else}
	<div class="login-container">
	  <h1>🎵 Welcome to Music Match 🎵</h1>
	  <p>Discover music you'll love based on your preferences.</p>
	  <button on:click={loginWithDex}>Login with Dex</button>
	</div>
  {/if}
  