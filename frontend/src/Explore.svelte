<script lang="ts">
    import type { User } from './lib/User';
    import './styles/explore.css';
    import {onMount} from "svelte";

    let userInfo: User = $props();

    // List of songs to be shown
    let tracks: String[] = [
        "40riOy7x9W7GXjyGp4pjAv",
        "49MHCPzvMLXhRjDantBMVH",
        "2G2YzndIA6jeWFPBXhUjh5",
        "6WCeFNVAXUtNczb7lqLiZU",
        "30U2ANWm8iFBRiYX3USS5H",
    ];

    // Index of tail of cards array within tracks
    // Prevent rendering out of bounds
    let currentIndex = 0;

    // Prevent card to be swiped in both left and right
    let isAnimating = false;

    // Array of div containing iframes
    let cards: {element: HTMLDivElement, id: string}[] = [];

    // Array of embed controller for autoplay
    // Separated from cards array because we don't know what type this is
    let embedControllers: any[] = [];

    // iframe API from spotify to generate controllers
    let iframeAPI: any = null;

    // HTML element. Will be assigned on mount
    let exploreAccept: HTMLElement | null = null
    let exploreReject: HTMLElement | null = null;
    let cardContainer: HTMLElement | null = null;

    onMount(() => {
        exploreAccept = document.getElementById("explore-accept");
        exploreReject = document.getElementById("explore-reject");
        cardContainer = document.getElementById("card-container");

        // This function will be called once IFrameAPI from spotify is ready to be used
        window.onSpotifyIframeApiReady = (IFrameAPI: any) => {
            // Save to generate controller for other songs
            iframeAPI = IFrameAPI;

            // Create three cards initially
            for (let i = 0; i < 3; i++) {
                if (currentIndex + i < tracks.length) {
                    createCard(tracks[currentIndex])
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
            }

            // Initiate autoplay
            if (embedControllers.length > 0) {
                embedControllers[0]?.play();
            }
        };
    })

    // Helper function to create card. Takes track id of a song
    function createCard(trackId: String) {
        if (!cardContainer) return;

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
            { // Options
                uri:`spotify:track:${trackId}`,
                width: '100%',
                height: '100%',
            },
            (EmbedController: any) => embedControllers.push(EmbedController) // Callback, to insert the controller into embedControllers array
        )

        // Once card is made, push it to cards array
        cards.push({element: exploreCard, id: trackId});

        // Increase the index for tail element
        currentIndex++;
    }

    // Show empty state when no cards left
    function showEmptyState() {
        let emptyState = document.getElementById("empty-state");
        if (!emptyState) return;
        emptyState.classList.remove("hidden");
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
    function reset() {
        // Reset index and make initial cards
        currentIndex = 0;
        for (let i = 0; i < 3; i++) {
            if (currentIndex + i < tracks.length) {
                createCard(tracks[currentIndex])
            }
        }
        updateCardPositions();
        // Set up drag events for the top card
        if (cards.length > 0) {
            setupDrag(cards[0].element);
        }
        embedControllers[0].play();
    }

    // Set up drag events for a card
    // We went through the code found at https://codepen.io/radenadri/pen/ZYYQKgN and adopted it
    function setupDrag(card: HTMLDivElement) {
        let startX: number, startY: number, moveX: number, moveY: number;
        let isDragging = false;

        if (!cardContainer) return;
        cardContainer.onmousedown = startDrag
        cardContainer.ontouchstart = startDrag

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

            document.removeEventListener("mousemove", drag);
            document.removeEventListener("touchmove", drag);
            document.removeEventListener("mouseup", endDrag);
            document.removeEventListener("touchend", endDrag);

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
                card.style.transform = "translateY(0) rotate(0deg)";

                setTimeout(() => {
                    card.style.transition = "";
                }, 500);
            }
        }
    }

    // Swipe right (like)
    // We went through the code found at https://codepen.io/radenadri/pen/ZYYQKgN and adopted it
    function swipeRight() {
        if (isAnimating || cards.length === 0) return;

        isAnimating = true;

        const card = cards[0].element;
        card.classList.add("swipe-right");

        setTimeout(() => {
            postRating(cards[0].id, "like");
            card.remove();
            cards.shift();

            // Create new card if available
            if (currentIndex < tracks.length) {
                createCard(tracks[currentIndex]);
            }

            // Update positions of remaining cards
            updateCardPositions();

            // Set up drag for new top card
            if (cards.length > 0) {
                setupDrag(cards[0].element);
            } else {
                showEmptyState();
            }

            isAnimating = false;
        }, 300);

        embedControllers.shift();
        embedControllers[0].play();
    }

    // Swipe left (dislike)
    // We went through the code found at https://codepen.io/radenadri/pen/ZYYQKgN and adopted it
    function swipeLeft() {
        if (isAnimating || cards.length === 0) return;

        isAnimating = true;

        const card = cards[0].element;
        card.classList.add("swipe-left");

        setTimeout(() => {
            postRating(cards[0].id, "dislike");
            card.remove();
            cards.shift();

            // Create new card if available
            if (currentIndex < tracks.length) {
                createCard(tracks[currentIndex]);
            }

            // Update positions of remaining cards
            updateCardPositions();

            // Set up drag for new top card
            if (cards.length > 0) {
                setupDrag(cards[0].element);
            } else {
                showEmptyState();
            }

            isAnimating = false;
        }, 300);

        embedControllers.shift();
        embedControllers[0].play();
    }

    async function postRating(trackId: string, rating: string) {
        try {
            const res = await fetch(`http://localhost:8000/api/feedback/${trackId}`, {
                method: "PUT",
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    rating: rating
                })
            });
            if (!res.ok) {
                console.error("NetworkError");
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
            const res = await fetch(`http://localhost:8000/api/save/${cards[0].id}`, {
                method: "PUT"
            });
            if (!res.ok) {
                console.error("NetworkError");
                console.error(res);
                return;
            }
        } catch (error) {
            console.error(error);
            return;
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
                <button onclick={reset}>
                    Find more
                </button>
            </div>

            <!-- Icon for moving the card to left side -->
            <div id="explore-reject" class="explore-action">
                <p>N</p>
            </div>

            <!-- Icon for moving the card to right side -->
            <div id="explore-accept" class="explore-action">
                <p>Y</p>
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
        <p id="explore-hints">Some text about keyboard shortcut</p>
    </section>
</main>
