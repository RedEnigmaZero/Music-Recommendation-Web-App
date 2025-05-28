<script lang="ts">
    import type { User } from '../lib/User';

    export let userInfo: User;
</script>

<svelte:head>
    <title>Library | Music Match</title>
</svelte:head>

<main class="main-view">
    <header class="main-header">
        <h1>📚 Your Library</h1>
        <button class="logout-btn" on:click={logout}>Logout</button>
    </header>

    <section class="content">
        <p>Your saved music and preferences.</p>
        <!-- Add library content here -->
    </section>
</main>