<script lang="ts">
    import type { User } from './lib/User';
    import './styles/explore.css';

    export let userInfo: User;
    
    let trackId: String = "40riOy7x9W7GXjyGp4pjAv";
</script>

<svelte:head>
    <title>Explore | Music Match</title>
</svelte:head>

<main class="main-view">
    <header class="main-header">
        <h1>🔍 Explore Music</h1>
        <a href="http://localhost:8000/logout">
            <button class="logout-btn">Logout</button>
        </a>

    </header>

    <section class="content explore-content">
        <p>Discover new music based on your preferences.</p>
        <!-- Add explore content here -->
        <div id="player">
            <iframe
                    title="Player"
                    style="border-radius:12px"
                    src={`https://open.spotify.com/embed/track/${trackId}?utm_source=generator&theme=0`}
                    width="100%"
                    height="100%"
                    allowfullscreen={true}
                    allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                    loading="lazy"></iframe>
        </div>
        <div id="explore-action-buttons">
            <button>Dislike</button>
            <button>Save</button>
            <button>Like</button>
        </div>
        <p id="explore-hints">Some text about keyboard shortcut</p>
    </section>
</main>
