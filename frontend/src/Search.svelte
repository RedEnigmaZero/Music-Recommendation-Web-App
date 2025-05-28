<script lang="ts">
    import type { User } from '../lib/User';

    export let userInfo: User;
</script>

<svelte:head>
    <title>Search | Music Match</title>
</svelte:head>

<main class="main-view">
    <header class="main-header">
        <h1>🔎 Search</h1>
        <button class="logout-btn" on:click={logout}>Logout</button>
    </header>

    <section class="content">
        <p>Search for artists, albums, or songs.</p>
        <!-- Add search form and results here -->
    </section>
</main>