<script lang="ts">
    import type { User } from '../lib/User';

    let userInfo: User = $props();
</script>

<svelte:head>
    <title>Library | Music Match</title>
</svelte:head>

<main class="main-view">
    <header class="main-header">
        <h1>📚 Your Library</h1>
    </header>

    <section class="content">
        <p>Your saved music and preferences.</p>
        <!-- Add library content here -->
    </section>
</main>