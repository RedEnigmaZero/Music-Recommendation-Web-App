<script lang="ts">
    import { onMount } from 'svelte';
    import type { User } from './lib/User';
    import Home from './Home.svelte';
    import Explore from './Explore.svelte';
    import Search from './Search.svelte';
    import Library from './Library.svelte';

    let isAuthenticated = false;
    let userInfo: User | null = null;
    let currentPage: string = 'home';

    // Check for auth token or handle redirect response
    onMount(async () => {
        await getUserInfo();
    });

    const DEX_CLIENT_ID = "Music-app";
    const REDIRECT_URI = "http://localhost:8000/authorize";
    const DEX_AUTH_ENDPOINT = "http://localhost:5556/auth";

    const loginWithDex = () => {
        const loginUrl = `${DEX_AUTH_ENDPOINT}?client_id=${DEX_CLIENT_ID}&redirect_uri=${encodeURIComponent(REDIRECT_URI)}&response_type=code&scope=openid%20email%20profile`;
        window.location.href = loginUrl;
    };

    const logout = () => {
        isAuthenticated = false;
        userInfo = null;
        window.location.href = 'http://localhost:8000/logout';
    };

    async function getUserInfo() {
        const res = await fetch("/api/me");
        if (!res.ok) {
            console.error("NetworkError" + res);
            throw Error("NetworkError" + res);
        }
        let data = await res.json();
        if (data) {
            userInfo = data;
            isAuthenticated = true;
        }
    }

    function navigate(page: string) {
        currentPage = page;
    }
</script>

<svelte:head>
    <title>Music Match</title>
    <link rel="stylesheet" href="/app.css" />
</svelte:head>

{#if isAuthenticated}
<div class="app-layout">
    <aside class="sidebar">
        <h2>🎵 Music Match</h2>
        <nav class="sidebar-nav">
            <ul>
                <li><button on:click={() => navigate('home')}>Home</button></li>
                <li><button on:click={() => navigate('explore')}>Explore</button></li>
                <li><button on:click={() => navigate('search')}>Search</button></li>
                <li><button on:click={() => navigate('library')}>Library</button></li>
            </ul>
        </nav>
    </aside>

    {#if currentPage === 'home'}
        <Home {userInfo} {logout} />
    {:else if currentPage === 'explore'}
        <Explore {userInfo} {logout} />
    {:else if currentPage === 'search'}
        <Search {userInfo} {logout} />
    {:else if currentPage === 'library'}
        <Library {userInfo} {logout} />
    {/if}
</div>
{:else}
<div class="login-container">
    <h1>🎵 Welcome to Music Match 🎵</h1>
    <p>Discover music you'll love based on your preferences.</p>
    <button on:click={loginWithDex}>Login with Dex</button>
</div>
{/if}