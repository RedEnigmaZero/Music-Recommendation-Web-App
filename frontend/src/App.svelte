<script lang="ts">
  import { onMount } from "svelte";
  import type { User } from "./lib/User";
  import Home from "./Home.svelte";
  import Explore from "./Explore.svelte";
  import Search from "./Search.svelte";
  import Library from "./Library.svelte";
  import initSpotifyIFrameAPI from "./lib/initSpotifyIFrameAPI";

  let isAuthenticated = false;
  let userInfo: User | null = null;
  let currentPage: string = "home";
  let isLoading = true;

  async function handleAuth() {
    isLoading = true;
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get("code");
    const error = urlParams.get("error");

    if (error) {
      console.error("SVELTE: Error received from Spotify redirect:", error);
      window.history.replaceState({}, document.title, window.location.pathname);
      isAuthenticated = false;
      userInfo = null;
      await new Promise(resolve => setTimeout(resolve, 200)); // 200ms wait
      isLoading = false;
      return;
    }

    if (code) {
      console.log("SVELTE: Authorization code found in URL:", code);

      window.history.replaceState({}, document.title, window.location.pathname);

      try {
        const response = await fetch("/api/spotify/token", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ code: code }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({
            error: "Failed to parse error JSON from backend",
          }));
          console.error(
            "SVELTE: Backend failed to exchange Spotify code:",
            errorData.error || response.statusText
          );
          isAuthenticated = false;
          userInfo = null;
        } else {
          const result = await response.json();
          if (result.success && result.user) {
            console.log(
              "SVELTE: User successfully authenticated via backend token exchange:",
              result.user
            );
            userInfo = result.user;
            isAuthenticated = true;
          } else {
            console.error(
              "SVELTE: Backend token exchange reported success=false or no user data:",
              result
            );
            isAuthenticated = false;
            userInfo = null;
          }
        }
      } catch (networkError) {
        console.error(
          "SVELTE: Network error during Spotify code exchange with backend:",
          networkError
        );
        isAuthenticated = false;
        userInfo = null;
      }
    } else {
      console.log(
        "SVELTE: No authorization code in URL. Checking existing session with getUserInfo()."
      );
      await getUserInfo();
    }

    if (!isAuthenticated) {
    await getUserInfo(); // fallback in case cookie just got set
    }
    
    isLoading = false;
  }

  onMount(async () => {
    await handleAuth();

    // Init iframe API for music player in explore tab
    initSpotifyIFrameAPI();
  });

  const DEX_CLIENT_ID = "Music-app";
  const DEX_REDIRECT_URI = "http://localhost:8000/authorize";
  const DEX_AUTH_ENDPOINT = "http://localhost:5556/auth";

  const loginWithDex = () => {
    const loginUrl = `${DEX_AUTH_ENDPOINT}?client_id=${DEX_CLIENT_ID}&redirect_uri=${encodeURIComponent(DEX_REDIRECT_URI)}&response_type=code&scope=openid%20email%20profile`;
    window.location.href = loginUrl;
  };

  const logout = () => {
    isAuthenticated = false;
    userInfo = null;
    window.location.href = "http://localhost:8000/logout";
  };

  async function getUserInfo() {
    console.log("SVELTE: getUserInfo() called to fetch /api/me");
    isLoading = true;
    try {
      const res = await fetch("/api/me");
      if (!res.ok) {
        console.log(
          "SVELTE: /api/me call not OK or user not logged in. Status:",
          res.status,
          res.statusText
        );
        userInfo = null;
        isAuthenticated = false;
      } else {
        const textResponse = await res.text();
        if (!textResponse) {
          console.log(
            "SVELTE: /api/me returned empty response. Assuming not authenticated."
          );
          userInfo = null;
          isAuthenticated = false;
        } else {
          const data = JSON.parse(textResponse);
          console.log("SVELTE: Data received from /api/me:", data);
          if (data && data.id) {
            userInfo = data;
            isAuthenticated = true;
            console.log("SVELTE: User identified from /api/me:", userInfo);
          } else {
            userInfo = null;
            isAuthenticated = false;
            console.log(
              "SVELTE: /api/me returned null or no user data. Not authenticated."
            );
          }
        }
      }
    } catch (error) {
      console.error(
        "SVELTE: Error in getUserInfo (fetching /api/me or parsing JSON):",
        error
      );
      userInfo = null;
      isAuthenticated = false;
    }
    isLoading = false;
  }

  function navigate(page: string) {
    currentPage = page;
  }

  const loginWithSpotify = () => {
    window.location.href = "http://localhost:8000/spotify/authorize";
  };
</script>

<svelte:head>
  <title>Music Match</title>
  <link rel="stylesheet" href="/app.css" />
</svelte:head>

{#if isLoading}
  <div class="login-container">
    <h1>Loading Music Match...</h1>
    <p>Please wait.</p>
  </div>
{:else if isAuthenticated}
  <div class="app-layout">
    <aside class="sidebar">
      <h2>🎵 Music Match</h2>
      <nav class="sidebar-nav">
        <ul>
          <li><button on:click={() => navigate("home")}>Home</button></li>
          <li><button on:click={() => navigate("explore")}>Explore</button></li>
          <li><button on:click={() => navigate("search")}>Search</button></li>
          <li><button on:click={() => navigate("library")}>Library</button></li>
        </ul>
      </nav>
      {#if userInfo}
        <div style="padding: 1rem; text-align: center; margin-top: auto;">
          <p style="margin-bottom: 0.5rem;">
            Logged in as: {userInfo.name || userInfo.email}
          </p>
          <button
            on:click={logout}
            style="background-color: #d9534f; color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer;"
            >Logout</button
          >
        </div>
      {/if}
    </aside>

    {#if currentPage === "home"}
      <Home {userInfo} {logout} />
    {:else if currentPage === "explore"}
      <Explore {userInfo} {logout} />
    {:else if currentPage === "search"}
      <Search {userInfo} {logout} />
    {:else if currentPage === "library"}
      <Library {userInfo} {logout} />
    {/if}
  </div>
{:else}
  <div class="login-container">
    <h1>🎵 Welcome to Music Match 🎵</h1>
    <p>Discover music you'll love based on your preferences.</p>
    <button on:click={loginWithSpotify}>Login with Spotify</button>
  </div>
{/if}
