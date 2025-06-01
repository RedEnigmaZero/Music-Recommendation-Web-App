<script lang="ts">
	import type { User } from "./lib/User";
	import "./styles/explore.css";
	import { onMount } from "svelte";
  
	export let userInfo: User | null; // User info, can be null if not immediately available
	export let logout: () => void; // Logout function passed from App.svelte
  
	// List of songs to be shown - will be populated from Spotify API
	let tracks: String[] = [];
  
	// Store track details from Spotify API
	let trackDetails: any[] = [];
  
	// Store user's likes for better recommendations
	let likedTracks: string[] = [];
	
	// Store liked artists for recommendations
	let likedArtists: string[] = [];
	
	// Store disliked tracks to avoid similar songs
	let dislikedTracks: string[] = [];
	
	// Store disliked artists to avoid recommending their songs
	let dislikedArtists: string[] = [];
	
	// Store disliked genres to avoid similar music
	let dislikedGenres: string[] = [];
	
	// Track which songs we've already shown to avoid duplicates
	let shownTrackIds: Set<string> = new Set();
  
	// Index of tail of cards array within tracks
	// Prevent rendering out of bounds
	let currentIndex = 0;
  
	// Prevent card to be swiped in both left and right
	let isAnimating = false;
  
	// Array of div containing iframes
	let cards: { element: HTMLDivElement; id: string }[] = [];
  
	// Array of embed controller for autoplay
	// Separated from cards array because we don't know what type this is
	let embedControllers: any[] = [];
  
	// iframe API from spotify to generate controllers
	let iframeAPI: any = null;
  
	// HTML element. Will be assigned on mount
	let exploreAccept: HTMLElement | null = null;
	let exploreReject: HTMLElement | null = null;
	let cardContainer: HTMLElement | null = null;
  
	onMount(async () => {
	  exploreAccept = document.getElementById("explore-accept");
	  exploreReject = document.getElementById("explore-reject");
	  cardContainer = document.getElementById("card-container");
  
	  // Load user preferences from storage or API
	  await loadUserPreferences();
  
	  // Get tracks from Spotify API
	  await getTracksFromSpotify();
  
	  // This function will be called once IFrameAPI from spotify is ready to be used
	  window.onSpotifyIframeApiReady = (IFrameAPI: any) => {
		// Save to generate controller for other songs
		iframeAPI = IFrameAPI;
  
		// Create three cards initially
		for (let i = 0; i < 3; i++) {
		  if (currentIndex + i < tracks.length) {
			createCard(tracks[currentIndex + i]);
		  }
		}
		updateCardPositions();
  
		// Set up drag events for the top card
		if (cards.length > 0) {
		  setupDrag(cards[0].element);
		}
  
		// Assign key binding here to prevent user from swiping before cards exist
		document.onkeydown = (e) => {
		  if (isAnimating) return;
  
		  if (e.key === "ArrowRight") {
			swipeRight();
		  } else if (e.key === "ArrowLeft") {
			swipeLeft();
		  }
		};
  
		// Initiate autoplay
		if (embedControllers.length > 0) {
		  embedControllers[0]?.play();
		}
	  };
	});
  
	// Load user preferences from your backend/storage
	async function loadUserPreferences() {
	  try {
		const res = await fetch('/api/user/preferences');
		if (res.ok) {
		  const preferences = await res.json();
		  likedTracks = preferences.likedTracks || [];
		  likedArtists = preferences.likedArtists || [];
		  dislikedTracks = preferences.dislikedTracks || [];
		  dislikedArtists = preferences.dislikedArtists || [];
		  dislikedGenres = preferences.dislikedGenres || [];
		}
	  } catch (error) {
		console.error("Error loading user preferences:", error);
	  }
	}
  
	// Save user preferences to your backend/storage
	async function saveUserPreferences() {
	  try {
		await fetch('/api/user/preferences', {
		  method: 'PUT',
		  headers: {
			'Content-Type': 'application/json',
		  },
		  body: JSON.stringify({
			likedTracks,
			likedArtists,
			dislikedTracks,
			dislikedArtists,
			dislikedGenres
		  })
		});
	  } catch (error) {
		console.error("Error saving user preferences:", error);
	  }
	}
  
	// Check if a track should be filtered out based on dislikes
	function shouldFilterTrack(track: any): boolean {
	  // Filter out disliked tracks
	  if (dislikedTracks.includes(track.id)) {
		return true;
	  }
	  
	  // Filter out tracks by disliked artists
	  if (track.artists && track.artists.some(artist => dislikedArtists.includes(artist.id))) {
		return true;
	  }
	  
	  // Filter out tracks with disliked genres (if genre data is available)
	  if (track.genres && track.genres.some(genre => dislikedGenres.includes(genre))) {
		return true;
	  }
	  
	  return false;
	}
  
	// Helper function to create card. Takes track id of a song
	function createCard(trackId: String, trackIndex: number = currentIndex) {
	  if (!cardContainer || !iframeAPI) return;
  
	  // div that iframe will go in
	  const exploreCard = document.createElement("div");
	  exploreCard.classList.add("explore-card");
	  cardContainer.appendChild(exploreCard);
  
	  // overlay so that user can hover over the card and swipe it.
	  // if this does not exist, click will be taken by inner html and user cannot swipe
	  const playerOverlay = document.createElement("div");
	  playerOverlay.classList.add("explore-player-overlay");
	  exploreCard.appendChild(playerOverlay);
  
	  // A div that will be consumed by spotify API
	  const player = document.createElement("div");
	  exploreCard.appendChild(player);
  
	  // Create embedded controller for the song for autoplay
	  iframeAPI.createController(
		player, // element to consume
		{
		  // Options
		  uri: `spotify:track:${trackId}`,
		  width: "100%",
		  height: "100%",
		},
		(EmbedController: any) => embedControllers.push(EmbedController) // Callback, to insert the controller into embedControllers array
	  );
  
	  // Once card is made, push it to cards array
	  cards.push({ element: exploreCard, id: trackId.toString() });
  
	  // Increase the index for tail element only if this is the next sequential card
	  if (trackIndex === currentIndex) {
		currentIndex++;
	  }
	}
  
	// Show empty state when no cards left
	function showEmptyState() {
	  let emptyState = document.getElementById("empty-state");
	  if (!emptyState) return;
	  emptyState.classList.remove("hidden");
	  
	  // Hide the empty state since we'll load more tracks
	  setTimeout(() => {
		emptyState.classList.add("hidden");
	  }, 100);
	}
  
	// Remove all ordering class and reassign
	function updateCardPositions() {
	  cards.forEach((card, index) => {
		card.element.classList.remove("explore-card-1");
		card.element.classList.remove("explore-card-2");
		card.element.classList.remove("explore-card-3");
		card.element.classList.add(`explore-card-${index + 1}`);
	  });
	}
  
	// Reset the state. Should be called after refreshing tracks array for new content
	// This function should only be called when there are no cards left.
	async function reset() {
	  // Clear existing cards and controllers
	  cards.forEach(card => card.element.remove());
	  cards = [];
	  embedControllers = [];
	  
	  await getMoreTracks();
  
	  // Reset index and make initial cards
	  currentIndex = 0;
	  for (let i = 0; i < 3; i++) {
		if (currentIndex + i < tracks.length) {
		  createCard(tracks[currentIndex + i]);
		}
	  }
	  updateCardPositions();
	  // Set up drag events for the top card
	  if (cards.length > 0) {
		setupDrag(cards[0].element);
	  }
	  if (embedControllers.length > 0) {
		embedControllers[0].play();
	  }
	}
  
	// Set up drag events for a card
	// We went through the code found at https://codepen.io/radenadri/pen/ZYYQKgN and adopted it
	function setupDrag(card: HTMLDivElement) {
	  let startX: number, startY: number, moveX: number, moveY: number;
	  let isDragging = false;
  
	  if (!cardContainer) return;
	  
	  // Remove existing event listeners to prevent duplicates
	  cardContainer.onmousedown = null;
	  cardContainer.ontouchstart = null;
	  
	  cardContainer.onmousedown = startDrag;
	  cardContainer.ontouchstart = startDrag;
  
	  function startDrag(e) {
		if (isAnimating) return;
  
		isDragging = true;
		const clientX = e.clientX || e.touches[0].clientX;
		const clientY = e.clientY || e.touches[0].clientY;
  
		startX = clientX;
		startY = clientY;
  
		document.onmousemove = drag;
		document.ontouchmove = drag;
		document.onmouseup = endDrag;
		document.ontouchend = endDrag;
	  }
  
	  function drag(e) {
		if (!isDragging) return;
		if (!exploreAccept || !exploreReject) return;
  
		e.preventDefault();
  
		const clientX = e.clientX || e.touches[0].clientX;
		const clientY = e.clientY || e.touches[0].clientY;
  
		moveX = clientX - startX;
		moveY = clientY - startY;
  
		// Calculate rotation based on drag distance
		const rotate = moveX * 0.1;
  
		// Apply transform
		card.style.transform = `translate(${moveX}px, ${moveY}px) rotate(${rotate}deg)`;
  
		// Show icon if dragged far enough
		if (moveX > 50) {
		  exploreAccept.classList.add("show-action");
		  exploreReject.classList.remove("show-action");
		} else if (moveX < -50) {
		  exploreReject.classList.add("show-action");
		  exploreAccept.classList.remove("show-action");
		} else {
		  exploreReject.classList.remove("show-action");
		  exploreAccept.classList.remove("show-action");
		}
	  }
  
	  function endDrag() {
		if (!isDragging) return;
		if (!exploreAccept || !exploreReject) return;
  
		isDragging = false;
  
		// Clean up event listeners properly
		document.onmousemove = null;
		document.ontouchmove = null;
		document.onmouseup = null;
		document.ontouchend = null;
  
		exploreReject.classList.remove("show-action");
		exploreAccept.classList.remove("show-action");
  
		// Check if card was dragged far enough to trigger swipe
		const threshold = 100;
  
		if (moveX > threshold) {
		  swipeRight();
		} else if (moveX < -threshold) {
		  swipeLeft();
		} else {
		  // Return to original position
		  card.style.transition = "transform 0.5s";
		  card.style.transform = "translateX(0) translateY(0) rotate(0deg)";
  
		  setTimeout(() => {
			card.style.transition = "";
		  }, 500);
		}
	  }
	}
  
	// Swipe right (like)
	function swipeRight() {
	  if (isAnimating || cards.length === 0) return;
  
	  isAnimating = true;
	  
	  // Store the liked track and its artists for better recommendations
	  const currentTrack = trackDetails.find(track => track.id === cards[0].id);
	  if (currentTrack) {
		// Add to liked tracks if not already there
		if (!likedTracks.includes(cards[0].id)) {
		  likedTracks.push(cards[0].id);
		}
		
		// Add artists to liked artists list
		currentTrack.artists?.forEach(artist => {
		  if (!likedArtists.includes(artist.id)) {
			likedArtists.push(artist.id);
		  }
		  
		  // Remove from disliked artists if they were there
		  const dislikedIndex = dislikedArtists.indexOf(artist.id);
		  if (dislikedIndex > -1) {
			dislikedArtists.splice(dislikedIndex, 1);
		  }
		});
		
		// Remove from disliked tracks if it was there
		const dislikedTrackIndex = dislikedTracks.indexOf(cards[0].id);
		if (dislikedTrackIndex > -1) {
		  dislikedTracks.splice(dislikedTrackIndex, 1);
		}
		
		// Save preferences
		saveUserPreferences();
	  }
  
	  const card = cards[0].element;
	  card.classList.add("swipe-right");
  
	  setTimeout(async () => {
		await postRating(cards[0].id, "like");
		card.remove();
		cards.shift();
		embedControllers.shift();
  
		// Create new card if available
		if (currentIndex < tracks.length) {
		  createCard(tracks[currentIndex]);
		} else {
		  // Auto-load more tracks when we're running low
		  await loadMoreTracksIfNeeded();
		}
  
		// Update positions of remaining cards
		updateCardPositions();
  
		// Set up drag for new top card
		if (cards.length > 0) {
		  setupDrag(cards[0].element);
		  // Start playing the new top card
		  if (embedControllers.length > 0) {
			embedControllers[0].play();
		  }
		} else {
		  showEmptyState();
		  await reset(); // Automatically load more when empty
		}
  
		isAnimating = false;
	  }, 300);
	}
  
	// Swipe left (dislike)
	function swipeLeft() {
	  if (isAnimating || cards.length === 0) return;
  
	  isAnimating = true;
  
	  // Store the disliked track and its artists to avoid similar recommendations
	  const currentTrack = trackDetails.find(track => track.id === cards[0].id);
	  if (currentTrack) {
		// Add to disliked tracks if not already there
		if (!dislikedTracks.includes(cards[0].id)) {
		  dislikedTracks.push(cards[0].id);
		}
		
		// Add artists to disliked artists list (but only if they're not in liked artists)
		currentTrack.artists?.forEach(artist => {
		  if (!likedArtists.includes(artist.id) && !dislikedArtists.includes(artist.id)) {
			dislikedArtists.push(artist.id);
		  }
		});
		
		// Add genres to disliked genres if available
		if (currentTrack.genres) {
		  currentTrack.genres.forEach(genre => {
			if (!dislikedGenres.includes(genre)) {
			  dislikedGenres.push(genre);
			}
		  });
		}
		
		// Remove from liked tracks if it was there
		const likedTrackIndex = likedTracks.indexOf(cards[0].id);
		if (likedTrackIndex > -1) {
		  likedTracks.splice(likedTrackIndex, 1);
		}
		
		// Save preferences
		saveUserPreferences();
	  }
  
	  const card = cards[0].element;
	  card.classList.add("swipe-left");
  
	  setTimeout(async () => {
		await postRating(cards[0].id, "dislike");
		card.remove();
		cards.shift();
		embedControllers.shift();
  
		// Create new card if available
		if (currentIndex < tracks.length) {
		  createCard(tracks[currentIndex]);
		} else {
		  // Auto-load more tracks when we're running low
		  await loadMoreTracksIfNeeded();
		}
  
		// Update positions of remaining cards
		updateCardPositions();
  
		// Set up drag for new top card
		if (cards.length > 0) {
		  setupDrag(cards[0].element);
		  // Start playing the new top card
		  if (embedControllers.length > 0) {
			embedControllers[0].play();
		  }
		} else {
		  showEmptyState();
		  await reset(); // Automatically load more when empty
		}
  
		isAnimating = false;
	  }, 300);
	}
  
	async function postRating(trackId: string, rating: string) {
	  try {
		const res = await fetch(`/api/feedback/${trackId}`, {
		  method: "PUT",
		  headers: {
			"Content-Type": "application/json",
		  },
		  body: JSON.stringify({
			rating: rating,
		  }),
		});
		if (!res.ok) {
		  console.error("Error posting rating");
		  console.error(res);
		  return;
		}
	  } catch (error) {
		console.error(error);
		return;
	  }
	}
  
	async function saveSong() {
	  try {
		const res = await fetch(`/api/save/${cards[0].id}`, {
		  method: "PUT",
		});
		if (!res.ok) {
		  console.error("Error saving song");
		  console.error(res);
		  return;
		}
	  } catch (error) {
		console.error(error);
		return;
	  }
	}
  
	// Get tracks from Spotify API - this will populate the tracks array
	async function getTracksFromSpotify() {
	  try {
		// Build URL with user preferences as query parameters
		let url = `/api/spotify/discover-tracks`;
		if (likedTracks.length > 0) {
		  url = `/api/spotify/personalized-tracks`;
		}
		
		// Add dislike filters as query parameters
		const params = new URLSearchParams();
		if (dislikedTracks.length > 0) {
		  params.append('excludeTracks', dislikedTracks.join(','));
		}
		if (dislikedArtists.length > 0) {
		  params.append('excludeArtists', dislikedArtists.join(','));
		}
		if (dislikedGenres.length > 0) {
		  params.append('excludeGenres', dislikedGenres.join(','));
		}
		if (likedTracks.length > 0) {
		  params.append('seedTracks', likedTracks.slice(-5).join(',')); // Use last 5 liked tracks as seeds
		}
		if (likedArtists.length > 0) {
		  params.append('seedArtists', likedArtists.slice(-5).join(',')); // Use last 5 liked artists as seeds
		}
		
		if (params.toString()) {
		  url += `?${params.toString()}`;
		}
		
		const res = await fetch(url);
		if (!res.ok) {
		  console.error("Error fetching tracks from Spotify");
		  console.error(res);
		  return;
		}
  
		const data = await res.json();
		
		// Extract track IDs and store full track details - filter out duplicates and dislikes
		const newTracks = data.tracks
		  .filter(track => !shownTrackIds.has(track.id))
		  .filter(track => !shouldFilterTrack(track));
		
		if (newTracks.length === 0) {
		  console.log("No new tracks found after filtering");
		  return;
		}
		
		tracks = newTracks.map(track => track.id);
		trackDetails = newTracks;
		
		// Mark these tracks as shown
		newTracks.forEach(track => shownTrackIds.add(track.id));
		
		console.log(`Fetched ${newTracks.length} new tracks based on preferences:`, trackDetails);
		
	  } catch (error) {
		console.error("Error in getTracksFromSpotify:", error);
	  }
	}
	
	// Get more tracks (replacement for getMoreTracks which was missing)
	async function getMoreTracks() {
	  await getTracksFromSpotify();
	}
  
	// Auto-load more tracks when running low
	async function loadMoreTracksIfNeeded() {
	  // If we're running low on tracks (less than 2 remaining), load more
	  if (currentIndex >= tracks.length - 2) {
		console.log("Running low on tracks, loading more...");
		await getMoreTracks();
		
		// Create new cards if we got new tracks
		for (let i = cards.length; i < 3 && currentIndex < tracks.length; i++) {
		  createCard(tracks[currentIndex]);
		}
		
		// Set up drag for the top card if we just created cards
		if (cards.length > 0) {
		  setupDrag(cards[0].element);
		}
	  }
	}
  
  </script>
  
  <svelte:head>
	<title>Explore | Music Match</title>
  </svelte:head>
  
  <main class="main-view explore-main-view">
	<header class="main-header">
	  <h1>🔍 Explore Music</h1>
	</header>
  
	<section class="content explore-content">
	  <p>Discover new music based on your preferences.</p>
	  <!-- Add explore content here -->
	  <p id="explore-prompt">Swipe right if you love the song!</p>
	  <div id="card-container">
		<!-- Show when no cards left to swipe -->
		<div id="empty-state" class="hidden">
		  <h3>No more for now!</h3>
		  <button onclick={reset}> Find more </button>
		</div>
  
		<!-- Icon for moving the card to left side -->
		<div id="explore-reject" class="explore-action">
		  <p>❌</p>
		</div>
  
		<!-- Icon for moving the card to right side -->
		<div id="explore-accept" class="explore-action">
		  <p>♥️</p>
		</div>
  
		<!-- Cards will be inserted here by JavaScript -->
	  </div>
  
	  <!-- Button if people want to click instead -->
	  <div id="explore-action-buttons">
		<button onclick={swipeLeft}>Dislike</button>
  
		<!-- Maybe something like super like? -->
		<button onclick={saveSong}>Save</button>
  
		<button onclick={swipeRight}>Like</button>
	  </div>
  
	  <!-- Keyboard shortcut hints for user -->
	  <p id="explore-hints">
		<span><kbd>←</kbd> dislike</span> <span><kbd>→</kbd> like</span>
	  </p>
	</section>
  </main>
