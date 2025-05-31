<script lang="ts">
    import type { User } from '../lib/User';
  
    export let userInfo: User;
    export let logout: () => void;
  
    const trendingSongs = [
      {
        name: "Blinding Lights",
        artist: "The Weeknd",
        image: "/images/blinding_lights.png"
      },
      {
        name: "As It Was",
        artist: "Harry Styles",
        image: "/images/as_it_was.png"
      },
      {
        name: "Kill Bill",
        artist: "SZA",
        image: "/images/kill_bill.png"
      },
      {
        name: "Paint The Town Red",
        artist: "Doja Cat",
        image: "/images/paint_red.png"
      },
      {
        name: "good 4 u",
        artist: "Olivia Rodrigo",
        image: "/images/good4u.png"
      }
    ];
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
      <h2>🔥 Trending Now</h2>
      <div class="scroll-container">
        {#each trendingSongs as song}
          <div class="album-card">
            <img
              src={song.image}
              alt={song.name}
              style="width: 160px; height: 160px; object-fit: cover; border-radius: 6px;"
            />
            <p><strong>{song.name}</strong></p>
            <p style="font-size: 0.85rem;">{song.artist}</p>
          </div>
        {/each}
      </div>
    </section>
  </main>
  