import { test, expect, vi, beforeEach, describe } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import App from './App.svelte';
import Home from './Home.svelte';
import Explore from './Explore.svelte';
import Library from './Library.svelte';
import Search from './Search.svelte';

/*
In order to understand how to write the tests, first we looked at the lab slides, then we had to do some reading from svelte testing documentation and npm documentation. We also read up on documentation in NYT's response fields to help make tests on articles.
Here are the links of the documentation that we used. The tests were succesfully ran on our machines. Check test_proof for screenshots on the passing tests.
https://docs.npmjs.com/downloading-and-installing-node-js-and-npm - Node and npm documentation 
https://svelte.dev/docs/svelte/testing - Svelte testing documentation
https://svelte.dev/tutorial/svelte/welcome-to-svelte - Intro Svelte code documentation
https://canvas.ucdavis.edu/courses/993295/files/folder/Lab%20Materials/week%205? - Week 5 Lab Slides
*/

// Test that the App shows a loading screen
test('App shows loading screen', () => {
  render(App);
  expect(screen.getByText(/loading/i)).toBeInTheDocument();
});

// Test that the App can handle a Spotify redirect error 
test('App handles Spotify error', async () => {
  history.pushState({}, '', '/?error=access_denied');
  render(App);
  expect(await screen.findByText(/loading/i)).toBeInTheDocument();
});

// Test that the Home page is shown after the user is signed in
test('Home shows for authenticated user', () => {
  render(Home);
  expect(screen.getByRole('heading', { name: /welcome, user/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument();
});

// Test that the Library shows that you need to be authenticated
test('Library shows message when not authenticated', () => {
  render(Library);
  expect(screen.getByText(/spotify playlists/i)).toBeInTheDocument();
  expect(screen.getByText(/please log in to see your library/i)).toBeInTheDocument();
});

// Test that the Search page shows the search bar
test('Search shows the correct search input', () => {
  render(Search);
  expect(screen.getByPlaceholderText(/search for songs, artists, albums/i)).toBeInTheDocument();
});

// Test that when the user types in the search bar it shows the output
test('Search input updates when user types', async () => {
  render(Search);
  const input = screen.getByPlaceholderText(/search for songs, artists, albums/i);
  await userEvent.type(input, 'J Cole');
  expect(input).toHaveValue('J Cole');
});

