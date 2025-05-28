<script lang="ts">
    import type { User } from '../lib/User';

    export let userInfo: User;
    export let logout: () => void;
</script>

<svelte:head>
    <title>Home | Music Match</title>
</svelte:head>

<main class="main-view">
    <header class="main-header">
        <h1>🎵 Welcome, {userInfo?.name || "User"}!</h1>
        <button class="logout-btn" on:click={logout}>Logout</button>
    </header>

    <section class="content">
        <p>Set your music preferences or start exploring recommendations.</p>
        <!-- Placeholder for additional components like preferences or song recs -->
    </section>
</main>