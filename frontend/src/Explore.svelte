<script lang="ts">
    import type { User } from '../lib/User';

    export let userInfo: User;
</script>

<svelte:head>
    <title>Explore | Music Match</title>
</svelte:head>

<main class="main-view">
    <header class="main-header">
        <h1>🔍 Explore Music</h1>
        <button class="logout-btn" on:click={logout}>Logout</button>
    </header>

    <section class="content">
        <p>Discover new music based on your preferences.</p>
        <!-- Add explore content here -->
    </section>
</main>